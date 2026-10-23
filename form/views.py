# inside/form/views.py

from django.shortcuts import render, redirect, get_object_or_404
from asset.admin import admin_site 
from django.forms import modelformset_factory
from django.contrib.auth.models import Group
from django.db.models import Count, Q
from django.urls import reverse
from django.views import View
from django.db import transaction
from django.contrib.auth.mixins import LoginRequiredMixin
from django.contrib.contenttypes.models import ContentType
from django.http import HttpResponseForbidden, HttpResponseBadRequest, JsonResponse
from django.contrib import messages
from datetime import date
from django.utils import timezone
from django.contrib.auth.decorators import login_required
from django.http import JsonResponse
from django.views.decorators.http import require_GET
from django.contrib import messages
from asset.models import AssetEquipment
from django.contrib.auth.decorators import login_required, permission_required
from django.http import HttpResponse
from django.template.loader import get_template
import io

# Import Forms dan Models
from .forms import (AssetSelectionForm, ChecksheetPIForm, ChecksheetItemForm,)
from .forms import LampiranCapexForm
from .models import (
    ApprovalStep, ApprovalLog,
    DOCUMENT_STATUS_CHOICES,
    FormPengajuanEquipmentDisposed,
    FormLampiranCapex,
    
)
from .models import ChecksheetPI, ChecksheetItem, FormBAStandby
from django.template.loader import get_template
from asset.models import AssetEquipmentDisposed
from data.models import checksheetmasterlist
import logging
logger = logging.getLogger(__name__)


# ============================================
# ====FIXED AND FINAL CODE====================
# ============================================

# MAPPING STATUS APPROVAL
STATUS_TRANSITIONS = {
    'DRAFT': 'SUB',
    'SUB': 'APR1',
    'APR1': 'APR2',
    'APR2': 'FIN',
}

STATUS_LIST_KEYS = list(STATUS_TRANSITIONS.keys()) # ['DRAFT', 'SUB', 'APR1', 'APR2']
DOCUMENT_MODEL_MAPPING = {
    'checksheet_pi': ChecksheetPI,
    'pde': FormPengajuanEquipmentDisposed,
    'capex': FormLampiranCapex,
}

# ------------------------------
# 3. Select Asset View
# ------------------------------
class SelectAssetView(View):
    """Halaman untuk memilih aset dan mengisi PIC/Atasan."""
    template_name = 'admin/select_asset.html'

    def get(self, request):
        cn_sap_from_url = request.GET.get('cn_sap')
        form = AssetSelectionForm(
            initial={'asset': cn_sap_from_url} if cn_sap_from_url else None
        )
        return render(request, self.template_name, {
            'form': form,
            'header': 'Pilih Aset untuk Inspeksi'
        })

    def post(self, request):
        form = AssetSelectionForm(request.POST)
        if form.is_valid():
            cn_sap = form.cleaned_data['asset']
            pic = form.cleaned_data['pic_inspector']
            atasan = form.cleaned_data['atasan_inspector']

            return redirect(
                reverse('form:create_checksheet') +
                f'?cn_sap={cn_sap}&pic={pic}&atasan={atasan}'
            )

        return render(request, self.template_name, {
            'form': form,
            'header': 'Pilih Aset untuk Inspeksi'
        })

# -----------------------------------------------------------
# 4. Detail Checksheet PI (Perbaikan context & level approval)
# -----------------------------------------------------------
class ChecksheetDetailView(View):
    template_name = 'admin/checksheet_detail.html'

    def get(self, request, pk):
        checksheet = get_object_or_404(ChecksheetPI, pk=pk)
        items = checksheet.items.all()

        total_items = items.count()
        good_count = items.filter(condition='G').count()
        bad_count = items.filter(condition='B').count()
        na_count = items.filter(Q(condition='N') | Q(condition__isnull=True)).count()

        valid_total = total_items if total_items > 0 else 1
        good_percent = round((good_count / valid_total) * 100, 2)
        bad_percent = round((bad_count / valid_total) * 100, 2)
        na_percent = round((na_count / valid_total) * 100, 2)
        condition_status = "Good" if good_percent >= 71 else "Bad"

        # Tentukan siapa yang sedang bertanggung jawab approve
        current_status_key = checksheet.status
        approving_step = None
        is_current_approver = False
        required_urutan = 0

        # Tentukan level approval yang aktif. 
        # required_urutan = index status saat ini.
        try:
            current_status_index = STATUS_LIST_KEYS.index(current_status_key)
            # 💡 PERBAIKAN LOGIKA: Approval Step untuk 'SUB' adalah urutan 1 (indeks 1). 
            # Approval Step untuk 'APR1' adalah urutan 2 (indeks 2).
            required_urutan = current_status_index
        except ValueError:
            # Status DRAFT, FIN atau REJ tidak memiliki urutan berikutnya yang aktif
            required_urutan = 0
            
        if 0 < required_urutan <= len(STATUS_TRANSITIONS):
            try:
                # ✅ FIX: Menggunakan required_urutan yang sudah benar
                approving_step = ApprovalStep.objects.get(urutan=required_urutan)
                required_group = approving_step.penanggung_jawab_group
                is_current_approver = request.user.groups.filter(pk=required_group.pk).exists()
            except ApprovalStep.DoesNotExist:
                messages.warning(request, f"Langkah Approval Urutan {required_urutan} belum dikonfigurasi di database.")
                pass

        # Ambil log approval
        content_type = ContentType.objects.get_for_model(checksheet)
        approval_history = ApprovalLog.objects.filter(
            content_type=content_type,
            object_id=pk
        ).order_by('tanggal_persetujuan')

        context = {
            'checksheet': checksheet,
            'items': items,
            'total_items': total_items,
            'good_count': good_count,
            'bad_count': bad_count,
            'na_count': na_count,
            'good_percent': good_percent,
            'bad_percent': bad_percent,
            'na_percent': na_percent,
            'condition_status': condition_status,
            'approving_step': approving_step,
            'is_current_approver': is_current_approver,
            'approval_history': approval_history,
        }

        # Tambahkan durasi setelah context ada
        if checksheet.submitted_at:
            duration = timezone.now() - checksheet.submitted_at
            context["duration_at_current_step"] = str(duration).split('.')[0]

        return render(request, self.template_name, context)


# ------------------------------
# 5. Create Checksheet View
# ------------------------------
class CreateChecksheetView(View):
    """Halaman untuk membuat Checksheet baru."""
    template_name = 'admin/create_checksheet.html'

    def get(self, request):
        cn_sap = request.GET.get('cn_sap', '').strip()
        pic = request.GET.get('pic')
        atasan = request.GET.get('atasan')

        if not cn_sap:
            messages.error(request, "Nomor Aset (CN_SAP) tidak ditemukan. Silakan pilih aset terlebih dahulu.")
            return redirect(reverse('form:select_asset'))

        try:
            asset = get_object_or_404(AssetEquipmentDisposed, CN_SAP=cn_sap)
        except Exception:
            messages.error(request, f"Aset dengan CN_SAP '{cn_sap}' tidak ditemukan.")
            return redirect(reverse('form:select_asset'))

        # --- Data Header ---
        initial_header_data = {
            'cn_sap': asset.CN_SAP,
            'egi': asset.EGI,
            'hm_smr': asset.HM_SMR,
            'pic_inspector': pic,
            'atasan_inspector': atasan,
        }

        egi_clean = asset.EGI.strip() if asset.EGI else ''
        master_items = checksheetmasterlist.objects.filter(EGI__iexact=egi_clean)

        warning = None
        if not master_items.exists():
            warning = f"Tidak ada item master yang cocok untuk EGI '{egi_clean}'"

        extra_forms = master_items.count()

        ChecksheetItemFormSet = modelformset_factory(
            ChecksheetItem,
            form=ChecksheetItemForm,
            extra=extra_forms,
            can_delete=False
        )

        initial_data = [
            {
                'category': item.CATEGORY,
                'item_name': item.ITEM,
                'qty': item.QTY,
                'condition': 'G',
                'remarks': '',
            }
            for item in master_items
        ]

        formset = ChecksheetItemFormSet(queryset=ChecksheetItem.objects.none(), initial=initial_data, prefix='items')
        header_form = ChecksheetPIForm(initial=initial_header_data)

        context = {
            'header_form': header_form,
            'formset': formset,
            'asset': asset,
            'cn_sap': cn_sap,
            'pic': pic,
            'atasan': atasan,
            'header': f'Form Checksheet untuk {cn_sap}',
            'warning': warning,
        }
        return render(request, self.template_name, context)

    def post(self, request):
        cn_sap = request.GET.get('cn_sap')
        pic = request.GET.get('pic')
        atasan = request.GET.get('atasan')

        try:
            asset = get_object_or_404(AssetEquipmentDisposed, CN_SAP=cn_sap)
        except Exception:
            messages.error(request, f"Aset dengan CN_SAP '{cn_sap}' tidak ditemukan saat menyimpan.")
            return redirect(reverse('form:select_asset'))
            
        # Perbaikan: Membangun data POST dengan field hidden/read-only dari URL/DB
        post_data_with_header = request.POST.copy()
        post_data_with_header['cn_sap'] = asset.CN_SAP
        post_data_with_header['egi'] = asset.EGI
        post_data_with_header['hm_smr'] = asset.HM_SMR
        post_data_with_header['pic_inspector'] = pic
        post_data_with_header['atasan_inspector'] = atasan

        # Validasi Form Header
        header_form = ChecksheetPIForm(post_data_with_header) 

        # Siapkan Formset Item
        master_items = checksheetmasterlist.objects.filter(EGI__iexact=asset.EGI.strip() if asset.EGI else '')
        extra_forms = master_items.count()
        ChecksheetItemFormSet = modelformset_factory(ChecksheetItem, form=ChecksheetItemForm, extra=extra_forms)
        formset = ChecksheetItemFormSet(request.POST, queryset=ChecksheetItem.objects.none(), prefix='items')
        
        
        # Cek validitas kedua form: Header dan Item
        if header_form.is_valid() and formset.is_valid():
            with transaction.atomic():
                # 1. Simpan Header ChecksheetPI
                checksheet_instance = header_form.save(commit=False)
                checksheet_instance.status = 'DRAFT'
                # Jika Anda memiliki field seperti created_by, tambahkan di sini:
                # checksheet_instance.created_by = request.user 
                checksheet_instance.save() 

                # 2. Simpan Item ChecksheetItem
                instances = formset.save(commit=False)
                for instance in instances:
                    instance.checksheet_pi = checksheet_instance
                ChecksheetItem.objects.bulk_create(instances)

                messages.success(request, f"Checksheet {cn_sap} berhasil dibuat. Silakan submit untuk persetujuan.")
                return render(request, 'admin/create_checksheet.html', {
                    'header_form': header_form,
                    'formset': formset,
                    'checksheet_saved': checksheet_instance, 
                    'cn_sap': cn_sap,
                    'pic': pic,
                    'atasan': atasan,
                    'header': f'Form Checksheet untuk {cn_sap}',
                })

        # Jika tidak valid, re-render form dengan error
        messages.error(request, "Gagal menyimpan checksheet. Terdapat kesalahan pada input.")
        
        context = {
            'header_form': header_form,
            'formset': formset,
            'asset': asset,
            'cn_sap': cn_sap,
            'pic': pic,
            'atasan': atasan,
            'header': f'Form Checksheet untuk {cn_sap}',
        }
        return render(request, self.template_name, context)

# -----------------------------------------------------------
# 6. Process Approval/Rejection View (PERBAIKAN FINAL)
# -----------------------------------------------------------
class ProcessApprovalView(LoginRequiredMixin, View):
    def post(self, request, document_type, pk):
        ModelClass = DOCUMENT_MODEL_MAPPING.get(document_type)
        if not ModelClass:
            return HttpResponseBadRequest("Tipe dokumen tidak valid.")

        document = get_object_or_404(ModelClass, pk=pk)
        current_status = document.status
        action = request.POST.get('action')
        notes = request.POST.get('notes', '')
        user = request.user

        if action not in ['approve', 'reject', 'submit']:
            return HttpResponseBadRequest("Aksi tidak valid.")

        redirect_url = reverse('form:checksheet_detail', args=[document.pk])
        content_type = ContentType.objects.get_for_model(document)

        try:
            with transaction.atomic():
                # === 1️⃣ SUBMIT (DRAFT → SUB) ===
                if action == 'submit':
                    if current_status != 'DRAFT':
                        messages.warning(request, "Dokumen sudah diajukan.")
                        return redirect(redirect_url)

                    document.status = 'SUB'
                    document.submitted_at = timezone.now()
                    document.diajukan_oleh = user
                    document.save(update_fields=['status', 'submitted_at', 'diajukan_oleh'])

                    # Langkah Approval Pertama (urutan=1) harus dibuat lognya.
                    step = ApprovalStep.objects.filter(urutan=1).first() 
                    ApprovalLog.objects.create(
                        content_type=content_type,
                        object_id=document.pk,
                        langkah=step, # Menggunakan langkah approval pertama
                        approved_by=user,
                        action='SUBMIT',
                        komentar=notes,
                        tanggal_persetujuan=timezone.now(), # Tambahkan tanggal persetujuan
                    )

                    messages.success(request, "✅ Dokumen berhasil diajukan ke Level 1.")
                    return redirect(redirect_url)

                # === 2️⃣ APPROVE / REJECT (SUB, APR1, APR2) ===
                if current_status in ['SUB', 'APR1', 'APR2']:
                    
                    # 💡 PERBAIKAN KRITIS: Mengambil langkah persetujuan yang sesuai dengan status saat ini.
                    # Status 'SUB' memiliki indeks 1, yang harus diselesaikan oleh ApprovalStep urutan 1.
                    required_urutan = STATUS_LIST_KEYS.index(current_status) 
                    
                    step = ApprovalStep.objects.filter(urutan=required_urutan).first()

                    if not step:
                        messages.error(request, f"Langkah approval urutan **{required_urutan}** belum dikonfigurasi. (Status: {current_status})")
                        return redirect(redirect_url)

                    if not user.groups.filter(pk=step.penanggung_jawab_group.pk).exists():
                        messages.error(request, f"Anda bukan penanggung jawab (Grup: {step.penanggung_jawab_group.name}) untuk langkah ini.")
                        return redirect(redirect_url)

                    if action == 'approve':
                        next_status = STATUS_TRANSITIONS.get(current_status, 'FIN')
                        update_fields_list = ['status']
                        if next_status == 'FIN':
                            document.finalized_at = timezone.now()
                            update_fields_list.append('finalized_at')

                        document.status = next_status
                        document.save(update_fields=update_fields_list)
                        
                        ApprovalLog.objects.create(
                            content_type=content_type,
                            object_id=document.pk,
                            langkah=step,
                            approved_by=user,
                            action='APPROVED',
                            komentar=notes,
                            tanggal_persetujuan=timezone.now(),
                        )
                        messages.success(request, f"✅ Dokumen disetujui. Status sekarang: {next_status}.")
                        return redirect(redirect_url)

                    elif action == 'reject':
                        document.status = 'REJ'
                        document.save(update_fields=['status'])
                        ApprovalLog.objects.create(
                            content_type=content_type,
                            object_id=document.pk,
                            langkah=step,
                            approved_by=user,
                            action='REJECTED',
                            komentar=notes,
                            tanggal_persetujuan=timezone.now(), # Tambahkan tanggal persetujuan
                        )
                        messages.warning(request, "❌ Dokumen ditolak dan dikembalikan ke pengaju.")
                        return redirect(redirect_url)

        except Exception as e:
            logger.error(f"Error di ProcessApprovalView: {e}")
            messages.error(request, "Terjadi kesalahan saat memproses approval. Silakan cek log server.")
            return redirect(redirect_url)

        # Tambahan jaga-jaga
        return redirect(redirect_url)

    
# -----------------------------------------------------------
# 7. Process Resubmit
# -----------------------------------------------------------    

class ResubmitChecksheetView(LoginRequiredMixin, View):
    """
    Mengubah status dokumen dari REJ (Rejected) kembali ke SUB (Submitted).
    Aksi ini hanya boleh dilakukan oleh Pengaju (diajukan_oleh).
    """
    def post(self, request, pk):
        document = get_object_or_404(ChecksheetPI, pk=pk)
        
        redirect_url = reverse('form:checksheet_detail', kwargs={'pk': pk})

        # --- VALIDASI KRITIS ---
        # 1. Pastikan user yang login adalah pembuat/pengaju dokumen.
        if document.diajukan_oleh != request.user:
            messages.error(request, "Anda tidak memiliki izin untuk mengajukan ulang dokumen ini.")
            return redirect(redirect_url)

        # 2. Pastikan status dokumen benar-benar REJ.
        if document.status != 'REJ':
            messages.error(request, f"Dokumen tidak dapat diajukan ulang karena status saat ini adalah {document.status}.")
            return redirect(redirect_url)
        
        # --- PROSES RESUBMIT ---
        try:
            document.status = 'SUB' 
            document.submitted_at = timezone.now()
            document.save(update_fields=['status', 'submitted_at'])
            
            # Opsional: Mencatat log RESUBMITTED (Bagus untuk Audit Trail)
            content_type = ContentType.objects.get_for_model(document)
            step = ApprovalStep.objects.filter(urutan=1).first() # Kembali ke Level 1
            ApprovalLog.objects.create(
                content_type=content_type,
                object_id=document.pk,
                langkah=step,
                approved_by=request.user,
                action='RESUBMITTED',
                komentar=request.POST.get('notes', 'Mengajukan ulang setelah ditolak.'),
                tanggal_persetujuan=timezone.now(),
            )
            
            messages.success(request, "✅ Dokumen berhasil diajukan ulang (Resubmit) dan masuk kembali ke antrian persetujuan Level 1.")
            
        except Exception as e:
            messages.error(request, f"Terjadi kesalahan sistem saat mengajukan ulang: {e}")
            return redirect(redirect_url) 
            
        return redirect(redirect_url)

# -----------------------------------------------------------
# 8. Update checksheetview
# -----------------------------------------------------------   

class UpdateChecksheetView(LoginRequiredMixin, View):
    # PERUBAHAN/REFINEMENT: 
    # Mengubah nama template agar lebih sesuai dengan lokasi file: 
    # inside/form/templates/admin/edit_checksheet.html
    template_name = 'admin/edit_checksheet.html' 

    def get_checksheet_formset(self, checksheet=None, data=None):
        ChecksheetItemFormSet = modelformset_factory(
            ChecksheetItem, 
            form=ChecksheetItemForm, 
            extra=0, # Jangan tambahkan baris baru secara default
            can_delete=False # Item Checksheet tidak boleh dihapus
        )
        # Jika dokumen sudah ada, gunakan queryset yang sudah ada
        queryset = ChecksheetItem.objects.filter(checksheet_pi=checksheet) if checksheet else ChecksheetItem.objects.none()
        
        # PENAMBAHAN: Menentukan prefix untuk formset agar tidak bertabrakan dengan header form
        return ChecksheetItemFormSet(data=data, queryset=queryset, prefix='item') 


    def dispatch(self, request, pk, *args, **kwargs):
        # 1. Ambil Dokumen dan Lakukan Pemeriksaan Dasar
        checksheet = get_object_or_404(ChecksheetPI, pk=pk)
        
        # Otorisasi: Hanya user yang mengajukan dokumen yang bisa mengedit
        if checksheet.diajukan_oleh and checksheet.diajukan_oleh != request.user:
            messages.error(request, "Anda tidak memiliki izin untuk mengedit dokumen ini.")
            return redirect(reverse('form:checksheet_detail', kwargs={'pk': pk}))
            
        # Status Validasi: Hanya DRAFT atau REJECTED (REJ) yang bisa diedit
        if checksheet.status not in ['DRAFT', 'REJ']:
            messages.warning(request, f"Dokumen dengan status '{checksheet.status}' tidak bisa diedit.")
            return redirect(reverse('form:checksheet_detail', kwargs={'pk': pk}))
            
        self.checksheet = checksheet # Simpan instance untuk digunakan di get/post
        return super().dispatch(request, pk, *args, **kwargs)

    
    def get(self, request, pk):
        checksheet = self.checksheet # Ambil instance dari dispatch
        
        # 1. Inisialisasi Header Form dengan data instance
        header_form = ChecksheetPIForm(instance=checksheet)
        
        # 2. Inisialisasi Item Formset dengan queryset item yang sudah ada
        formset = self.get_checksheet_formset(checksheet=checksheet)
        
        context = {
            'header_form': header_form,
            'formset': formset,
            'checksheet': checksheet,
            'header': f'Edit Checksheet untuk {checksheet.cn_sap}',
        }
        return render(request, self.template_name, context)

    
    def post(self, request, pk):
        checksheet = self.checksheet # Ambil instance dari dispatch
        
        # 1. Bind Header Form dengan data POST dan instance
        header_form = ChecksheetPIForm(request.POST, instance=checksheet)
        
        # 2. Bind Item Formset dengan data POST dan queryset yang sudah ada
        formset = self.get_checksheet_formset(checksheet=checksheet, data=request.POST)

        if header_form.is_valid() and formset.is_valid():
            try:
                with transaction.atomic():
                    # Simpan Header (akan mengupdate instance 'checksheet')
                    checksheet_instance = header_form.save() 
                    
                    # Simpan Item Formset (akan mengupdate item-item yang sudah ada)
                    formset.save() 
                    
                    messages.success(request, f"✅ Checksheet {checksheet.cn_sap} berhasil diperbarui.")
                    
                    # Redirect kembali ke halaman detail
                    return redirect(reverse('form:checksheet_detail', kwargs={'pk': checksheet_instance.pk}))

            except Exception as e:
                logger.error(f"Error saat menyimpan UpdateChecksheetView: {e}")
                messages.error(request, "❌ Gagal menyimpan perubahan. Terjadi kesalahan sistem.")
        
        # Jika tidak valid, re-render form dengan error
        messages.error(request, "Terdapat kesalahan pada input. Silakan cek kembali item yang diisi.")
        context = {
            'header_form': header_form,
            'formset': formset,
            'checksheet': checksheet,
            'header': f'Edit Checksheet untuk {checksheet.cn_sap}',
        }
        return render(request, self.template_name, context)
    


# ── AJAX lookup CN SAP → data AssetEquipment ──────────────────────────────
@login_required
@require_GET
def ajax_asset_lookup(request):

    """
    Lookup data asset dari multiple sumber:
    - AssetEquipment : data identitas unit
    - AR01           : NILAI_AKUISISI (acquisition_value) dan NBV (book_value)
                       diagregasi dengan SUM per CN_SAP (type_name)
    """

    from django.db.models import Sum
    from data.models import AR01
    


    cn_sap = request.GET.get('cn_sap', '').strip()
    if not cn_sap:
        return JsonResponse({'found': False, 'error': 'CN SAP kosong'})


    # ── 1. Data dari AssetEquipment ──────────────────────────
    try:
        # ✅ Lookup dari AssetEquipment (bukan Disposed)
        asset = AssetEquipment.objects.get(CN_SAP=cn_sap)
    except AssetEquipment.DoesNotExist:
        return JsonResponse({
            'found': False,
            'error': f"CN SAP '{cn_sap}' tidak ditemukan"
        })

    # ── 2. Data dari AR01 — agregasi SUM per type_name ───────
    # type_name di AR01 = CN_SAP di AssetEquipment

    ar01_aggregated = AR01.objects.filter(
        type_name=cn_sap
    ).aggregate(
        total_acquisition_value = Sum('acquisition_value'),
        total_book_value        = Sum('book_value'),
    )

    # Ambil hasil agregasi, default 0 jika tidak ada data
    nilai_akuisisi = ar01_aggregated['total_acquisition_value'] or 0
    nbv            = ar01_aggregated['total_book_value']        or 0


    # ── 3. Return JSON gabungan ───────────────────────────────
    return JsonResponse({
        'found': True,
        'data': {
            # Dari AssetEquipment
            'CN_SAP':         asset.CN_SAP,
            'No_Asset':       asset.No_Asset       or '',
            'GROUP':          asset.GROUP           or '',
            'TYPE':           asset.TYPE            or '',
            'EGI':            asset.EGI             or '',
            'HM_SMR':         str(asset.HM_SMR)     if asset.HM_SMR else '',
            'SPO_EQUIPMENT':  str(asset.SPO_EQUIPMENT) if asset.SPO_EQUIPMENT else '',
            'PERSENTASE_SPO': str(asset.PERSENTASE_SPO) if asset.PERSENTASE_SPO else '',
            'LOCATION':       asset.LOCATION        or '',
            'SUB_LOCATION':   asset.SUB_LOCATION    or '',
            'BRAND':          asset.BRAND           or '',
            'SN':             asset.SN              or '',

            # Dari AR01 (sudah diagregasi)
            'NILAI_AKUISISI': str(nilai_akuisisi),
            'NBV':            str(nbv),

            # Sumber info untuk debugging (opsional, bisa dihapus)
            '_ar01_rows_count': AR01.objects.filter(type_name=cn_sap).count(),
        }
    })

# ── Helper: submit otomatis ke approval ───────────────────────────────────
def _auto_submit_to_approval(instance, user):
    """
    Setelah form dibuat, langsung submit ke approval step pertama.
    Status berubah dari DRAFT → SUB, dan ApprovalLog dibuat.
    """
    # Ambil approval step pertama (urutan=1)
    try:
        first_step = ApprovalStep.objects.get(urutan=1)
    except ApprovalStep.DoesNotExist:
        # Jika belum ada approval step, tetap DRAFT
        return False

    # Update status form
    instance.status = 'SUB'
    instance.submitted_at = timezone.now()
    instance.diajukan_oleh = user
    instance.save()

    # Catat di ApprovalLog
    content_type = ContentType.objects.get_for_model(instance)
    ApprovalLog.objects.create(
        content_type=content_type,
        object_id=instance.pk,
        langkah=first_step,
        approved_by=user,
        action='SUBMIT',
        komentar='Auto-submitted oleh sistem saat form dibuat.',
    )
    return True


# ── Helper: cek apakah user boleh create form ─────────────────────────────
def _user_can_create_form(user):
    """
    Cek apakah user termasuk group yang boleh membuat form.
    Sesuaikan nama group dengan yang ada di database Anda.
    """
    ALLOWED_GROUPS = ['PIC Asset', 'Supervisor Asset', 'Staff Asset']
    # Superuser selalu boleh
    if user.is_superuser:
        return True
    return user.groups.filter(name__in=ALLOWED_GROUPS).exists()


# ── Create FormLampiranCapex ───────────────────────────────────────────────
@login_required
def lampiran_capex_create(request):
    if not _user_can_create_form(request.user):
        messages.error(request, "Anda tidak memiliki akses untuk membuat form ini.")
        return redirect('inside_admin:asset_assetequipmentdisposed_changelist')

    initial_cn_sap = request.GET.get('cn_sap', '').strip()

    if initial_cn_sap:
        existing = FormLampiranCapex.objects.filter(CN_SAP=initial_cn_sap).first()
        if existing:
            messages.warning(
                request,
                f"Form Lampiran Capex untuk {initial_cn_sap} sudah ada. "
                f"Anda diarahkan ke halaman detail."
            )
            return redirect('form:lampiran_capex_detail', pk=existing.pk)

    if request.method == 'POST':
        # ✅ Ambil CN_SAP dari POST
        cn_sap_post = request.POST.get('CN_SAP', '').strip()

        # ✅ Ambil data auto-fill langsung dari database
        # Tidak mengandalkan field readonly dari HTML yang tidak terkirim
        try:
            asset = AssetEquipment.objects.get(CN_SAP=cn_sap_post)
        except AssetEquipment.DoesNotExist:
            messages.error(request, f"CN SAP '{cn_sap_post}' tidak ditemukan.")
            form = LampiranCapexForm(request.POST)
            return render(request, 'form/lampiran_capex_form.html', {
                'form': form,
                'initial_cn_sap': cn_sap_post,
                'title': 'Buat Form Lampiran Capex',
            })

        # ✅ Gabungkan POST data dengan data dari database
        post_data = request.POST.copy()
        post_data['CN_SAP']         = asset.CN_SAP
        post_data['GROUP']          = asset.GROUP or ''
        post_data['TYPE']           = asset.TYPE or ''
        post_data['EGI']            = asset.EGI or ''
        post_data['HM_SMR']         = str(asset.HM_SMR) if asset.HM_SMR else '0'
        post_data['SPO_EQUIPMENT']  = str(asset.SPO_EQUIPMENT) if asset.SPO_EQUIPMENT else ''
        post_data['PERSENTASE_SPO'] = str(asset.PERSENTASE_SPO) if asset.PERSENTASE_SPO else '0'

        form = LampiranCapexForm(post_data)
        if form.is_valid():
            instance = form.save(commit=False)
            instance.diajukan_oleh = request.user
            instance.status = 'DRAFT'
            instance.save()

            submitted = _auto_submit_to_approval(instance, request.user)

            if submitted:
                messages.success(
                    request,
                    f"Form Lampiran Capex {instance.CN_SAP} berhasil dibuat "
                    f"dan otomatis disubmit ke approval."
                )
            else:
                messages.warning(
                    request,
                    f"Form Lampiran Capex {instance.CN_SAP} berhasil dibuat "
                    f"sebagai DRAFT. Approval step belum dikonfigurasi."
                )
            return redirect('form:lampiran_capex_detail', pk=instance.pk)
        else:
            # ✅ Tampilkan error dengan initial_cn_sap agar form bisa re-lookup
            messages.error(request, "Periksa kembali isian form.")
            return render(request, 'form/lampiran_capex_form.html', {
                'form': form,
                'initial_cn_sap': cn_sap_post,
                'title': 'Buat Form Lampiran Capex',
            })
    else:
        form = LampiranCapexForm(initial_cn_sap=initial_cn_sap)

    return render(request, 'form/lampiran_capex_form.html', {
        'form': form,
        'initial_cn_sap': initial_cn_sap,
        'title': 'Buat Form Lampiran Capex',
    })


# ✅ VERSI BARU — pakai ini
# ── Detail / Lihat FormLampiranCapex ──────────────────────────────────────
@login_required
def lampiran_capex_detail(request, pk):
    instance = get_object_or_404(FormLampiranCapex, pk=pk)

    content_type = ContentType.objects.get_for_model(instance)
    logs = ApprovalLog.objects.filter(
        content_type=content_type,
        object_id=instance.pk,
    ).order_by('tanggal_persetujuan')

    # ✅ Tambahan ini yang membuat template tidak error
    autofill_display = [
        ('CN SAP',        instance.CN_SAP),
        ('Class (GROUP)', instance.GROUP),
        ('Type',          instance.TYPE),
        ('EGI',           instance.EGI),
        ('Hour Meter',    instance.HM_SMR),
        ('SPO Equipment', instance.SPO_EQUIPMENT),
        ('% SPO',         instance.PERSENTASE_SPO),
    ]

    return render(request, 'form/lampiran_capex_detail.html', {
        'instance':         instance,
        'logs':             logs,
        'autofill_display': autofill_display,   # ✅ kirim ke template
        'title':            f'Detail Lampiran Capex — {instance.CN_SAP}',
    })
@login_required
def daftar_lampiran_capex(request):
    """Daftar semua Form Lampiran Capex milik user yang login."""
    daftar = FormLampiranCapex.objects.filter(
        diajukan_oleh=request.user
    ).order_by('-created_at')

    return render(request, 'form/daftar_lampiran_capex.html', {
        'daftar': daftar,
        'title': 'Daftar Form Lampiran Capex',
    })

@login_required
def lampiran_capex_create_ajax(request):
    if request.method != 'POST':
        return JsonResponse({'success': False, 'errors': 'Method tidak valid'})

    if not _user_can_create_form(request.user):
        return JsonResponse({'success': False, 'errors': 'Akses ditolak'})

    cn_sap = request.POST.get('CN_SAP', '').strip()

    existing = FormLampiranCapex.objects.filter(CN_SAP=cn_sap).first()
    if existing:
        return JsonResponse({
            'success': False,
            'errors': f'Form untuk CN SAP {cn_sap} sudah ada.'
        })

    try:
        asset = AssetEquipment.objects.get(CN_SAP=cn_sap)
    except AssetEquipment.DoesNotExist:
        return JsonResponse({
            'success': False,
            'errors': f"CN SAP '{cn_sap}' tidak ditemukan."
        })

    # ── Helper: bulatkan decimal ──────────────────────────
    def clean_decimal(value, decimal_places=4):
        """
        Bersihkan nilai decimal:
        - Hapus trailing zeros berlebih
        - Batasi jumlah decimal places
        - Handle None dan string kosong
        """
        if value is None or str(value).strip() == '':
            return '0'
        try:
            from decimal import Decimal, ROUND_HALF_UP, InvalidOperation
            d = Decimal(str(value))
            # Bulatkan sesuai decimal_places
            quantize_str = '0.' + '0' * decimal_places
            d = d.quantize(Decimal(quantize_str), rounding=ROUND_HALF_UP)
            return str(d)
        except (InvalidOperation, ValueError):
            return '0'

    # Gabungkan POST dengan data dari DB
    post_data = request.POST.copy()
    post_data['CN_SAP']         = asset.CN_SAP
    post_data['GROUP']          = asset.GROUP or ''
    post_data['TYPE']           = asset.TYPE  or ''
    post_data['EGI']            = asset.EGI   or ''
    post_data['HM_SMR']         = str(asset.HM_SMR) if asset.HM_SMR else '0'
    post_data['SPO_EQUIPMENT']  = str(asset.SPO_EQUIPMENT) if asset.SPO_EQUIPMENT else ''

    # ✅ Bersihkan PERSENTASE_SPO — max 4 decimal places
    post_data['PERSENTASE_SPO'] = clean_decimal(
        asset.PERSENTASE_SPO, decimal_places=4
    )

    form = LampiranCapexForm(post_data)
    if form.is_valid():
        instance = form.save(commit=False)
        instance.diajukan_oleh = request.user
        instance.status = 'DRAFT'
        instance.save()

        _auto_submit_to_approval(instance, request.user)

        detail_url = reverse('form:lampiran_capex_detail', args=[instance.pk])

        return JsonResponse({
            'success':        True,
            'cn_sap':         instance.CN_SAP,
            'detail_url':     detail_url,
            'status_display': instance.get_status_display(),
        })
    else:
        return JsonResponse({
            'success': False,
            'errors':  form.errors
        })
    

#==============================================================
#======buat fungsi export modal ke PDF ========================
#==============================================================

@login_required  
def lampiran_capex_preview(request):
    """
    Render halaman preview/print dari FormLampiranCapex.
    Menerima data via POST dari modal (sebelum disimpan).
    """
    if request.method != 'POST':
        return HttpResponse("Method tidak valid", status=405)

    # Ambil semua data dari POST
    data = {
        'CN_SAP':                   request.POST.get('CN_SAP', ''),
        'GROUP':                    request.POST.get('GROUP', ''),
        'TYPE':                     request.POST.get('TYPE', ''),
        'EGI':                      request.POST.get('EGI', ''),
        'HM_SMR':                   request.POST.get('HM_SMR', ''),
        'SPO_EQUIPMENT':            request.POST.get('SPO_EQUIPMENT', ''),
        'PERSENTASE_SPO':           request.POST.get('PERSENTASE_SPO', ''),
        'NILAI_AKUISISI':           request.POST.get('NILAI_AKUISISI', ''),
        'NBV':                      request.POST.get('NBV', ''),
        'RV':                       request.POST.get('RV', ''),
        'NBV_STATUS':               request.POST.get('NBV_STATUS', ''),
        'DATE_DELIVERY':            request.POST.get('DATE_DELIVERY', ''),
        'LIFE_EQUIPMENT':           request.POST.get('LIFE_EQUIPMENT', ''),
        'STANDAR_DEPRE_EQUIPMENT':  request.POST.get('STANDAR_DEPRE_EQUIPMENT', ''),
        'REPLACEMENT':              request.POST.get('REPLACEMENT', ''),
        'KONDISI_BODY':             request.POST.get('KONDISI_BODY', ''),
        'KONDISI_FRAME':            request.POST.get('KONDISI_FRAME', ''),
        'KONDISI_KOMPONEN':         request.POST.get('KONDISI_KOMPONEN', ''),
        'PROSENTASE_LIFE_COMP_SPO': request.POST.get('PROSENTASE_LIFE_COMP_SPO', ''),
        'COST_REPAIR':              request.POST.get('COST_REPAIR', ''),
        'HARGA_NEW':                request.POST.get('HARGA_NEW', ''),
        'NILAI_SISA_COMP':          request.POST.get('NILAI_SISA_COMP', ''),
        'OBSOLETE':                 request.POST.get('OBSOLETE', ''),
        'doc_number_auto':          request.POST.get('doc_number_auto', ''),
        'doc_number_manual':        request.POST.get('doc_number_manual', ''),
        # Tanda tangan
        'dibuat_nama':              request.POST.get('dibuat_nama', ''),
        'dibuat_jabatan':           request.POST.get('dibuat_jabatan', ''),
        'diperiksa_nama':           request.POST.get('diperiksa_nama', ''),
        'diperiksa_jabatan':        request.POST.get('diperiksa_jabatan', ''),
        'disetujui_nama':           request.POST.get('disetujui_nama', ''),
        'disetujui_jabatan':        request.POST.get('disetujui_jabatan', ''),
    }

    # Cek apakah request untuk PDF download atau preview
    output_type = request.POST.get('output_type', 'preview')

    if output_type == 'pdf':
        # Generate PDF menggunakan xhtml2pdf
        try:
            from xhtml2pdf import pisa

            template = get_template('lampiran_capex_pdf.html')
            html_content = template.render({
                'data': data,
                'request': request,
            })

            response = HttpResponse(content_type='application/pdf')
            response['Content-Disposition'] = (
                f'attachment; filename="LampiranCapex_{data["CN_SAP"]}.pdf"'
            )

            pdf_file = io.BytesIO()
            pisa_status = pisa.CreatePDF(
                html_content,
                dest=pdf_file,
                encoding='utf-8',
            )

            if pisa_status.err:
                return HttpResponse(
                    "Gagal generate PDF", status=500
                )

            response.write(pdf_file.getvalue())
            return response

        except ImportError:
            return HttpResponse(
                "xhtml2pdf belum terinstall. "
                "Jalankan: pip install xhtml2pdf",
                status=500
            )

    # Default: return HTML preview untuk print
    template = get_template('lampiran_capex_pdf.html')
    html_content = template.render({
        'data': data,
        'request': request,
        'is_preview': True,
    })
    return HttpResponse(html_content)

#--buat AJAX untuk form standby---
@login_required
def ba_standby_create_ajax(request):
    """ endpoint AJAX untuk submit form BA Standby dari modal"""
    if request.method != 'POST':
        return JsonResponse({'success': False, 'error': 'Method tidak valid'})
    if not _user_can_create_form(request.user):
        return JsonResponse({'success': False, 'error':'Akses ditolak'})
    cn_sap = request.POST.get('CN_SAP', '').strip()

    #cek duplikat
    existing = FormBAStandby.objects.filter(
        CN_SAP =cn_sap,
        status__in=['DRAFT','SUB', 'APR1', 'APR2']
    ).first()
    if existing:
        return JsonResponse({
            'success': False,
            'error': f'BA Standby untuk CN SAP {cn_sap} sudah ada dalam proses.'
        })
  # Ambil data asset dari AssetEquipment
    try:
        asset = AssetEquipment.objects.get(CN_SAP=cn_sap)
    except AssetEquipment.DoesNotExist:
        return JsonResponse({
            'success': False,
            'error': f"CN_SAP '{cn_sap}' tidak di temukan."
        })  
    try:
        instance = FormBAStandby(
            CN_SAP = asset.CN_SAP,
            EGI = asset.EGI or '',
            EQUIP_NAME = asset.TYPE or '',
            SERIAL_NUMBER = asset.SN or '',
            HM = str(asset.HM_SMR)   if asset.HM_SMR else '',
            LOCATION = asset.LOCATION or '',
            STATUS_STANDBY = 'STANDBY',

            NO_DOKUMEN_AUTO     = request.POST.get('NO_DOKUMEN_AUTO', ''),
            NO_DOKUMEN_MANUAL   = request.POST.get('NO_DOKUMEN_MANUAL', ''),
            TANGGAL_EFEKTIF     = request.POST.get('TANGGAL_EFEKTIF', '') or None,  
            ALASAN_STANDBY      = request.POST.get('ALASAN_STANDBY', ''),                        
                                                                            
            DIAJUKAN_NAMA       = request.POST.get('DIAJUKAN_NAMA', ''),                                                                
            DIAJUKAN_JABATAN    = request.POST.get('DIAJUKAN_JABATAN', ''),                                                                
                                                                            
            MENGETAHUI1_NAMA    = request.POST.get('MENGETAHUI1_NAMA', ''),
            MENGETAHUI1_JABATAN = request.POST.get('MENGETAHUI1_JABATAN', ''),

            # Mengetahui 2
            MENGETAHUI2_NAMA    = request.POST.get('MENGETAHUI2_NAMA', ''),
            MENGETAHUI2_JABATAN = request.POST.get('MENGETAHUI2_JABATAN', ''),

            # Menyetujui 1
            MENYETUJUI1_NAMA    = request.POST.get('MENYETUJUI1_NAMA', ''),
            MENYETUJUI1_JABATAN = request.POST.get('MENYETUJUI1_JABATAN ', ''),

            # Menyetujui 2
            MENYETUJUI2_NAMA    = request.POST.get('MENYETUJUI2_NAMA', ''),
            MENYETUJUI2_JABATAN = request.POST.get('MENYETUJUI2_JABATAN', ''),

            # Menyetujui 3
            MENYETUJUI3_NAMA    = request.POST.get('MENYETUJUI3_NAMA', ''),
            MENYETUJUI3_JABATAN = request.POST.get('MENYETUJUI3_JABATAN', ''), 

            diajukan_oleh = request.user,
            status = 'DRAFT',                                                             
        )
        instance.save()

        #auto submit ke approval
        _auto_submit_to_approval(instance, request.user)

        detail_url = reverse('form:ba_standby_detail', args=[instance.pk])

        return JsonResponse({
            'success' : True,
            'cn_sap': instance.CN_SAP,
            'detail_url':detail_url,
            'status_display': instance.get_status_display(),            
        })
    except Exception as e:
        return JsonResponse({
            'success': False,
            'error': str(e)
        })

 

#=== detail BA Standby======
@login_required
def ba_standby_detail(request, pk):
    instance = get_object_or_404(FormBAStandby, pk=pk)
    content_type = ContentType.objects.get_for_model(instance)
    logs  =ApprovalLog.objects.filter(
        content_type = content_type,
        object_id = instance.pk,        
    ).order_by('tanggal_persetujuan')

    return render(request, 'form/ba_standby_detail,html',{
        'instance' : instance,
        'logs' : logs,
        'title' : f'Detail BA Standby - {instance.CN_SAP}',
    })
#=== preview/print/ PDF BA Standby ======
@login_required
def ba_standby_preview(request):
    if request.method != 'POST':
        return HttpResponse("methode tidak valid", status = 405)
    
    data = {
        'CN_SAP':           request.POST.get('CN_SAP', ''),
        'EGI':              request.POST.get('EGI', ''),
        'EQUIP_NAME':       request.POST.get('EQUIP_NAME', ''),
        'SERIAL_NUMBER':    request.POST.get('SERIAL_NUMBER', ''),
        'HM':               request.POST.get('HM', ''),
        'LOCATION':         request.POST.get('LOCATION', ''),
        'STATUS_STANDBY':   request.POST.get('STATUS_STANDBY', 'STANDBY'),
        'NO_DOKUMEN_AUTO':  request.POST.get('NO_DOKUMEN_AUTO', ''),
        'NO_DOKUMEN_MANUAL':request.POST.get('NO_DOKUMEN_MANUAL', ''),
        'TANGGAL_EFEKTIF':  request.POST.get('TANGGAL_EFEKTIF', ''),
        'ALASAN_STANDBY':   request.POST.get('ALASAN_STANDBY', ''),
        # Tanda tangan
        'DIAJUKAN_NAMA':      request.POST.get('DIAJUKAN_NAMA', ''),
        'DIAJUKAN_JABATAN':   request.POST.get('DIAJUKAN_JABATAN', ''),
        'MENGETAHUI1_NAMA':   request.POST.get('MENGETAHUI1_NAMA', ''),
        'MENGETAHUI1_JABATAN':request.POST.get('MENGETAHUI1_JABATAN', ''),
        'MENGETAHUI2_NAMA':   request.POST.get('MENGETAHUI2_NAMA', ''),
        'MENGETAHUI2_JABATAN':request.POST.get('MENGETAHUI2_JABATAN', ''),
        'MENYETUJUI1_NAMA':   request.POST.get('MENYETUJUI1_NAMA', ''),
        'MENYETUJUI1_JABATAN':request.POST.get('MENYETUJUI1_JABATAN', ''),
        'MENYETUJUI2_NAMA':   request.POST.get('MENYETUJUI2_NAMA', ''),
        'MENYETUJUI2_JABATAN':request.POST.get('MENYETUJUI2_JABATAN', ''),
        'MENYETUJUI3_NAMA':   request.POST.get('MENYETUJUI3_NAMA', ''),
        'MENYETUJUI3_JABATAN':request.POST.get('MENYETUJUI3_JABATAN', ''),
        'doc_number_auto':    request.POST.get('NO_DOKUMEN_AUTO', ''),
        'doc_number_manual':  request.POST.get('NO_DOKUMEN_MANUAL', ''),
    }
    
    output_type = request.POST.get('output_type', 'preview')
    template    = get_template('ba_standby_pdf.html')
    html_content = template.render({
        'data':       data,
        'request':    request,
        'is_preview': True,
        'auto_print': output_type == 'pdf',
    })
    return HttpResponse(html_content)