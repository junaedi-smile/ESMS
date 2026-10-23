import logging
import os
from datetime import date, datetime
from django.db.models.signals import post_save, post_delete
from django.dispatch import receiver
from django.db.models import Sum
from django.core.mail import EmailMessage
from django.utils import timezone
from django.conf import settings
from django.template.loader import render_to_string
from django.template import TemplateDoesNotExist
from django.core.signing import TimestampSigner
from django.urls import reverse

from .models import (
    AssetMonthlyStatus,
    AssetEquipmentDisposed,
    AssetEquipment,
    AssetEquipmentOperate,
    AssetEquipmentBreakdown,
    AssetEquipmentStandby,
    AssetEquipmentPrepareDisposed,
)
from data.models import (
    EquipmentWeight,
    AR01,
    KaryawanPenerimaNotifikasi,
)

logger = logging.getLogger(__name__)


def _parse_month(month_value):
    if not month_value:
        return None
    if isinstance(month_value, datetime):
        return month_value.date()
    if isinstance(month_value, date):
        return month_value
    if isinstance(month_value, str):
        try:
            return datetime.strptime(month_value, '%Y-%m-%d').date()
        except ValueError:
            logger.error(f"Could not parse MONTH string: {month_value}")
    return None


def _bersihkan_semua_tabel_anak(cn_sap):
    AssetEquipmentDisposed.objects.filter(asset__CN_SAP=cn_sap).delete()
    AssetEquipmentStandby.objects.filter(asset__CN_SAP=cn_sap).delete()
    AssetEquipmentBreakdown.objects.filter(asset__CN_SAP=cn_sap).delete()
    AssetEquipmentOperate.objects.filter(asset__CN_SAP=cn_sap).delete()
    # ✅ Gunakan asset__CN_SAP karena ini model mandiri berelasi OneToOne
    AssetEquipmentPrepareDisposed.objects.filter(asset__CN_SAP=cn_sap).delete()


# ============================================================
# 1. CENTRALIZED SINKRONISASI STATUS ASSET (REVISI AMAN DOKUMEN & METADATA)
# ============================================================
@receiver(post_save, sender=AssetMonthlyStatus)
def central_asset_status_sync(sender, instance, created, **kwargs):

    # 1. PENCEGAHAN REKURSI: Jika sedang proses update, jangan jalankan lagi
    if kwargs.get('raw', False):
        return
     
    current_cn_sap = instance.CN_SAP
     
    # 🌟 CEK KELENGKAPAN DOKUMEN FASE 1 DARI MODEL MANDIRINYA LANGSUNG
    prepare_obj = AssetEquipmentPrepareDisposed.objects.filter(asset__CN_SAP=current_cn_sap).first()
    
    is_complete = False
    if prepare_obj:
        is_complete = bool(
            prepare_obj.foto_4_sisi and 
            prepare_obj.rca and 
            prepare_obj.inspeksi_unit and 
            prepare_obj.pengajuan_disposed
        )
     
    print(f"--- SIGNAL TRIGGERED FOR {current_cn_sap} | Dokumen Lengkap: {is_complete} ---")
     
    # Tentukan kondisi final dengan aturan bisnis ketat
    if is_complete:
        condition = 'disposed'
        equipment_condition_val = 'DISPOSED'
        status_disposed_val = 'DISPOSED'
    else:
        # 🌟 JIKA DOKUMEN BELUM LENGKAP, CEGAH AGAR TIDAK BISA DISPOSED!
        raw_cond = (instance.EQUIPMENT_CONDITION or '').lower().strip()
        
        if raw_cond == 'disposed':
            condition = 'prepare for disposed'
            equipment_condition_val = 'PREPARE FOR DISPOSED'
            status_disposed_val = 'PREPARE FOR DISPOSED'
        else:
            condition = raw_cond
            equipment_condition_val = instance.EQUIPMENT_CONDITION
            status_disposed_val = instance.STATUS_EQUIPMENT_DISPOSED

    VALID_CONDITIONS = ['operate', 'standby', 'disposed', 'breakdown', 'prepare for disposed']

    # ── Ambil Weight & NBV terbaru ──────────────────────────────
    weight_obj = EquipmentWeight.objects.filter(equipment_type=instance.TYPE, egi=instance.EGI).first()
    latest_weight = weight_obj.weight if weight_obj else None
     
    latest_nbv = AR01.objects.filter(type_name=current_cn_sap).aggregate(total_nbv=Sum('book_value'))['total_nbv'] or 0

    # UPDATE INSTANCE LANGSUNG JIKA PERLU (Tanpa memicu signal lagi)
    if instance.WEIGHT != latest_weight or instance.NBV != latest_nbv:
        AssetMonthlyStatus.objects.filter(pk=instance.pk).update(WEIGHT=latest_weight, NBV=latest_nbv)
        instance.refresh_from_db()

    # ── Jika kondisi tidak dikenal → hapus semua ────────────────
    if condition not in VALID_CONDITIONS:
        try:
            _bersihkan_semua_tabel_anak(current_cn_sap)
            AssetEquipment.objects.filter(CN_SAP=current_cn_sap).delete()
        except Exception as e:
            logger.error(f"[{current_cn_sap}] Error cleaning: {e}")
        return

    processed_month = _parse_month(instance.MONTH)
    month_number    = processed_month.month if processed_month else None

    # ── STEP A: Upsert ke AssetEquipment (Master) ───────────────
    try:
        asset_parent, _ = AssetEquipment.objects.update_or_create(
            CN_SAP=current_cn_sap,
            defaults={
                'No_Asset':                 instance.No_Asset,
                'CN_ELLIPSE':               instance.CN_ELLIPSE,
                'EGI':                      instance.EGI,
                'TYPE':                     instance.TYPE,
                'GROUP':                    instance.GROUP,
                'CLASS_WEIGHT':             instance.CLASS_WEIGHT,
                'OWNERSHIP':                instance.OWNERSHIP,
                'SECTION':                  instance.SECTION,
                'LOCATION':                 instance.LOCATION,
                'SUB_SITE':                 instance.SUB_SITE,
                'SUB_LOCATION':             instance.SUB_LOCATION,
                'BRAND':                    instance.BRAND,
                'SN':                       instance.SN,
                'HM_SMR':                   instance.HM_SMR,
                'HM_DATE':                  instance.HM_DATE,
                'SPO_EQUIPMENT':            instance.SPO_EQUIPMENT,
                'PERSENTASE_SPO':           instance.PERSENTASE_SPO,
                'EQUIPMENT_CONDITION':      equipment_condition_val, 
                'STATUS_EQUIPMENT':         instance.STATUS_EQUIPMENT,
                'STATUS_EQUIPMENT_DISPOSED': status_disposed_val,     
                'REFERENSI_NO_PDE':         instance.REFERENSI_NO_PDE,
                'LAST_UPDATED_MONTH':       month_number,
                'LAST_UPDATED_YEAR':        instance.YEAR,
                'BP':                       instance.BP,
            }
        )
    except Exception as e:
        logger.error(f"[{current_cn_sap}] Critical Error Upsert Parent: {e}", exc_info=True)
        return

    # ── STEP B: Shared defaults untuk tabel anak ────────────────
    shared_defaults = {
        'No_Asset':                 instance.No_Asset,
        'CN_ELLIPSE':               instance.CN_ELLIPSE,
        'EGI':                      instance.EGI,
        'TYPE':                     instance.TYPE,
        'GROUP':                    instance.GROUP,
        'CLASS_WEIGHT':             instance.CLASS_WEIGHT,
        'OWNERSHIP':                instance.OWNERSHIP,
        'SECTION':                  instance.SECTION,
        'LOCATION':                 instance.LOCATION,
        'SUB_SITE':                 instance.SUB_SITE,
        'SUB_LOCATION':             instance.SUB_LOCATION,
        'BRAND':                    instance.BRAND,
        'SN':                       instance.SN,
        'HM_SMR':                   instance.HM_SMR,
        'HM_DATE':                  instance.HM_DATE,
        'SPO_EQUIPMENT':            instance.SPO_EQUIPMENT,
        'PERSENTASE_SPO':           instance.PERSENTASE_SPO,
        'EQUIPMENT_CONDITION':      equipment_condition_val, 
        'STATUS_EQUIPMENT':         instance.STATUS_EQUIPMENT,
        'STATUS_EQUIPMENT_DISPOSED': status_disposed_val,     
        'REFERENSI_NO_PDE':         instance.REFERENSI_NO_PDE,
        'LAST_UPDATED_MONTH':       month_number,
        'LAST_UPDATED_YEAR':        instance.YEAR,
        'BP':                       instance.BP,
    }

    # ── STEP C: AMANKAN FILE & METADATA LAMA SEBELUM BERSIH-BERSIH ────────
    existing_prepare = AssetEquipmentPrepareDisposed.objects.filter(asset__CN_SAP=current_cn_sap).first()
    existing_disposed = AssetEquipmentDisposed.objects.filter(asset=asset_parent).first()

    # Ambil file dan informasi _uploaded_at / _uploaded_by yang sudah ada agar tidak hilang
    saved_files = {
        'foto_4_sisi': (existing_prepare.foto_4_sisi if existing_prepare else None) or (existing_disposed.foto_4_sisi if existing_disposed else None),
        'foto_4_sisi_uploaded_at': (existing_prepare.foto_4_sisi_uploaded_at if existing_prepare else None) or (existing_disposed.foto_4_sisi_uploaded_at if existing_disposed else None),
        'foto_4_sisi_uploaded_by': (existing_prepare.foto_4_sisi_uploaded_by if existing_prepare else None) or (existing_disposed.foto_4_sisi_uploaded_by if existing_disposed else None),

        'inspeksi_unit': (existing_prepare.inspeksi_unit if existing_prepare else None) or (existing_disposed.inspeksi_unit if existing_disposed else None),
        'inspeksi_unit_uploaded_at': (existing_prepare.inspeksi_unit_uploaded_at if existing_prepare else None) or (existing_disposed.inspeksi_unit_uploaded_at if existing_disposed else None),
        'inspeksi_unit_uploaded_by': (existing_prepare.inspeksi_unit_uploaded_by if existing_prepare else None) or (existing_disposed.inspeksi_unit_uploaded_by if existing_disposed else None),

        'rca': (existing_prepare.rca if existing_prepare else None) or (existing_disposed.rca if existing_disposed else None),
        'rca_uploaded_at': (existing_prepare.rca_uploaded_at if existing_prepare else None) or (existing_disposed.rca_uploaded_at if existing_disposed else None),
        'rca_uploaded_by': (existing_prepare.rca_uploaded_by if existing_prepare else None) or (existing_disposed.rca_uploaded_by if existing_disposed else None),

        'pengajuan_disposed': (existing_prepare.pengajuan_disposed if existing_prepare else None) or (existing_disposed.pengajuan_disposed if existing_disposed else None),
        'pengajuan_disposed_uploaded_at': (existing_prepare.pengajuan_disposed_uploaded_at if existing_prepare else None) or (existing_disposed.pengajuan_disposed_uploaded_at if existing_disposed else None),
        'pengajuan_disposed_uploaded_by': (existing_prepare.pengajuan_disposed_uploaded_by if existing_prepare else None) or (existing_disposed.pengajuan_disposed_uploaded_by if existing_disposed else None),
    }

    # Bersihkan tabel anak yang lain
    _bersihkan_semua_tabel_anak(current_cn_sap)

    # ── STEP D: ISI TABEL ANAK SESUAI KONDISI (DENGAN MENYERTAKAN FILE & METADATA AMAN) ──
    if condition == 'disposed' or is_complete:
        defaults_disposed = {
            **shared_defaults,
            'EQUIPMENT_CONDITION': 'DISPOSED',
            'nbv_disposed': latest_nbv,
            **saved_files, # 🌟 Sertakan file & metadata lengkap agar tidak hilang!
        }
        AssetEquipmentDisposed.objects.update_or_create(
            asset=asset_parent, defaults=defaults_disposed
        )

    elif condition == 'standby':
        AssetEquipmentStandby.objects.update_or_create(
            asset=asset_parent, defaults=shared_defaults
        )

    elif condition == 'breakdown':
        AssetEquipmentBreakdown.objects.update_or_create(
            asset=asset_parent, defaults=shared_defaults
        )

    elif condition == 'operate':
        operate_defaults = shared_defaults.copy()
        operate_defaults.pop('LAST_UPDATED_MONTH', None)
        operate_defaults.pop('LAST_UPDATED_YEAR', None)
        operate_defaults.update({
            'FOTO':    instance.FOTO,
            'NBV':     latest_nbv,
            'WEIGHT':  latest_weight,
            'YEAR':    instance.YEAR,
            'MONTH':   instance.MONTH,
        })
        AssetEquipmentOperate.objects.update_or_create(
            asset=asset_parent, defaults=operate_defaults
        )

    elif condition == 'prepare for disposed':
        prepare_defaults = shared_defaults.copy()
        prepare_defaults.pop('LAST_UPDATED_MONTH', None)
        prepare_defaults.pop('LAST_UPDATED_YEAR', None)
         
        prepare_defaults['EQUIPMENT_CONDITION'] = 'PREPARE FOR DISPOSED'
        prepare_defaults['STATUS_EQUIPMENT_DISPOSED'] = 'PREPARE FOR DISPOSED'
        prepare_defaults['nbv_prepare'] = latest_nbv 
         
        # 🌟 Masukkan kembali file & metadata yang diselamatkan ke Prepare
        prepare_defaults.update(saved_files)
          
        AssetEquipmentPrepareDisposed.objects.update_or_create(
            asset_id=current_cn_sap, defaults=prepare_defaults
        )

# ============================================================
# 2. POST_DELETE — Sinkronisasi setelah record dihapus
# ============================================================
@receiver(post_delete, sender=AssetMonthlyStatus)
def sync_asset_equipment_after_delete(sender, instance, **kwargs):
    current_cn_sap = instance.CN_SAP
    logger.info(f"[{current_cn_sap}] post_delete triggered.")

    try:
        from django.db import transaction
        with transaction.atomic():

            remaining = AssetMonthlyStatus.objects.filter(
                CN_SAP=current_cn_sap
            ).order_by('-YEAR', '-MONTH').first()

            if remaining:
                logger.info(f"[{current_cn_sap}] Re-syncing to latest record (condition: {remaining.EQUIPMENT_CONDITION}).")
                central_asset_status_sync(
                    sender=AssetMonthlyStatus,
                    instance=remaining,
                    created=False,
                )
            else:
                logger.info(f"[{current_cn_sap}] No records left. Deleting all related data.")
                _bersihkan_semua_tabel_anak(current_cn_sap)
                AssetEquipment.objects.filter(CN_SAP=current_cn_sap).delete()

    except Exception as e:
        logger.error(f"[{current_cn_sap}] ERROR during post_delete: {e}", exc_info=True)


# ============================================================
# 3. WEIGHT & NBV SYNC
# ============================================================
@receiver(post_save, sender=AssetMonthlyStatus)
def fill_weight_after_creation(sender, instance, created, **kwargs):
    try:
        equipment_data = EquipmentWeight.objects.get(
            equipment_type=instance.TYPE, egi=instance.EGI
        )
        if instance.WEIGHT != equipment_data.weight:
            AssetMonthlyStatus.objects.filter(pk=instance.pk).update(WEIGHT=equipment_data.weight)
    except EquipmentWeight.DoesNotExist:
        if instance.WEIGHT is not None:
            AssetMonthlyStatus.objects.filter(pk=instance.pk).update(WEIGHT=None)
    except Exception as e:
        logger.error(f"Error weight fill: {e}")


@receiver(post_save, sender=EquipmentWeight)
def update_weight_on_equipment_change(sender, instance, created, **kwargs):
    try:
        AssetMonthlyStatus.objects.filter(
            TYPE=instance.equipment_type, EGI=instance.egi
        ).update(WEIGHT=instance.weight)
        AssetEquipmentOperate.objects.filter(
            TYPE=instance.equipment_type, EGI=instance.egi
        ).update(WEIGHT=instance.weight)
    except Exception as e:
        logger.error(f"Error weight update: {e}")


@receiver(post_delete, sender=EquipmentWeight)
def clear_weight_on_equipment_delete(sender, instance, **kwargs):
    try:
        AssetMonthlyStatus.objects.filter(
            TYPE=instance.equipment_type, EGI=instance.egi
        ).update(WEIGHT=None)
        AssetEquipmentOperate.objects.filter(
            TYPE=instance.equipment_type, EGI=instance.egi
        ).update(WEIGHT=None)
    except Exception as e:
        logger.error(f"Error weight clear: {e}")


@receiver(post_save, sender=AssetMonthlyStatus)
def fill_nbv_after_save(sender, instance, **kwargs):
    try:
        sum_nbv = AR01.objects.filter(
            type_name=instance.CN_SAP
        ).aggregate(total_nbv=Sum('book_value'))['total_nbv'] or 0
        if instance.NBV != sum_nbv:
            AssetMonthlyStatus.objects.filter(pk=instance.pk).update(NBV=sum_nbv)
    except Exception as e:
        logger.error(f"Error NBV fill: {e}")


@receiver(post_save, sender=AR01)
def update_nbv_on_ar01_change(sender, instance, **kwargs):
    try:
        related = AssetMonthlyStatus.objects.filter(CN_SAP=instance.type_name)
        if not related.exists():
            return
        for rec in related:
            sum_nbv = AR01.objects.filter(
                type_name=rec.CN_SAP
            ).aggregate(total_nbv=Sum('book_value'))['total_nbv'] or 0
            AssetMonthlyStatus.objects.filter(pk=rec.pk).update(NBV=sum_nbv)
            AssetEquipmentOperate.objects.filter(
                asset__CN_SAP=rec.CN_SAP
            ).update(NBV=sum_nbv)
    except Exception as e:
        logger.error(f"Error NBV update from AR01: {e}")


@receiver(post_delete, sender=AR01)
def clear_nbv_on_ar01_delete(sender, instance, **kwargs):
    try:
        related = AssetMonthlyStatus.objects.filter(CN_SAP=instance.type_name)
        if not related.exists():
            return
        for rec in related:
            sum_nbv = AR01.objects.filter(
                type_name=rec.CN_SAP
            ).aggregate(total_nbv=Sum('book_value'))['total_nbv'] or 0
            AssetMonthlyStatus.objects.filter(pk=rec.pk).update(NBV=sum_nbv)
            AssetEquipmentOperate.objects.filter(
                asset__CN_SAP=rec.CN_SAP
            ).update(NBV=sum_nbv)
    except Exception as e:
        logger.error(f"Error NBV clear from AR01: {e}")



# =========================================================================
# 4. Untuk Model Prepare Disposed (Sekarang berdiri mandiri, sender langsung)
# =========================================================================
@receiver(post_save, sender=AssetEquipmentPrepareDisposed)
def notif_prepare_disposed(sender, instance, created, **kwargs):
    dokumen_prepare_map = {
        'foto_4_sisi'        : 'notif_foto_4_sisi',
        'inspeksi_unit'      : 'notif_inspeksi',
        'rca'                : 'notif_rca',
        'pengajuan_disposed' : 'notif_pengajuan_disposed',
    }

    update_fields = kwargs.get('update_fields')

    if update_fields:
        for field_db, field_notif in dokumen_prepare_map.items():
            if field_db in update_fields:
                ocr_valid    = getattr(instance, '_ocr_valid', None)
                ocr_message  = getattr(instance, '_ocr_message', "Dokumen berhasil diproses")
                no_dokumen   = getattr(instance, '_no_dokumen', None)
                nama_dok_ocr = getattr(instance, '_nama_dok_ocr', None)
                usd_max      = getattr(instance, '_usd_max', None)
                ocr_depan    = getattr(instance, '_ocr_depan', True)
                ocr_belakang = getattr(instance, '_ocr_belakang', True)
                ocr_kanan    = getattr(instance, '_ocr_kanan', True)
                ocr_kiri     = getattr(instance, '_ocr_kiri', True)
                
                proses_dan_kirim_email(
                    instance, field_db, field_notif, 
                    ocr_valid=ocr_valid, ocr_message=ocr_message, 
                    no_dokumen=no_dokumen, nama_dok_ocr=nama_dok_ocr, usd_max=usd_max,
                    ocr_depan=ocr_depan, ocr_belakang=ocr_belakang, ocr_kanan=ocr_kanan, ocr_kiri=ocr_kiri
                )
    else:
        for field_db, field_notif in dokumen_prepare_map.items():
            file_obj = getattr(instance, field_db, None)
            if file_obj:
                uploaded_at = getattr(instance, f'{field_db}_uploaded_at', None)
                if uploaded_at:
                    selisih = (timezone.now() - uploaded_at).total_seconds()
                    if selisih < 10:
                        ocr_valid    = getattr(instance, '_ocr_valid', None)
                        ocr_message  = getattr(instance, '_ocr_message', "Dokumen berhasil diproses")
                        no_dokumen   = getattr(instance, '_no_dokumen', None)
                        nama_dok_ocr = getattr(instance, '_nama_dok_ocr', None)
                        usd_max      = getattr(instance, '_usd_max', None)
                        ocr_depan    = getattr(instance, '_ocr_depan', True)
                        ocr_belakang = getattr(instance, '_ocr_belakang', True)
                        ocr_kanan    = getattr(instance, '_ocr_kanan', True)
                        ocr_kiri     = getattr(instance, '_ocr_kiri', True)

                        proses_dan_kirim_email(
                            instance, field_db, field_notif, 
                            ocr_valid=ocr_valid, ocr_message=ocr_message, 
                            no_dokumen=no_dokumen, nama_dok_ocr=nama_dok_ocr, usd_max=usd_max,
                            ocr_depan=ocr_depan, ocr_belakang=ocr_belakang, ocr_kanan=ocr_kanan, ocr_kiri=ocr_kiri
                        )

# ====================================================================================================================== #
# 4. FUNGSI UTAMA PENGIRIM EMAIL (REUSABLE)- DOKUMEN UPLOAD 1 FILE PDF ========================================= ================= #
# ======================================================================================================================= #

def proses_dan_kirim_email(instance, field_name, filter_notif_field, ocr_valid=None, ocr_message=None, no_dokumen=None, nama_dok_ocr=None, usd_max=None, ocr_depan=None, ocr_belakang=None, ocr_kanan=None, ocr_kiri=None):
    """
    Fungsi bersama untuk mengecek file, mencari email tujuan berdasarkan matrix,
    dan mengirimkannya beserta lampiran serta menampilkan hasil ocr.
    """
    file_obj = getattr(instance, field_name, None)
    if not file_obj:
        return
     
    # ── Data waktu upload ──────────────────────────────────────
    uploaded_at = getattr(instance, f'{field_name}_uploaded_at', None)        
    local_time = timezone.localtime(uploaded_at) if uploaded_at else timezone.localtime(timezone.now())

    nama_hari_id = {
        'Monday': 'Senin', 'Tuesday': 'Selasa', 'Wednesday': 'Rabu',
        'Thursday': 'Kamis', 'Friday': 'Jumat', 'Saturday': 'Sabtu', 'Sunday': 'Minggu'
    }

    nama_bulan_id = {
        '01': 'Januari', '02': 'Februari', '03': 'Maret', '04': 'April',
        '05': 'Mei', '06': 'Juni', '07': 'Juli', '08': 'Agustus',
        '09': 'September', '10': 'Oktober', '11': 'November', '12': 'Desember'
    }

    hari_en = local_time.strftime('%A')
    hari_id = nama_hari_id.get(hari_en, '')
    tanggal_angka = int(local_time.strftime('%d'))
    bulan_angka = local_time.strftime('%m')
    bulan_id = nama_bulan_id.get(bulan_angka, '')
    tahun_str = local_time.strftime('%Y')

    tanggal_str = f"{hari_id}, {tanggal_angka} {bulan_id} {tahun_str}"
    jam_str = local_time.strftime('%H:%M')

    # ── Data pengupload ──────────────────────────────────────────
    if hasattr(instance, 'updated_by') and instance.updated_by:
        user_pengupload = instance.updated_by.get_full_name() or instance.updated_by.username
    else:
        user_pengupload = "System Administrator"
                
    # ── Deteksi CN_SAP secara dinamis berdasarkan model ─────────
    if hasattr(instance, 'asset') and instance.asset:
        cn_sap = instance.asset.CN_SAP
    elif hasattr(instance, 'CN_SAP'):
        cn_sap = instance.CN_SAP
    else:
        cn_sap = "-"
     
    nama_dokumen_display = nama_dok_ocr if nama_dok_ocr else field_name.replace('_', ' ').upper()

    # ── Penerima email ─────────────────────────────────────────
    filters = {'is_active': True, filter_notif_field: True}
    email_query = KaryawanPenerimaNotifikasi.objects.filter(**filters).values_list("email", flat=True)        
    email_tujuan = list(email_query)

    if not email_tujuan:
        print(f"--> [WARNING] Email tidak dikirim untuk {cn_sap} karena daftar penerima '{filter_notif_field}' kosong.")
        return

    subjek_email = f"[SI-MASTER NOTIFICATION] Dokumen {nama_dokumen_display} {cn_sap} Telah Diupload"  

    context = {
        'nama_dokumen': nama_dokumen_display,
        'cn_sap': cn_sap,
        'user_pengupload': user_pengupload,
        'tanggal_str': tanggal_str,
        'jam_str': jam_str,
        'field_name': field_name,
        'ocr_valid': ocr_valid,
        'nama_dok_ocr': nama_dok_ocr,
        'no_dokumen': no_dokumen,
        'usd_max': usd_max,
        'ocr_message': ocr_message,
        'egi_db': getattr(instance, 'EGI', '-') or '-',
        'sn_db': getattr(instance, 'SN', '-') or '-',
        'ocr_depan': ocr_depan,
        'ocr_belakang': ocr_belakang,
        'ocr_kanan': ocr_kanan,
        'ocr_kiri': ocr_kiri,
    }

    try:
        pesan_konten = render_to_string('emails/notifikasi_ocr.html', context)
    except Exception as e:
        print(f" --> [ERROR] Gagal merender template HTML email: {str(e)}")
        return

    try:
        email = EmailMessage(
            subject=subjek_email,
            body=pesan_konten,
            from_email=settings.EMAIL_HOST_USER,
            to=email_tujuan,
        )

        if hasattr(file_obj, 'path') and os.path.exists(file_obj.path):
            email.attach_file(file_obj.path)

        email.content_subtype = "html"
        email.send(fail_silently=False)

        print(f" ---> [SUCCESS] Email notifikasi {nama_dokumen_display} {cn_sap} berhasil dikirim ke {email_tujuan}")
    except Exception as e:
        print(f" --> [ERROR] Gagal mengirim email notifikasi untuk {cn_sap}: {str(e)} ")


# ── DETEKSI PEMICU (RECEIVERS) ────────────────────────────────────────────────

# 1. Untuk Model Breakdown
@receiver(post_save, sender=AssetEquipmentBreakdown)
def notif_breakdown(sender, instance, **kwargs):
    proses_dan_kirim_email(instance, 'ba_breakdown', 'notif_ba_breakdown')


# 2. Untuk Model Standby
@receiver(post_save, sender=AssetEquipmentStandby)
def notif_standby(sender, instance, **kwargs):
    proses_dan_kirim_email(instance, 'ba_standby', 'notif_ba_standby')


# 3. Untuk Model Disposed
@receiver(post_save, sender=AssetEquipmentDisposed)
def notif_disposed(sender, instance, created, **kwargs):
    dokumen_disposed_map = {
        'foto_4_sisi'        : 'notif_foto_4_sisi',
        'inspeksi_unit'      : 'notif_inspeksi',
        'rca'                : 'notif_rca',
        'pengajuan_disposed' : 'notif_pengajuan_disposed',
        'lampiran_capex'     : 'notif_lampiran_capex',
        'pde'                : 'notif_pde',
        'summary_pde'        : 'notif_summary_pde',
    }

    update_fields = kwargs.get('update_fields')

    if update_fields:
        for field_db, field_notif in dokumen_disposed_map.items():
            if field_db in update_fields:
                ocr_valid    = getattr(instance, '_ocr_valid', None)
                ocr_message  = getattr(instance, '_ocr_message', "Dokumen berhasil diproses")
                no_dokumen   = getattr(instance, '_no_dokumen', None)
                nama_dok_ocr = getattr(instance, '_nama_dok_ocr', None)
                usd_max      = getattr(instance, '_usd_max', None)
                ocr_depan    = getattr(instance, '_ocr_depan', True)
                ocr_belakang = getattr(instance, '_ocr_belakang', True)
                ocr_kanan    = getattr(instance, '_ocr_kanan', True)
                ocr_kiri     = getattr(instance, '_ocr_kiri', True)                

                proses_dan_kirim_email(
                    instance, field_db, field_notif, 
                    ocr_valid=ocr_valid, ocr_message=ocr_message, no_dokumen=no_dokumen, 
                    nama_dok_ocr=nama_dok_ocr, usd_max=usd_max,
                    ocr_depan=ocr_depan, ocr_belakang=ocr_belakang, ocr_kanan=ocr_kanan, ocr_kiri=ocr_kiri
                )
    else:
        for field_db, field_notif in dokumen_disposed_map.items():
            if field_db in ['rca', 'pengajuan_disposed', 'foto_4_sisi', 'inspeksi_unit']:
                continue

            file_obj = getattr(instance, field_db, None)
            if file_obj:
                uploaded_at = getattr(instance, f'{field_db}_uploaded_at', None)
                if uploaded_at:
                    selisih = (timezone.now() - uploaded_at).total_seconds()
                    if selisih < 10:
                        ocr_valid    = getattr(instance, '_ocr_valid', None)
                        ocr_message  = getattr(instance, '_ocr_message', "Dokumen berhasil diproses")
                        no_dokumen   = getattr(instance, '_no_dokumen', None)
                        nama_dok_ocr = getattr(instance, '_nama_dok_ocr', None)
                        usd_max      = getattr(instance, '_usd_max', None)
                        ocr_depan    = getattr(instance, '_ocr_depan', True)
                        ocr_belakang = getattr(instance, '_ocr_belakang', True)
                        ocr_kanan    = getattr(instance, '_ocr_kanan', True)
                        ocr_kiri     = getattr(instance, '_ocr_kiri', True)

                        proses_dan_kirim_email(
                            instance, field_db, field_notif, 
                            ocr_valid=ocr_valid, ocr_message=ocr_message, no_dokumen=no_dokumen, 
                            nama_dok_ocr=nama_dok_ocr, usd_max=usd_max, 
                            ocr_depan=ocr_depan, ocr_belakang=ocr_belakang, ocr_kanan=ocr_kanan, ocr_kiri=ocr_kiri
                        )







import threading
from django.dispatch import receiver
from django.db.models.signals import post_save
from django.utils import timezone
from django.core.signing import TimestampSigner
from django.urls import reverse
from django.conf import settings
from .models import AssetEquipmentPrepareDisposed
from data.models import KaryawanPenerimaNotifikasi

signer = TimestampSigner()

# =========================================================================
# 1. SIGNAL & HANDLER: FORM FOTO 4 SISI (APPROVED & WAITING)
# =========================================================================

@receiver(post_save, sender=AssetEquipmentPrepareDisposed)
def notif_foto_4_sisi_status_change(sender, instance, created, **kwargs):
    if created:
        return

    status_foto = getattr(instance, 'foto_4_sisi_status', None)
    if not status_foto:
        return

    # ── JIKA STATUS: APPROVED ──
    if status_foto == 'APPROVED':
        approved_at = getattr(instance, 'foto_4_sisi_approved_at', None)
        if not approved_at:
            instance.foto_4_sisi_approved_at = timezone.now()
            sender.objects.filter(pk=instance.pk).update(foto_4_sisi_approved_at=instance.foto_4_sisi_approved_at)
            approved_at = instance.foto_4_sisi_approved_at

        if (timezone.now() - approved_at).total_seconds() < 60:
            email_thread = threading.Thread(
                target=proses_dan_kirim_email_approval_foto_4_sisi,
                args=(instance.pk,)
            )
            email_thread.daemon = True
            email_thread.start()

    # ── JIKA STATUS: WAITING (SUBMIT) ──
    elif status_foto == 'WAITING':
        submitted_at = getattr(instance, 'foto_4_sisi_submitted_at', None)
        if not submitted_at:
            instance.foto_4_sisi_submitted_at = timezone.now()
            sender.objects.filter(pk=instance.pk).update(foto_4_sisi_submitted_at=instance.foto_4_sisi_submitted_at)
            submitted_at = instance.foto_4_sisi_submitted_at

        if (timezone.now() - submitted_at).total_seconds() < 60:
            email_thread = threading.Thread(
                target=proses_dan_kirim_email_waiting_foto_4_sisi,
                args=(instance.pk,)
            )
            email_thread.daemon = True
            email_thread.start()


def proses_dan_kirim_email_approval_foto_4_sisi(instance_pk):
    from django.template.loader import render_to_string
    from django.core.mail import EmailMessage
    import os

    try:
        from asset.utils_ocr import generate_pdf_foto_4_sisi_file 
    except ImportError:
        generate_pdf_foto_4_sisi_file = None

    try:
        instance = AssetEquipmentPrepareDisposed.objects.filter(pk=instance_pk).first()
        if not instance:
            return

        cn_sap = instance.asset.CN_SAP if instance.asset else (getattr(instance, 'CN_SAP', '-'))
        
        filters = {'is_active': True, 'notif_pengajuan_disposed': True} 
        email_tujuan = list(KaryawanPenerimaNotifikasi.objects.filter(**filters).values_list("email", flat=True))     

        if not email_tujuan:
            return

        approved_at = instance.foto_4_sisi_approved_at or timezone.now()
        local_time = timezone.localtime(approved_at)
        
        nama_hari_id = {'Monday': 'Senin', 'Tuesday': 'Selasa', 'Wednesday': 'Rabu', 'Thursday': 'Kamis', 'Friday': 'Jumat', 'Saturday': 'Sabtu', 'Sunday': 'Minggu'}
        nama_bulan_id = {'01': 'Januari', '02': 'Februari', '03': 'Maret', '04': 'April', '05': 'Mei', '06': 'Juni', '07': 'Juli', '08': 'Agustus', '09': 'September', '10': 'Oktober', '11': 'November', '12': 'Desember'}
        
        tanggal_str = f"{nama_hari_id.get(local_time.strftime('%A'), '')}, {int(local_time.strftime('%d'))} {nama_bulan_id.get(local_time.strftime('%m'), '')} {local_time.strftime('%Y')}"
        jam_str = local_time.strftime('%H:%M')

        approved_by_user = instance.foto_4_sisi_approver.get_full_name() if instance.foto_4_sisi_approver else "Management"
        subjek_email = f"[SI-MASTER NOTIFICATION] Form Foto 4 Sisi Unit Disposed {cn_sap} Telah APPROVED"

        context = {
            'cn_sap': cn_sap,
            'egi_db': getattr(instance, 'EGI', '-') or '-',
            'sn_db': getattr(instance, 'SN', '-') or '-',
            'approved_by': approved_by_user,
            'tanggal_str': tanggal_str,
            'jam_str': jam_str,
        }

        pesan_konten = render_to_string('emails/notifikasi_form_digital_approved.html', context)
        email = EmailMessage(subject=subjek_email, body=pesan_konten, from_email=settings.EMAIL_HOST_USER, to=email_tujuan)

        pdf_file_path = None
        if generate_pdf_foto_4_sisi_file:
            try:
                generated_result = generate_pdf_foto_4_sisi_file(instance)
                if isinstance(generated_result, str) and os.path.exists(generated_result):
                    pdf_file_path = generated_result
                elif hasattr(generated_result, 'path') and os.path.exists(generated_result.path):
                    pdf_file_path = generated_result.path
            except Exception:
                pass

        if pdf_file_path and os.path.exists(pdf_file_path):
            email.attach_file(pdf_file_path)

        email.content_subtype = "html"
        email.send(fail_silently=False)

        if pdf_file_path and os.path.exists(pdf_file_path):
            try:
                os.remove(pdf_file_path)
            except Exception:
                pass
    except Exception as e:
        print(f" --> [ERROR] Gagal mengirim email approval foto 4 sisi: {str(e)}")


def proses_dan_kirim_email_waiting_foto_4_sisi(instance_pk):
    from django.template.loader import render_to_string
    from django.core.mail import EmailMessage

    try:
        instance = AssetEquipmentPrepareDisposed.objects.filter(pk=instance_pk).first()
        if not instance:
            return

        cn_sap = instance.asset.CN_SAP if instance.asset else (getattr(instance, 'CN_SAP', '-'))
        
        email_tujuan = []
        if getattr(instance, 'foto_4_sisi_approver', None) and instance.foto_4_sisi_approver.email:
            email_tujuan.append(instance.foto_4_sisi_approver.email)
        else:
            filters = {'is_active': True, 'notif_waiting_prepare': True}
            email_tujuan = list(KaryawanPenerimaNotifikasi.objects.filter(**filters).values_list("email", flat=True))

        if not email_tujuan:
            return

        submitted_at = instance.foto_4_sisi_submitted_at or timezone.now()
        local_time = timezone.localtime(submitted_at)
        
        nama_hari_id = {'Monday': 'Senin', 'Tuesday': 'Selasa', 'Wednesday': 'Rabu', 'Thursday': 'Kamis', 'Friday': 'Jumat', 'Saturday': 'Sabtu', 'Sunday': 'Minggu'}
        nama_bulan_id = {'01': 'Januari', '02': 'Februari', '03': 'Maret', '04': 'April', '05': 'Mei', '06': 'Juni', '07': 'Juli', '08': 'Agustus', '09': 'September', '10': 'Oktober', '11': 'November', '12': 'Desember'}
        
        tanggal_str = f"{nama_hari_id.get(local_time.strftime('%A'), '')}, {int(local_time.strftime('%d'))} {nama_bulan_id.get(local_time.strftime('%m'), '')} {local_time.strftime('%Y')}"
        jam_str = local_time.strftime('%H:%M')

        # PERBAIKAN DI SINI: Gunakan getattr yang aman untuk menghindari error jika nama field berbeda
        submitted_user = getattr(instance, 'foto_4_sisi_submitted_by', None) or getattr(instance, 'submitted_by', None)
        submitted_by_user = submitted_user.get_full_name() or submitted_user.username if submitted_user else "User"
        
        subjek_email = f"[ACTION REQUIRED] Permintaan Approval Foto 4 Sisi Unit Disposed - CN: {cn_sap}"

        token = signer.sign(str(cn_sap))
        base_url = getattr(settings, 'DOMAIN_URL', 'http://127.0.0.1:8001')
        
        approve_path = reverse('asset:email_approval_action', args=[cn_sap, 'approve'])
        reject_path = reverse('asset:email_approval_action', args=[cn_sap, 'reject'])
        
        approve_url = f"{base_url}{approve_path}?token={token}"
        reject_url = f"{base_url}{reject_path}?token={token}"

        context = {
            'cn_sap': cn_sap,
            'egi_db': getattr(instance, 'EGI', '-') or '-',
            'sn_db': getattr(instance, 'SN', '-') or '-',
            'submitted_by': submitted_by_user,
            'approver_name': instance.foto_4_sisi_approver.get_full_name() if instance.foto_4_sisi_approver else "Bapak/Ibu",
            'form_title': 'Form 4 Foto Disposed',
            'tanggal_str': tanggal_str,
            'jam_str': jam_str,
            'system_url': f"{base_url}/admin/asset/assetequipmentpreparedisposed/",
            'approve_url': approve_url,
            'reject_url': reject_url,
        }

        pesan_konten = render_to_string('emails/notif_message_approved.html', context)
        email = EmailMessage(subject=subjek_email, body=pesan_konten, from_email=settings.EMAIL_HOST_USER, to=email_tujuan)
        email.content_subtype = "html"
        email.send(fail_silently=False)
    except Exception as e:
        print(f" --> [ERROR] Gagal mengirim email waiting foto 4 sisi: {str(e)}")


# =========================================================================
# 2. SIGNAL & HANDLER: INSPEKSI UNIT (APPROVED & WAITING)
# =========================================================================

@receiver(post_save, sender=AssetEquipmentPrepareDisposed)
def notif_inspeksi_unit_status_change(sender, instance, created, **kwargs):
    if created:
        return

    status_inspeksi = getattr(instance, 'inspeksi_status', None)
    if not status_inspeksi:
        return

    # ── JIKA STATUS: APPROVED ──
    if status_inspeksi == 'APPROVED':
        approved_at = getattr(instance, 'inspeksi_approved_at', None)
        if not approved_at:
            instance.inspeksi_approved_at = timezone.now()
            sender.objects.filter(pk=instance.pk).update(inspeksi_approved_at=instance.inspeksi_approved_at)
            approved_at = instance.inspeksi_approved_at

        if (timezone.now() - approved_at).total_seconds() < 60:
            email_thread = threading.Thread(
                target=proses_dan_kirim_email_approval_inspeksi,
                args=(instance.pk,)
            )
            email_thread.daemon = True
            email_thread.start()

    # ── JIKA STATUS: WAITING (SUBMIT) ──
    elif status_inspeksi == 'WAITING':
        submitted_at = getattr(instance, 'inspeksi_submitted_at', None)
        if not submitted_at:
            instance.inspeksi_submitted_at = timezone.now()
            sender.objects.filter(pk=instance.pk).update(inspeksi_submitted_at=instance.inspeksi_submitted_at)
            submitted_at = instance.inspeksi_submitted_at

        if (timezone.now() - submitted_at).total_seconds() < 60:
            email_thread = threading.Thread(
                target=proses_dan_kirim_email_waiting_inspeksi,
                args=(instance.pk,)
            )
            email_thread.daemon = True
            email_thread.start()


def proses_dan_kirim_email_approval_inspeksi(instance_pk):
    from django.template.loader import render_to_string
    from django.core.mail import EmailMessage
    import os

    try:
        from asset.utils_ocr import generate_pdf_inspeksi_unit_file 
    except ImportError:
        generate_pdf_inspeksi_unit_file = None

    try:
        instance = AssetEquipmentPrepareDisposed.objects.filter(pk=instance_pk).first()
        if not instance:
            return

        cn_sap = instance.asset.CN_SAP if instance.asset else (getattr(instance, 'CN_SAP', '-'))
        
        filters = {'is_active': True, 'notif_pengajuan_disposed': True} 
        email_tujuan = list(KaryawanPenerimaNotifikasi.objects.filter(**filters).values_list("email", flat=True))     

        if not email_tujuan:
            return

        approved_at = instance.inspeksi_approved_at or timezone.now()
        local_time = timezone.localtime(approved_at)
        
        nama_hari_id = {'Monday': 'Senin', 'Tuesday': 'Selasa', 'Wednesday': 'Rabu', 'Thursday': 'Kamis', 'Friday': 'Jumat', 'Saturday': 'Sabtu', 'Sunday': 'Minggu'}
        nama_bulan_id = {'01': 'Januari', '02': 'Februari', '03': 'Maret', '04': 'April', '05': 'Mei', '06': 'Juni', '07': 'Juli', '08': 'Agustus', '09': 'September', '10': 'Oktober', '11': 'November', '12': 'Desember'}
        
        tanggal_str = f"{nama_hari_id.get(local_time.strftime('%A'), '')}, {int(local_time.strftime('%d'))} {nama_bulan_id.get(local_time.strftime('%m'), '')} {local_time.strftime('%Y')}"
        jam_str = local_time.strftime('%H:%M')

        approved_by_user = instance.inspeksi_approver.get_full_name() if instance.inspeksi_approver else "Management"
        subjek_email = f"[SI-MASTER NOTIFICATION] Form Check Sheet Inspeksi Unit {cn_sap} Telah APPROVED"

        context = {
            'cn_sap': cn_sap,
            'egi_db': getattr(instance, 'EGI', '-') or '-',
            'sn_db': getattr(instance, 'SN', '-') or '-',
            'approved_by': approved_by_user,
            'tanggal_str': tanggal_str,
            'jam_str': jam_str,
        }

        pesan_konten = render_to_string('emails/notifikasi_form_digital_approved.html', context)
        email = EmailMessage(subject=subjek_email, body=pesan_konten, from_email=settings.EMAIL_HOST_USER, to=email_tujuan)

        pdf_file_path = None
        if generate_pdf_inspeksi_unit_file:
            try:
                generated_result = generate_pdf_inspeksi_unit_file(instance)
                if isinstance(generated_result, str) and os.path.exists(generated_result):
                    pdf_file_path = generated_result
                elif hasattr(generated_result, 'path') and os.path.exists(generated_result.path):
                    pdf_file_path = generated_result.path
            except Exception:
                pass

        if pdf_file_path and os.path.exists(pdf_file_path):
            email.attach_file(pdf_file_path)

        email.content_subtype = "html"
        email.send(fail_silently=False)

        if pdf_file_path and os.path.exists(pdf_file_path):
            try:
                os.remove(pdf_file_path)
            except Exception:
                pass
    except Exception as e:
        print(f" --> [ERROR] Gagal mengirim email approval inspeksi: {str(e)}")


def proses_dan_kirim_email_waiting_inspeksi(instance_pk):
    from django.template.loader import render_to_string
    from django.core.mail import EmailMessage

    try:
        instance = AssetEquipmentPrepareDisposed.objects.filter(pk=instance_pk).first()
        if not instance:
            return

        cn_sap = instance.asset.CN_SAP if instance.asset else (getattr(instance, 'CN_SAP', '-'))
        
        email_tujuan = []
        if getattr(instance, 'inspeksi_approver', None) and instance.inspeksi_approver.email:
            email_tujuan.append(instance.inspeksi_approver.email)
        else:
            filters = {'is_active': True, 'notif_waiting_prepare': True}
            email_tujuan = list(KaryawanPenerimaNotifikasi.objects.filter(**filters).values_list("email", flat=True))

        if not email_tujuan:
            return

        submitted_at = instance.inspeksi_submitted_at or timezone.now()
        local_time = timezone.localtime(submitted_at)
        
        nama_hari_id = {'Monday': 'Senin', 'Tuesday': 'Selasa', 'Wednesday': 'Rabu', 'Thursday': 'Kamis', 'Friday': 'Jumat', 'Saturday': 'Sabtu', 'Sunday': 'Minggu'}
        nama_bulan_id = {'01': 'Januari', '02': 'Februari', '03': 'Maret', '04': 'April', '05': 'Mei', '06': 'Juni', '07': 'Juli', '08': 'Agustus', '09': 'September', '10': 'Oktober', '11': 'November', '12': 'Desember'}
        
        tanggal_str = f"{nama_hari_id.get(local_time.strftime('%A'), '')}, {int(local_time.strftime('%d'))} {nama_bulan_id.get(local_time.strftime('%m'), '')} {local_time.strftime('%Y')}"
        jam_str = local_time.strftime('%H:%M')

        submitted_user = getattr(instance, 'inspeksi_submitted_by', None)
        submitted_by_user = submitted_user.get_full_name() or submitted_user.username if submitted_user else "User"
        
        subjek_email = f"[ACTION REQUIRED] Permintaan Approval Check Sheet Inspeksi Unit - CN: {cn_sap}"

        token = signer.sign(str(cn_sap))
        base_url = getattr(settings, 'DOMAIN_URL', 'http://127.0.0.1:8001')
        
        approve_path = reverse('asset:email_approval_action', args=[cn_sap, 'approve'])
        reject_path = reverse('asset:email_approval_action', args=[cn_sap, 'reject'])
        
        approve_url = f"{base_url}{approve_path}?token={token}"
        reject_url = f"{base_url}{reject_path}?token={token}"

        context = {
            'cn_sap': cn_sap,
            'egi_db': getattr(instance, 'EGI', '-') or '-',
            'sn_db': getattr(instance, 'SN', '-') or '-',
            'submitted_by': submitted_by_user,
            'approver_name': instance.inspeksi_approver.get_full_name() if instance.inspeksi_approver else "Bapak/Ibu",
            'form_title': 'Form Check Sheet Inspeksi Unit',
            'tanggal_str': tanggal_str,
            'jam_str': jam_str,
            'system_url': f"{base_url}/admin/asset/assetequipmentpreparedisposed/",
            'approve_url': approve_url,
            'reject_url': reject_url,
        }

        pesan_konten = render_to_string('emails/notif_message_approved.html', context)
        email = EmailMessage(subject=subjek_email, body=pesan_konten, from_email=settings.EMAIL_HOST_USER, to=email_tujuan)
        email.content_subtype = "html"
        email.send(fail_silently=False)
    except Exception as e:
        print(f" --> [ERROR] Gagal mengirim email waiting inspeksi: {str(e)}")



