# asset/views.py
import pandas as pd
from django.shortcuts import render, redirect, get_list_or_404
from django.http import HttpResponse
from django.core.files.storage import FileSystemStorage
from django.contrib.auth import authenticate, login
from django.contrib.auth import logout
from django.contrib.auth.forms import UserCreationForm
from django.shortcuts import get_object_or_404
from django.urls import reverse
from django.utils import timezone
from django.views.decorators.http import require_POST
from django.http import JsonResponse
from django.contrib.admin.views.decorators import staff_member_required
from django.views.decorators.http import require_GET
from django.core.paginator import Paginator
from .models import AssetEquipment
from .forms import AssetEquipmentForm
from django.db.models import Count
from django.views.decorators.csrf import csrf_exempt
import io
import os
import tempfile
from .resources import AssetEquipmentResource
from django.contrib.auth.decorators import login_required
from django.db.models import Q
from .models import AssetEquipment
from .models import AssetEquipmentDisposed, AssetEquipmentStandby, AssetEquipmentBreakdown
from .models import AssetEquipmentPrepareDisposed

from django.views.generic import ListView, CreateView
from django.contrib.auth.mixins import LoginRequiredMixin
from django.urls import reverse_lazy
from django.forms import ModelForm
from asset.admin import admin_site
import logging
from django.views import View

from django.contrib import messages
from .utils_ocr import verifikasi_dokumen_rca, extract_text_from_file
from .utils_ocr import generate_foto_4_sisi_pdf

# Buat instance logger
logger = logging.getLogger(__name__)    

#form untuk global monitoring
from form.models import ChecksheetPI

from accounts.views import (
    calculate_bottleneck_info,
    calculate_total_processing_time,
    get_current_approval_step_name,
    get_next_approval_step_name,
)    

from django.utils import timezone  # Pastikan timezone ter-import jika belum ada di atas

# CREATE: Menambahkan asset equipment baru
def asset_equipment_create(request):
    if request.method =='POST':
        form = AssetEquipmentForm(request.POST, request.FILES)
        if form.is_valid():
            form.save()
            return redirect('asset_equipment_list')
    else:
        form = AssetEquipmentForm()
    return redirect(request,'asset/asset_form.html',{'form':form})    

# UPDATE : Mengedit asset equipment 
def asset_equipment_update(request,pk):
    asset_equipment = get_object_or_404(AssetEquipment,pk=pk)
    if request.method =='POST':
        form = AssetEquipmentForm(request.POST, instance=asset_equipment) 
        if form.is_valid():
            form.save()
            return redirect('asset_equipment_list') 
    else:
        form = AssetEquipmentForm(instance=asset_equipment)
    return render(request,'asset/asset_form.html',{'form':form})

# DELETE : Menghapus asset equipment
def asset_equipment_delete(request,pk):
    asset_equipment = get_object_or_404(AssetEquipment,pk=pk)
    if request.method == 'POST':
        asset_equipment.delete()
        return redirect('asset_equipment_list')
    return render(request,'asset/confirm_delete.html',{'asset_equipment':asset_equipment}) 

# IMPORT : Mengimport data dari file Excel  
def import_asset_equipment_excel(request):
    if request.method == 'POST' and request.FILES.get("file"):
        file = request.FILES["file"]
        file_extention = file.name.split(".")[-1]

        #simpan file sementara
        fs = FileSystemStorage()
        filename = fs.save(file.name, file)
        file_path = fs.path(filename)

        try:
            if file_extention in ["xls","xlsx"]:
                df = pd.read_excel(file_path, engine='openpyxl')
            else:
                return render(request, "asset/import.html",{"error":"format file tidak didukung !"})
            #Pastikan kolom yang dibutuhkan ada
            required_columns = {
                 "No_Asset",
                 "CN_SAP",
                 "CN_ELLIPSE",
                 "EGI",
                 "TYPE",
                 "GROUP",
                 "OWNERSHIP",
                 "LOCATION",                 
                 "SUB_SITE",
                 "BRAND",
                 "SN",
                 "HM_SMR",
                 "HM_DATE",
                 "SPO_EQUIPMENT",
                 "PERSENTASE_SPO",
                 "EQUIPMENT_CONDITION",
                 "STATUS_EQUIPMENT",
                 "STATUS_EQUIPMENT_DISPOSED",
                 "REFERENSI_NO_PDE"
                 "BP"
                 }
            if not required_columns.issubset(df.columns):
                return render(request,'asset/import.html',{"error":"kolom dalam file tidak sesuai !"})
            
            # Sesuaikan urutan kolom dengan model menggunakan reindex()

            # Rename kolom sesuai nama field model
            column_mapping = {
                "No_Asset": "No_Asset",
                "Code Number": "CN_SAP",
                "cn_ellipse": "CN_ELLIPSE",
                "EGI": "EGI",
                "Type": "TYPE",
                "Class": "GROUP",
                "Ownership": "OWNERSHIP",
                "Location": "LOCATION",
                "Sub Site": "SUB_SITE",
                "Brand": "BRAND",
                "SN": "SN",
                "Hour Meter": "HM_SMR",
                "Hour Meter Date": "HM_DATE",
                "SPO Equipment": "SPO_EQUIPMENT",
                "% SPO Equipment": "PERSENTASE_SPO",
                "Equipment Condition": "EQUIPMENT_CONDITION",
                "Status Equipment 1": "STATUS_EQUIPMENT",
                "Status Equipment Disposed": "STATUS_EQUIPMENT_DISPOSED",
                "referensi_no_pde": "REFERENSI_NO_PDE",
                "BP": "BP"
            }

            # Rename kolom berdasarkan mapping
            df.rename(columns=column_mapping, inplace=True)

            # Hanya gunakan kolom yang dibutuhkan
            model_fields = list(column_mapping.values())
            df = df[model_fields]


            #bersihkan data dari whitespice
            df = df.applymap(lambda x: x.strip() if isinstance(x,str) else x)

            # 🌟 AMBIL DATA BULAN DAN TAHUN BERJALAN SAAT INI UNTUK MODEL BULANAN
            current_date = timezone.now().date()
            current_year = current_date.year
            

            #Looping untuk memasukkan data kedalam Database
            errors = []        
            # 🌟 JANGAN PAKAI BULK_CREATE. Gunakan update_or_create agar def save() di models.py terpanggil!
            for _, row in df.iterrows():
                # Ubah format tanggal jika berupa string
                hm_date_val = row["HM_DATE"]
                if pd.isna(hm_date_val): hm_date_val = None

                # Gunakan get_or_create atau update_or_create untuk AssetMonthlyStatus
                from .models import AssetMonthlyStatus
                asset_instance, created = AssetMonthlyStatus.objects.get_or_create(
                    CN_SAP=row["CN_SAP"],
                    MONTH=current_date.replace(day=1), # Mengunci awal bulan berjalan
                    YEAR=current_year,
                )

                # Set value sisanya
                asset_instance.No_Asset = row["No_Asset"]
                asset_instance.CN_ELLIPSE = row["CN_ELLIPSE"]
                asset_instance.EGI = row["EGI"]
                asset_instance.TYPE = row["TYPE"]
                asset_instance.GROUP = row["GROUP"]
                asset_instance.OWNERSHIP = row["OWNERSHIP"]
                asset_instance.LOCATION = row["LOCATION"]
                asset_instance.SUB_SITE = row["SUB_SITE"]
                asset_instance.BRAND = row["BRAND"]
                asset_instance.SN = row["SN"]
                asset_instance.HM_SMR = row["HM_SMR"]
                asset_instance.HM_DATE = hm_date_val
                asset_instance.SPO_EQUIPMENT = row["SPO_EQUIPMENT"] if not pd.isna(row["SPO_EQUIPMENT"]) else None
                asset_instance.PERSENTASE_SPO = row["PERSENTASE_SPO"] if not pd.isna(row["PERSENTASE_SPO"]) else None
                
                # Masukkan data Equipment Condition mentah dari Excel
                asset_instance.EQUIPMENT_CONDITION = row["EQUIPMENT_CONDITION"]
                asset_instance.STATUS_EQUIPMENT = row["STATUS_EQUIPMENT"]
                asset_instance.REFERENSI_NO_PDE = row["REFERENSI_NO_PDE"]
                asset_instance.BP = row['BP']

                # 🌟 KUNCI UTAMA: Panggil .save() satu per satu!
                # Ini memicu intercept otomatis yang memaksa 'DISPOSED' menjadi 'PREPARE FOR DISPOSED' di tabel UI jika berkas kosong.
                asset_instance.save()

            return render(request, "asset/import.html", {"message": "Import berhasil & status ter-otomatisasi oleh sistem OCR", "error": errors})
        except Exception as e:
            return render(request, "asset/import.html", {"error": f"terjadi kesalahan: {str(e)}"})
    return render(request, "asset/import.html")

# EKSPORT : mengeksport data ke file excel
@csrf_exempt  # jika kamu mengalami masalah CSRF saat submit dari JS
def export_asset_equipment_excel(request):
    if request.method == 'POST':
        ids = request.POST.getlist('selected_ids[]')  # JS form biasanya kirim sebagai array
        if not ids:
            return HttpResponse("No items selected.", status=400)

        queryset = AssetEquipment.objects.filter(id__in=ids).values(
            "No_Asset",
            "CN_SAP",
            "CN_ELLIPSE",
            "EGI",
            "FOTO",
            "TYPE",
            "GROUP",
            "OWNERSHIP",
            "LOCATION",                 
            "SUB_SITE",
            "BRAND",
            "SN",
            "HM_SMR",
            "HM_DATE",
            "SPO_EQUIPMENT",
            "PERSENTASE_SPO",
            "EQUIPMENT_CONDITION",
            "STATUS_EQUIPMENT",
            "STATUS_EQUIPMENT_DISPOSED",
            "REFERENSI_NO_PDE",
            "BP"
        )
        #Buat data frame di pandas 
        df = pd.DataFrame(list(queryset))

        #Simpan data ke Excel
        response = HttpResponse(content_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet")
        response["Content-Disposition"] = 'attachment; filename="selected_asset_equipments.xlsx"'

        with pd.ExcelWriter(response, engine="openpyxl") as writer:
            df.to_excel(writer, index=False, sheet_name="SelectedAssets")

        return response

    return HttpResponse("Invalid request method", status=405)

#Fungsi pagination 
def asset_equipment_list(request):
    per_page = request.GET.get('per_page', 10)  # default 10 jika tidak dipilih
    asset_equipments = AssetEquipment.objects.all().order_by('id')
    
    paginator = Paginator(asset_equipments, per_page)
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)

    return render(request, 'asset/asset_list.html', {
        'page_obj': page_obj,
        'per_page': int(per_page),
    })

def export_asset_equipment_excel(request):
    dataset = AssetEquipmentResource().export()
    response = HttpResponse(
        dataset.xlsx,
        content_type='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',
    )
    response['Content-Disposition'] = 'attachment; filename="asset_equipment.xlsx"'
    return response
@login_required
def assetequipment_list_view(request):
    equipments = AssetEquipment.objects.all()
    return render(request, 'asset/assetequipment_list.html', {'equipments': equipments})

   

#Login: Halaman login awal
def custom_login(request):
    if request.method == 'POST':
        username = request.POST['username']
        password = request.POST['password']
        user = authenticate(request, username=username, password=password)
        if user is not None:
            login(request, user)
            return redirect(reverse('admin:index'))  # ganti dengan URL setelah login
        else:
            return render(request, 'asset/auth/login.html', {'error': 'Username atau password salah'})
    return render(request, 'asset/auth/login.html')
#Register: Halaman register user
def register(request):
    if request.method == 'POST':
        form = UserCreationForm(request.POST)
        if form.is_valid():
            form.save()
            return redirect('login')
    else:
        form = UserCreationForm()
    return render(request, 'asset/auth/register.html', {'form': form})

#logout halaman admin
def custom_logout(request):
    logout(request)
    return redirect('login')

@login_required
def login_redirect_view(request):
    if request.user.is_superuser:
        return redirect('admin_dashboard')  # Atur sesuai url name dashboard admin
    elif hasattr(request.user, 'userprofile'):
        role = request.user.userprofile.role
        if role == 'admin':
            return redirect('admin_dashboard')
        elif role == 'user':
            return redirect('user_dashboard')
    return redirect('login')  # fallback kalau gak ada role

def custom_admin_index(request): 
    user = request.user
    my_admin_site = admin_site 
    
    context = my_admin_site.each_context(request)
    context['app_list'] = my_admin_site.get_app_list(request)
    
    
    # 🎯 PERBAIKAN 1: Pastikan data Asset Summary dimasukkan (untuk kartu di atas)
    # KARENA template admin/index.html membutuhkannya
    from django.db.models import Count
    from .models import AssetEquipment
    
    all_assets = AssetEquipment.objects.all()
    status_counts = all_assets.values('EQUIPMENT_CONDITION').annotate(count=Count('EQUIPMENT_CONDITION'))
    
    context['total_assets'] = all_assets.count()
    context['operate'] = next((item['count'] for item in status_counts if item['EQUIPMENT_CONDITION'] == 'OPERATE'), 0)
    context['breakdown'] = next((item['count'] for item in status_counts if item['EQUIPMENT_CONDITION'] == 'BREAKDOWN'), 0)
    context['standby'] = next((item['count'] for item in status_counts if item['EQUIPMENT_CONDITION'] == 'STANDBY'), 0)
    context['preparefordisposed'] = next((item['count'] for item in status_counts if item['EQUIPMENT_CONDITION'] == 'PREPARE FOR DISPOSED'), 0)
    context['disposed'] = next((item['count'] for item in status_counts if item['EQUIPMENT_CONDITION'] == 'DISPOSED'), 0)
    context['rfu'] = next((item['count'] for item in status_counts if item['BP'] == 'RFU'), 0)
    
    # Kunci: Gunakan logika exclude yang sama persis
    all_live_docs = ChecksheetPI.objects.exclude(status__in=['DRAFT']).order_by('-submitted_at')

    monitoring_data = []
    
    for doc in all_live_docs:
     # Hitung metrik yang dibutuhkan
        bottleneck_data = calculate_bottleneck_info(doc)
        elapsed_time = calculate_total_processing_time(doc)
        current_step = get_current_approval_step_name(doc.status)
    # ... (Logika processing metrik: bottleneck, elapsed time, current_step) ...
        
        # JIKA dokumen sudah FIN/REJ, pastikan current_step dan next_step diatur dengan benar
        current_step = get_current_approval_step_name(doc.status)
        next_step = '-'
        
        # 🎯 PERBAIKAN 3: Sinkronkan logic FIN/REJ dengan accounts/views.py dan gambar Anda
        if doc.status not in ['FIN', 'REJ']:
            next_step = get_next_approval_step_name(doc.status)
        
        # Perbarui current_step untuk status akhir
        # Gunakan 'Selesai (Finalized)' dan 'Ditolak (Rejected)' sesuai dengan fungsi get_current_approval_step_name di accounts/views.py
        if doc.status == 'FIN':
            current_step = 'Selesai (Finalized)' 
        elif doc.status == 'REJ':
            current_step = 'Ditolak (Rejected)'

        doc_data = {
            'pk': doc.pk,
            'cn_sap': doc.cn_sap,
            'status': doc.status,
            'current_approval_step': current_step,
            'next_approval_step': next_step,
            'submitted_at': doc.submitted_at.strftime("%Y-%m-%d %H:%M"),
            
            # Metrik Monitoring
            'current_approval_step': current_step, # Ini duplikasi, tapi biarkan saja untuk aman
            'longest_duration': bottleneck_data['longest_duration'],
            'bottleneck_step': bottleneck_data['bottleneck_step'],
            'elapsed_time': elapsed_time,
        }
        monitoring_data.append(doc_data)

    context['monitoring_data'] = monitoring_data

    # 🎯 Ganti PRINT dengan LOGGER
    logger.info("--- DEBUG MONITORING DATA ---")
    logger.info("Jumlah Dokumen yang SEDANG DIPROSES: %s", len(monitoring_data))
    if monitoring_data:
        # Gunakan %s untuk pemformatan string logging
        logger.info("Contoh Dokumen: %s Status: %s", monitoring_data[0]['cn_sap'], monitoring_data[0]['status'])
    logger.info("-----------------------------")
    
    # 🌟 BONUS: Tampilkan juga dokumen yang perlu aksi admin (jika ada)
    # Ini adalah data "Dokumen Pending Anda" untuk Superuser
    context['pending_docs'] = ChecksheetPI.objects.filter(
         status__in=['SUB', 'APR1', 'APR2'] # Ambil semua status yang sedang butuh persetujuan
    ).order_by('-submitted_at') 
    
    # PENTING: Tambahkan pemrosesan bottleneck untuk pending_docs Superuser agar HTML-nya tidak error
    for doc in context['pending_docs']:
        bottleneck_data = calculate_bottleneck_info(doc)
        doc.bottleneck_step = bottleneck_data['bottleneck_step']
        doc.longest_duration = bottleneck_data['longest_duration']
        doc.current_approval_step = get_current_approval_step_name(doc.status)
        doc.elapsed_time = calculate_total_processing_time(doc)
    
    # ...
    return render(request, 'admin/index.html', context)


#====================================================#
#===== Tambahan untuk filter location di dashboard===#
#====================================================#

from django.http import JsonResponse
from django.contrib.admin.views.decorators import staff_member_required
from django.views.decorators.http import require_GET
from data.models import conmon, directcost
from django.db.models import Sum, DecimalField, Count, Q, Case, When, IntegerField
from django.db.models.functions import Cast, ExtractMonth, ExtractYear
from django.utils import timezone

@staff_member_required
@require_GET
def dashboard_filter_data(request):
    from .models import AssetMonthlyStatus, AssetEquipment
    from form.models import (
        FormLampiranCapex, FormPengajuanEquipmentDisposed,
        FormPengajuanDisposedSite, FormRepairCostAnalisis, FormFotoKonditionUnit
    )

    # ============================================================
    # 🌟 1. DETEKSI ROLE USER — BAGIAN INI YANG DITAMBAHKAN
    # ============================================================
    user_lokasi   = ""
    user_section  = ""
    is_restricted = False

    if not request.user.is_superuser and hasattr(request.user, 'userprofile'):
        user_lokasi  = request.user.userprofile.lokasi or ""
        user_section = request.user.userprofile.section or ""
        if user_lokasi:
            is_restricted = True

    # ============================================================
    # 🌟 2. HELPER TERPUSAT — TERAPKAN ROLE FILTER KE QUERYSET APA PUN
    # ============================================================
    def apply_role_filter(qs, loc_field='LOCATION', sec_field='SECTION'):
        """Paksa filter lokasi & section sesuai role user login."""
        if is_restricted:
            qs = qs.filter(**{f'{loc_field}__iexact': user_lokasi})
            if user_section:
                qs = qs.filter(**{f'{sec_field}__iexact': user_section})
        return qs

    # ============================================================
    # 🌟 3. AMBIL PARAMETER UI DARI REQUEST
    # ============================================================
    location     = request.GET.get('location', '').strip()
    sub_location = request.GET.get('sub_location', '').strip()
    eq_class     = request.GET.get('eq_class', '').strip()
    egi          = request.GET.get('egi', '').strip()
    cn_sap       = request.GET.get('cn_sap', '').strip()

    # ============================================================
    # 🌟 4. KUNCI LOCATION: USER RESTRICTED TIDAK BISA OVERRIDE
    # Jika user restricted, parameter 'location' dari URL diabaikan,
    # diganti paksa dengan lokasi dari userprofile.
    # ============================================================
    if is_restricted:
        location = user_lokasi  # ✅ KUNCI — tidak bisa di-bypass via URL param

    # ============================================================
    # 🌟 5. REVERSE CASCADING: Jika user input CN_SAP, auto-detect location
    #    Tapi tetap dikunci ke lokasi role jika restricted.
    # ============================================================
    detected_location     = location
    detected_sub_location = sub_location

    if cn_sap and not sub_location:
        asset_info = AssetEquipment.objects.filter(CN_SAP__iexact=cn_sap).first()
        if asset_info:
            # ✅ FIX: Hanya pakai detected_location dari asset jika user BUKAN restricted
            # Jika restricted, tetap kunci ke user_lokasi
            if not is_restricted:
                detected_location = asset_info.LOCATION
                location = detected_location
            detected_sub_location = asset_info.SUB_LOCATION
            sub_location = detected_sub_location

    # ============================================================
    # 🌟 6. BASE QUERYSET — ROLE FILTER DULU, BARU FILTER UI
    # ============================================================
    # ✅ URUTAN PENTING: apply_role_filter() HARUS dipanggil SEBELUM filter UI
    qs = apply_role_filter(AssetEquipment.objects.all())

    # Terapkan filter tambahan dari UI (setelah role filter terkunci)
    if location:
        qs = qs.filter(LOCATION=location)
    if sub_location:
        qs = qs.filter(SUB_LOCATION=sub_location)
    if eq_class:
        qs = qs.filter(GROUP=eq_class)
    if egi:
        qs = qs.filter(EGI=egi)
    if cn_sap:
        qs = qs.filter(CN_SAP__icontains=cn_sap)

    # CN_SAP aktif setelah semua filter (dipakai oleh conmon & directcost)
    current_cn_saps = list(qs.values_list('CN_SAP', flat=True))

    # ============================================================
    # 🌟 7. HITUNG COUNTS
    # ============================================================
    counts = qs.aggregate(
        total     = Count('CN_SAP'),
        operate   = Count('CN_SAP', filter=Q(EQUIPMENT_CONDITION='OPERATE')),
        breakdown = Count('CN_SAP', filter=Q(EQUIPMENT_CONDITION='BREAKDOWN')),
        standby   = Count('CN_SAP', filter=Q(EQUIPMENT_CONDITION='STANDBY')),
        preparefordisposed   = Count('CN_SAP', filter=Q(EQUIPMENT_CONDITION='PREPARE FOR DISPOSED')),
        disposed  = Count('CN_SAP', filter=Q(EQUIPMENT_CONDITION='DISPOSED')),
        rfu       = Count('CN_SAP', filter=Q(BP='RFU')),
    )

    # ============================================================
    # 🌟 8. DISPOSED BREAKDOWN
    # ============================================================
    disposed_qs         = qs.filter(EQUIPMENT_CONDITION='DISPOSED')
    disposed_by_location = list(disposed_qs.values('LOCATION').annotate(count=Count('CN_SAP')).order_by('-count'))
    disposed_by_sub      = list(disposed_qs.values('SUB_LOCATION').annotate(count=Count('CN_SAP')).order_by('-count'))
    disposed_by_egi      = list(disposed_qs.values('EGI', 'TYPE').annotate(count=Count('CN_SAP')).order_by('-count'))
    disposed_by_cn       = list(disposed_qs.values('CN_SAP', 'TYPE').annotate(count=Count('CN_SAP')).order_by('-count'))

    # ============================================================
    # 🌟 8.5. PREPARE FOR DISPOSED PROGRESS STATS & DETAIL DOKUMEN
    # ============================================================
    prepare_qs = apply_role_filter(
        AssetEquipmentPrepareDisposed.objects.select_related('asset').filter(
            EQUIPMENT_CONDITION__iexact='PREPARE FOR DISPOSED'
        ),
        loc_field='LOCATION', 
        sec_field='SECTION'
    )

    if location:       prepare_qs = prepare_qs.filter(LOCATION=location)
    if sub_location:   prepare_qs = prepare_qs.filter(SUB_LOCATION=sub_location)
    if eq_class:       prepare_qs = prepare_qs.filter(GROUP=eq_class)
    if egi:            prepare_qs = prepare_qs.filter(EGI=egi)
    if cn_sap:         prepare_qs = prepare_qs.filter(asset__CN_SAP__icontains=cn_sap)

    total_prepare_unit = prepare_qs.count()
    
    prepare_complete_count = sum(1 for obj in prepare_qs if obj.is_phase_1_complete)
    prepare_progress_count = total_prepare_unit - prepare_complete_count
    
    if total_prepare_unit > 0:
        total_persentase = sum(obj.persentase_complete for obj in prepare_qs)
        prepare_avg_progress = round(total_persentase / total_prepare_unit, 1)
    else:
        prepare_avg_progress = 0.0

    # ✅ Hitung rekapitulasi per jenis dokumen untuk kartu detail di HTML
    doc_fields_map = ['foto_4_sisi', 'inspeksi_unit', 'rca', 'pengajuan_disposed']
    doc_counts = {}
    for df in doc_fields_map:
        complete_cnt = sum(1 for obj in prepare_qs if getattr(obj, df))
        pct = round((complete_cnt / total_prepare_unit * 100)) if total_prepare_unit > 0 else 0
        doc_counts[df] = {
            'count': complete_cnt,
            'percentage': pct
        }


    # ============================================================
    # 🌟 8.6. SERIALIZE DATA UNIT PREPARE UNTUK TABEL AJAX
    # ============================================================
    prepare_units_list = []
    for obj in prepare_qs:
        # Ambil CN_SAP aman melalui relasi OneToOne 'asset'
        cn_val = obj.asset.CN_SAP if obj.asset else (getattr(obj, 'CN_SAP', None) or '-')
        
        prepare_units_list.append({
            'cn_sap': cn_val,
            'egi': obj.EGI or '-',
            'location': obj.LOCATION or '-',
            'section': obj.SECTION or '-',
            'foto_4_sisi_url': obj.foto_4_sisi.url if hasattr(obj, 'foto_4_sisi') and obj.foto_4_sisi else None,
            'foto_4_sisi_uploaded_at': obj.foto_4_sisi_uploaded_at.strftime('%d/%m/%Y %H:%M') if hasattr(obj, 'foto_4_sisi_uploaded_at') and obj.foto_4_sisi_uploaded_at else None,
            'inspeksi_unit_url': obj.inspeksi_unit.url if hasattr(obj, 'inspeksi_unit') and obj.inspeksi_unit else None,
            'inspeksi_unit_uploaded_at': obj.inspeksi_unit_uploaded_at.strftime('%d/%m/%Y %H:%M') if hasattr(obj, 'inspeksi_unit_uploaded_at') and obj.inspeksi_unit_uploaded_at else None,
            'rca_url': obj.rca.url if hasattr(obj, 'rca') and obj.rca else None,
            'rca_uploaded_at': obj.rca_uploaded_at.strftime('%d/%m/%Y %H:%M') if hasattr(obj, 'rca_uploaded_at') and obj.rca_uploaded_at else None,
            'pengajuan_disposed_url': obj.pengajuan_disposed.url if hasattr(obj, 'pengajuan_disposed') and obj.pengajuan_disposed else None,
            'pengajuan_disposed_uploaded_at': obj.pengajuan_disposed_uploaded_at.strftime('%d/%m/%Y %H:%M') if hasattr(obj, 'pengajuan_disposed_uploaded_at') and obj.pengajuan_disposed_uploaded_at else None,
            'jumlah_complete': getattr(obj, 'jumlah_complete', 0),
            'persentase_complete': getattr(obj, 'persentase_complete', 0),
        })


    # ============================================================
    # 🌟 9. FOTO UNIT DARI CLOUDINARY
    # ============================================================
    unit_photo_url = "/static/image/asset/default_unit.jpg"

    if cn_sap:
        clean_cn = cn_sap.strip()
        # ✅ FIX: Pastikan foto yang diambil hanya dari CN_SAP milik user (via current_cn_saps)
        latest_status = (
            AssetMonthlyStatus.objects
            .filter(CN_SAP__in=current_cn_saps)  # ← terkunci ke data yang berhak dilihat
            .filter(Q(CN_SAP__iexact=clean_cn) | Q(CN_SAP__icontains=clean_cn))
            .filter(FOTO__isnull=False)
            .exclude(FOTO="")
            .order_by('-id')
            .first()
        )
        if latest_status and latest_status.FOTO:
            try:
                unit_photo_url = latest_status.FOTO.url
            except Exception:
                unit_photo_url = "/static/image/asset/default_unit.jpg"
                

    # ============================================================
    # 🌟 10. CONMON DATA
    # ============================================================
    conmon_list = []
    conmon_qs   = conmon.objects.none()

    if cn_sap:
        # ✅ FIX: Pastikan CN_SAP yang dicari ada dalam current_cn_saps (sudah terfilter role)
        if cn_sap.upper() in [c.upper() for c in current_cn_saps]:
            conmon_qs = conmon.objects.filter(CN_SAP__iexact=cn_sap)
            if not conmon_qs.exists():
                conmon_qs = conmon.objects.filter(CN_SAP__icontains=cn_sap)
        # Jika CN_SAP tidak ada dalam current_cn_saps, conmon_qs tetap kosong (aman)
    elif current_cn_saps:
        conmon_qs = conmon.objects.filter(CN_SAP__in=current_cn_saps)

    for item in conmon_qs:
        health_pct = "-"
        if item.COMP_HEALTH is not None:
            try:
                val = float(item.COMP_HEALTH)
                health_pct = f"{int(val)}%" if val == int(val) else f"{val:.1f}%"
            except (ValueError, TypeError):
                health_pct = f"{item.COMP_HEALTH}%"

        conmon_list.append({
            'cn_sap':    item.CN_SAP or '-',
            'egi':       item.EGI or '-',
            'component': item.COMPONENT or '-',
            'sn':        item.SN or '-',
            'lifetime':  item.LIFETIME or '-',
            'health':    health_pct,
            'status':    item.COMP_STATUS_HEALTH or '-',
        })

    # ============================================================
    # 🌟 11. DIRECT COST
    # ============================================================
    if cn_sap and cn_sap.upper() in [c.upper() for c in current_cn_saps]:
        directcost_qs = directcost.objects.filter(CN_SAP__icontains=cn_sap)
    elif current_cn_saps:
        directcost_qs = directcost.objects.filter(CN_SAP__in=current_cn_saps)
    else:
        directcost_qs = directcost.objects.none()  # ✅ FIX: Kosongkan jika tidak ada CN aktif

    if location and not cn_sap:
        directcost_qs = directcost_qs.filter(LOCATION=location)

    month_names = {
        1:'Jan', 2:'Feb', 3:'Mar', 4:'Apr', 5:'Mei', 6:'Jun',
        7:'Jul', 8:'Agu', 9:'Sep', 10:'Okt', 11:'Nov', 12:'Des'
    }

    aggregated_costs = (
        directcost_qs
        .values('LOCATION', 'YEAR', 'DATE', 'GL_ACCOUNT_TEXT', 'CN_SAP')
        .annotate(
            total_cost=Sum(
                Cast('COMP_CODE_CURR', output_field=DecimalField(max_digits=20, decimal_places=2))
            )
        )
        .order_by('CN_SAP', 'YEAR')
    )

    asset_egi_map = dict(
        AssetEquipment.objects.filter(CN_SAP__in=current_cn_saps)  # ✅ FIX: hanya dari cn aktif
        .exclude(CN_SAP__isnull=True).exclude(CN_SAP="")
        .values_list('CN_SAP', 'EGI')
    )

    grouped_data = {}
    for cost in aggregated_costs:
        cost_sum  = float(cost['total_cost']) if cost['total_cost'] else 0.0
        date_str  = cost.get('DATE') or ''
        month_text = '-'
        if date_str and len(date_str) >= 7:
            try:
                month_text = month_names.get(int(date_str[5:7]), '-')
            except (ValueError, IndexError):
                month_text = '-'

        key = (cost['CN_SAP'], cost['YEAR'], month_text, cost['GL_ACCOUNT_TEXT'], cost['LOCATION'])
        grouped_data[key] = grouped_data.get(key, 0.0) + cost_sum

    directcost_list = []
    for (cn_key, year_key, month_key, gl_key, loc_key), total_amount in grouped_data.items():
        directcost_list.append({
            'location':     loc_key or '-',
            'year':         year_key or '-',
            'month':        month_key,
            'direct_cost':  total_amount,
            'group_account': gl_key or '-',
            'cn_sap':       cn_key or '-',
            'egi':          asset_egi_map.get(cn_key, '-'),
        })

    # ============================================================
    # 🌟 12. BAR CHART BULANAN — IKUT FILTER ROLE
    # ============================================================
    # ✅ FIX: apply_role_filter ke AssetMonthlyStatus juga
    monthly_qs = apply_role_filter(AssetMonthlyStatus.objects.all())

    if location:     monthly_qs = monthly_qs.filter(LOCATION=location)
    if sub_location: monthly_qs = monthly_qs.filter(SUB_LOCATION=sub_location)
    if eq_class:     monthly_qs = monthly_qs.filter(GROUP=eq_class)
    if egi:          monthly_qs = monthly_qs.filter(EGI=egi)
    if cn_sap:       monthly_qs = monthly_qs.filter(CN_SAP__icontains=cn_sap)

    monthly_data = (
        monthly_qs
        .annotate(
            month_number=ExtractMonth('MONTH'),
            year_number=ExtractYear('MONTH'),
        )
        .values('year_number', 'month_number')
        .annotate(
            operate_count   = Count(Case(When(EQUIPMENT_CONDITION='OPERATE',   then=1), output_field=IntegerField())),
            breakdown_count = Count(Case(When(EQUIPMENT_CONDITION='BREAKDOWN', then=1), output_field=IntegerField())),
            standby_count   = Count(Case(When(EQUIPMENT_CONDITION='STANDBY',   then=1), output_field=IntegerField())),
            disposed_count  = Count(Case(When(EQUIPMENT_CONDITION='DISPOSED',  then=1), output_field=IntegerField())),
            prepare_disposed_count= Count(Case(When(EQUIPMENT_CONDITION__iexact='PREPARE FOR DISPOSED', then=1), output_field=IntegerField())),
            rfu_count       = Count(Case(When(BP='RFU', then=1),               output_field=IntegerField())),
        )
        .order_by('year_number', 'month_number')
    )

    bar_labels, bar_operate, bar_breakdown = [], [], []
    bar_standby, bar_disposed, bar_prepare_disposed, bar_rfu = [], [], [], [] # ✅ Tambahkan variabel list bar

    for row in monthly_data:
        bar_labels.append(f"{month_names.get(row['month_number'], '')} {row['year_number']}")
        bar_operate.append(row['operate_count'])
        bar_breakdown.append(row['breakdown_count'])
        bar_standby.append(row['standby_count'])
        bar_disposed.append(row['disposed_count'])
        bar_prepare_disposed.append(row['prepare_disposed_count'])
        bar_rfu.append(row['rfu_count'])

    # ============================================================
    # 🌟 13. DROPDOWN OPTIONS — TERKUNCI KE DATA YANG BERHAK DILIHAT
    # ============================================================
    def get_filtered_distinct(field_name, active_filters):
        """
        ✅ FIX: Base queryset HARUS dimulai dari apply_role_filter,
        bukan dari AssetEquipment.objects.all() mentah.
        """
        q_set = apply_role_filter(AssetEquipment.objects.all())  # ← KUNCI UTAMA
        for k, v in active_filters.items():
            if k != field_name and v:
                q_set = q_set.filter(**{k: v})
        return list(
            q_set.exclude(**{f'{field_name}__isnull': True})
            .exclude(**{field_name: ''})
            .values_list(field_name, flat=True)
            .distinct()
            .order_by(field_name)
        )

    current_filters = {
        'LOCATION':     location,
        'SUB_LOCATION': sub_location,
        'GROUP':        eq_class,
        'EGI':          egi,
        'CN_SAP':       cn_sap,
    }

    # ✅ FIX: Jika restricted, dropdown locations hanya berisi lokasi mereka
    if is_restricted:
        all_locations = [user_lokasi]
    else:
        all_locations = get_filtered_distinct('LOCATION', current_filters)

    all_sub_locations = get_filtered_distinct('SUB_LOCATION', current_filters)
    all_classes       = get_filtered_distinct('GROUP',        current_filters)
    all_egi           = get_filtered_distinct('EGI',          current_filters)
    all_cn_sap        = get_filtered_distinct('CN_SAP',       current_filters)

    # ============================================================
    # 🌟 14. MONITORING DOKUMEN — TERKUNCI KE CN_SAP YANG BERHAK DILIHAT
    # ============================================================
    FORM_DEFINITIONS = [
        {'model': FormLampiranCapex,                 'label': 'Lampiran Capex', 'icon': '📋'},
        {'model': FormPengajuanEquipmentDisposed,    'label': 'PDE',            'icon': '📄'},
        {'model': FormPengajuanDisposedSite,         'label': 'PDS',            'icon': '📝'},
        {'model': FormRepairCostAnalisis,            'label': 'RCA',            'icon': '🔧'},
        {'model': FormFotoKonditionUnit,             'label': 'Foto Kondisi',   'icon': '📷'},
    ]

    STATUS_LABELS = {
        'DRAFT': 'Draft', 'SUB': 'Submitted', 'APR1': 'Approved L1',
        'APR2': 'Approved L2', 'FIN': 'Final', 'REJ': 'Rejected'
    }
    STATUS_COLORS = {
        'DRAFT': '#888', 'SUB': '#1883ff', 'APR1': '#f57c00',
        'APR2': '#9c27b0', 'FIN': '#28a745', 'REJ': '#dc3545'
    }

    filter_status    = request.GET.get('status', '').strip().upper()
    filter_form_type = request.GET.get('form_type', '').strip()

    # ✅ FIX: allowed_cn_saps berasal dari qs yang sudah terfilter role
    allowed_cn_saps = qs.values_list('CN_SAP', flat=True)

    ajax_documents = []
    for form_def in FORM_DEFINITIONS:
        if filter_form_type and filter_form_type.lower() != form_def['label'].lower():
            continue

        # ✅ FIX: Filter CN_SAP ke allowed_cn_saps yang sudah terkunci role
        doc_qs = form_def['model'].objects.filter(CN_SAP__in=allowed_cn_saps)

        if filter_status:
            doc_qs = doc_qs.filter(status=filter_status)

        # User biasa hanya lihat dokumen milik sendiri
        if not (request.user.is_superuser or request.user.is_staff):
            doc_qs = doc_qs.filter(diajukan_oleh=request.user)

        for doc in doc_qs.select_related('diajukan_oleh').order_by('-updated_at'):
            date_sorting = doc.updated_at if doc.updated_at else timezone.now()
            elapsed = '-'
            if doc.submitted_at:
                delta = timezone.now() - doc.submitted_at
                elapsed = (f"{delta.days}h {delta.seconds // 3600}j"
                           if delta.days > 0 else f"{delta.seconds // 3600}j")

            opt = doc._meta
            ajax_documents.append({
                'pk':           doc.pk,
                'cn_sap':       getattr(doc, 'CN_SAP', '-'),
                'form_type':    form_def['label'],
                'form_icon':    form_def['icon'],
                'status':       doc.status,
                'status_label': STATUS_LABELS.get(doc.status, doc.status),
                'status_color': STATUS_COLORS.get(doc.status, '#888'),
                'diajukan_oleh': (
                    doc.diajukan_oleh.get_full_name() or doc.diajukan_oleh.username
                    if doc.diajukan_oleh else '-'
                ),
                'submitted_at': doc.submitted_at.strftime('%d/%m/%Y %H:%M') if doc.submitted_at else '-',
                'updated_at':   date_sorting.strftime('%d/%m/%Y %H:%M'),
                'raw_date':     date_sorting,
                'elapsed':      elapsed,
                'view_url':     f"/admin/{opt.app_label}/{opt.model_name}/{doc.pk}/change/",
            })

    ajax_documents.sort(key=lambda x: x['raw_date'], reverse=True)
    for doc_item in ajax_documents:
        doc_item.pop('raw_date', None)

    
    # ============================================================
    # 🌟 15. TAMBAHAN: Kirim flag sections ke response AJAX
    #    Agar JS bisa show/hide section saat filter berubah
    # ============================================================
    dashboard_sections = {
        'show_summary_cards':   True,
        'show_pie_chart':       True,
        'show_bar_chart':       True,
        'show_conmon':          True,
        'show_direct_cost':     True,
        'show_foto_unit':       True,
        'show_monitoring_docs': True,
        'show_disposed_table':  True,
    }

    if is_restricted:
        lokasi_upper  = user_lokasi.upper()
        section_upper = user_section.upper()

        if 'ADMO' in lokasi_upper:
            if any(s in section_upper for s in ['MINING-PHW', 'MINING - PHW', 'MINING-PSU', 'MINING - PSU']):
                dashboard_sections.update({
                    'show_conmon':      False,
                    'show_direct_cost': False,
                })
            elif 'PLANT' in section_upper:
                dashboard_sections.update({
                    'show_direct_cost': False,
                })

        elif 'JAHO' in lokasi_upper:
            dashboard_sections.update({
                'show_disposed_table': False,
            })

        else:
            dashboard_sections.update({
                'show_conmon':        False,
                'show_direct_cost':   False,
                'show_disposed_table': False,
            })

    # ============================================================
    # 🌟 16. RESPONSE
    # ============================================================
    return JsonResponse({
        'counts':                   counts,
        'disposed_by_location':     disposed_by_location,
        'disposed_by_sub_location': disposed_by_sub,
        'disposed_by_egi':          disposed_by_egi,
        'disposed_by_cn':           disposed_by_cn,
        # ✅ TAMBAHKAN STATISTIK PREPARE DISPOSED DI SINI:
        'prepare_stats': {
            'total': total_prepare_unit,
            'complete': prepare_complete_count,
            'progress': prepare_progress_count,
            'percentage': prepare_avg_progress,
            'documents': doc_counts,
        },
        'prepare_units': prepare_units_list, 
        'is_admin_view':            request.user.is_superuser or request.user.is_staff,
        'conmon_data':              conmon_list,
        'status':                   'success',
        'unit_photo_url':           unit_photo_url,
        'directcost_data':          directcost_list,
        'dashboard_sections':       dashboard_sections,
        'bar_chart': {
            'labels':    bar_labels,
            'operate':   bar_operate,
            'breakdown': bar_breakdown,
            'standby':   bar_standby,
            'disposed':  bar_disposed,
            'prepare_disposed': bar_prepare_disposed,
            'rfu':       bar_rfu,
        },
        'filter_options': {
            'locations':     all_locations,
            'sub_locations': all_sub_locations,
            'classes':       all_classes,
            'egi':           all_egi,
            'cn_sap':        all_cn_sap,
        },
        'active_filters': {
            'location':     detected_location,
            'sub_location': detected_sub_location,
            'eq_class':     eq_class,
            'egi':          egi,
            'cn_sap':       cn_sap,
        },
        'monitoring_documents': ajax_documents,
        'monitoring_total':     len(ajax_documents),
    })


# asset/views.py — tambahkan fungsi baru

# asset/views.py
from django.http import JsonResponse
from django.contrib.admin.views.decorators import staff_member_required
from django.views.decorators.http import require_GET
from .models import AssetEquipmentDisposed
from django.core.paginator import Paginator, EmptyPage, PageNotAnInteger

@staff_member_required
@require_GET
def document_tracking_summary(request):
    """
    Endpoint AJAX untuk monitoring progress dokumen per CN_SAP di dashboard INSIDE.
    """
    # Filter role berdasarkan lokasi & section user login
    user_lokasi  = ""
    user_section = ""
    is_restricted = False

    if not request.user.is_superuser and hasattr(request.user, 'userprofile'):
        user_lokasi  = request.user.userprofile.lokasi or ""
        user_section = request.user.userprofile.section or ""
        if user_lokasi:
            is_restricted = True

    # Menggunakan select_related untuk mengoptimalkan performa load database
    qs = AssetEquipmentDisposed.objects.select_related('asset')
    
    if is_restricted:
        qs = qs.filter(LOCATION__iexact=user_lokasi)
        if user_section:
            qs = qs.filter(SECTION__iexact=user_section)

    # Hitung summary global dashboard
    total_unit         = qs.count()
    total_all_complete = sum(1 for t in qs if t.is_all_complete)
    total_progress     = total_unit - total_all_complete

       # Summary persentase per jenis dokumen (menghindari ZeroDivisionError)
    doc_summary = {}
    for field, label in AssetEquipmentDisposed.DOC_LABELS.items():
        complete_count = sum(1 for unit in qs if getattr(unit, field))
        doc_summary[label] = {
            'complete': complete_count,
            'progress': total_unit - complete_count,
            # ✅ FIX: Proteksi jika total_unit masih 0 agar tidak memicu ZeroDivisionError
            'persen':   round((complete_count / total_unit * 100)) if total_unit > 0 else 0,
        }

    # Detail data progress per unit (CN_SAP)
    unit_details = []
    for unit in qs:
        cn_sap = unit.asset.CN_SAP if unit.asset else '-'
        status_per_dok = unit.get_status_per_dokumen()

        unit_details.append({
            'cn_sap':       cn_sap,
            'location':     unit.LOCATION or '-',
            'egi':          unit.EGI or '-',
            'section':      unit.SECTION or '-',
            'complete':     unit.jumlah_complete,
            'progress':     unit.jumlah_progress,
            'total':        unit.total_dokumen,
            'persen':       unit.persentase_complete,
            'all_complete': unit.is_all_complete,
            'dokumen': {
                label: status_per_dok[field]
                for field, label in AssetEquipmentDisposed.DOC_LABELS.items()
            }
        })

    # Kembalikan response JSON yang menyertakan data navigasi halaman

    return JsonResponse({
        'summary': {
            'total_unit':       total_unit,
            'all_complete':     total_all_complete,
            'in_progress':      total_progress,
        },
        'doc_summary':  doc_summary,
        'unit_details': unit_details,        
    })


from django.shortcuts import render
from django.contrib.admin.views.decorators import staff_member_required

@staff_member_required
def load_capex_form(request):
    """Endpoint untuk load HTML modal Lampiran Capex via AJAX."""
    return render(request, "modal_capex_disposed.html")

@staff_member_required
def load_ba_standby_form(request):
    """ Endpoint untuk load HTML modal BA Standby via AJAX"""
    return render(request, "modal_ba_standby.html")

@login_required
def prepare_for_disposed_list_view(request):
    """
    🌟 SIDE MENU BARU (FASE 1): 
    View untuk menampilkan daftar unit yang berstatus PREPARE FOR DISPOSED
    beserta tombol upload/unduh 4 DOKUMEN AWAL (Foto 4 Sisi, RCA, Inspeksi, Pengajuan).
    """
    # 1. Ambil Queryset Utama dari Model Mandiri khusus Prepare
    qs = AssetEquipmentPrepareDisposed.objects.filter(
        EQUIPMENT_CONDITION__iexact='PREPARE FOR DISPOSED'
    )

    # 2. Fitur Keamanan Level Data (Role-Based Security)
    if not request.user.is_superuser:
        if hasattr(request.user, 'userprofile'):
            profile = request.user.userprofile
            user_lokasi = profile.lokasi
            user_section = profile.section
            
            if user_lokasi:
                qs = qs.filter(LOCATION__iexact=user_lokasi)
                if user_section:
                    qs = qs.filter(SECTION__iexact=user_section)
            else:
                qs = qs.none()  # Kunci data jika tidak punya lokasi
        else:
            qs = qs.none()

    # 3. Fitur Pencarian (Search Bar di Frontend)
    search_query = request.GET.get('search', '').strip()
    if search_query:
        qs = qs.filter(
            Q(asset__CN_SAP__icontains=search_query) |
            Q(No_Asset__icontains=search_query) |
            Q(EGI__icontains=search_query) |
            Q(REFERENSI_NO_PDE__icontains=search_query)
        )

    # 4. Fitur Filter Dropdown (EGI & Location)
    filter_egi = request.GET.get('egi', '').strip()
    if filter_egi:
        qs = qs.filter(EGI__iexact=filter_egi)

    # Ambil list unik EGI untuk opsi dropdown di HTML
    egi_list = qs.values_list('EGI', flat=True).distinct().order_by('EGI')

    context = {
        'prepare_units': qs,          # Dikirim ke HTML prepare
        'egi_list': egi_list,
        'search_query': search_query,
        'selected_egi': filter_egi,
    }
    return render(request, 'asset/prepare_disposed_list.html', context)



@login_required
def upload_disposed_document_api(request, cn_sap):
    """
    API/View endpoint khusus untuk menangani interaksi tombol upload dokumen 
    dari Frontend (bisa via AJAX Form / Form Post biasa).
    """
    if request.method == 'POST':
        # Ambil data record berdasarkan CN_SAP (Primary Key pada model mandiri Prepare/Disposed)
        disposed_unit = get_object_or_404(AssetEquipmentPrepareDisposed, asset__CN_SAP__iexact=cn_sap)
        
        # Ambil jenis dokumen apa yang diupload (misal: 'foto_4_sisi', 'rca', dll)
        doc_type = request.POST.get('doc_type', '').strip()
        
        if doc_type not in AssetEquipmentPrepareDisposed.DOC_FIELDS:
            messages.error(request, "Jenis dokumen tidak valid.")
            return redirect(request.META.get('HTTP_REFERER', '/'))

        # Ambil file dari request.FILES
        uploaded_file = request.FILES.get('document_file')
        
        if uploaded_file:
            now = timezone.now()
            # 1. Simpan file ke kolom dokumen yang sesuai
            setattr(disposed_unit, doc_type, uploaded_file)
            # 2. Catat metadata log uploader
            setattr(disposed_unit, f'{doc_type}_uploaded_at', now)
            setattr(disposed_unit, f'{doc_type}_uploaded_by', request.user)
            
            disposed_unit.save()
            messages.success(request, f"Dokumen {disposed_unit.DOC_LABELS.get(doc_type)} berhasil diupload!")
        else:
            messages.error(request, "Gagal upload, file tidak ditemukan.")

    return redirect(request.META.get('HTTP_REFERER', '/'))

def _get_model_and_object(doc_type, cn_sap):
    """ Helper dinamis untuk memetakan model berdasarkan jenis dokumen dan Fase-nya """
    phase_1_docs = ['foto_4_sisi', 'inspeksi_unit', 'rca', 'pengajuan_disposed']
    
    if doc_type in phase_1_docs:
        # Cek apakah unit sudah ada di AssetEquipmentDisposed (Fase 2)
        obj = AssetEquipmentDisposed.objects.filter(asset__CN_SAP__iexact=cn_sap).first()
        if obj:
            return obj, AssetEquipmentDisposed
            
        # Jika belum ada di Disposed, ambil dari AssetEquipmentPrepareDisposed (Fase 1)
        model_cls = AssetEquipmentPrepareDisposed
        # ✅ PERBAIKAN: Gunakan asset__CN_SAP__iexact karena CN_SAP ada di tabel relasi induk
        obj = model_cls.objects.filter(asset__CN_SAP__iexact=cn_sap).first()
    else:
        # Untuk dokumen Fase 2
        model_cls = AssetEquipmentDisposed
        obj = model_cls.objects.filter(asset__CN_SAP__iexact=cn_sap).first()
        
    if not obj:
        raise model_cls.DoesNotExist(f'Data unit dengan CN_SAP "{cn_sap}" tidak ditemukan pada fase ini.')
        
    return obj, model_cls

@staff_member_required
@require_POST
def upload_quick_disposed(request):
    cn_sap   = request.POST.get('cn_sap', '').strip()
    doc_type = request.POST.get('doc_type', '').strip()
    doc_file = request.FILES.get('document_file')

    if not cn_sap:
        return JsonResponse({'success': False, 'error': 'CN_SAP tidak ditemukan.'}, status=400)
    if not doc_type:
        return JsonResponse({'success': False, 'error': 'Jenis dokumen tidak ditemukan.'}, status=400)
    if not doc_file:
        return JsonResponse({'success': False, 'error': 'File tidak ditemukan.'}, status=400)

    try:
        obj, model_cls = _get_model_and_object(doc_type, cn_sap)
    except (AssetEquipmentDisposed.DoesNotExist, AssetEquipmentPrepareDisposed.DoesNotExist, AssetEquipmentStandby.DoesNotExist, AssetEquipmentBreakdown.DoesNotExist):
        return JsonResponse({'success': False, 'error': f'Data CN_SAP "{cn_sap}" tidak ditemukan.'}, status=404)
    except Exception as e:
        return JsonResponse({'success': False, 'error': str(e)}, status=500)

    if doc_type not in model_cls.DOC_FIELDS:
        return JsonResponse({'success': False, 'error': f'Jenis dokumen "{doc_type}" tidak valid.'}, status=400)

    if not request.user.is_superuser:
        if hasattr(request.user, 'userprofile'):
            profile      = request.user.userprofile
            user_lokasi  = profile.lokasi or ""
            user_section = profile.section or ""
            obj_location = getattr(obj, 'LOCATION', '') or ''
            obj_section  = getattr(obj, 'SECTION', '')  or ''

            if user_lokasi and obj_location.lower() != user_lokasi.lower():
                return JsonResponse({'success': False, 'error': 'Anda tidak berhak untuk lokasi ini.'}, status=403)
            if user_section and obj_section.lower() != user_section.lower():
                return JsonResponse({'success': False, 'error': 'Anda tidak berhak untuk section ini.'}, status=403)

    # ✅ Inisialisasi variabel OCR — berlaku untuk semua doc_type
    ocr_valid    = True
    ocr_message  = "File berhasil diunggah"
    no_dokumen   = "-"
    nama_dok_ocr = "-"
    usd_max      = "-"

    # Variabel tambahan penampung struktur detail error visual khusus foto 4 sisi
    detail_foto_results = None


    # ============================================================
    # OCR SEBELUM SIMPAN — khusus dokumen RCA
    # ============================================================
    if doc_type == "rca":
        try:
            import tempfile, os

            ext      = os.path.splitext(doc_file.name)[1].lower()
            tmp_file = tempfile.NamedTemporaryFile(delete=False, suffix=ext)
            for chunk in doc_file.chunks():
                tmp_file.write(chunk)
            tmp_file.close()
            tmp_path = tmp_file.name

            serial_number         = getattr(obj, "SN",  "") or ""
            egi                   = getattr(obj, "EGI", "") or ""
            EXPECTED_NO_DOKUMEN   = "PLO/09/F-020"
            EXPECTED_NAMA_DOKUMEN = "REPAIR COST ANALYSIS"

            from .utils_ocr import verifikasi_dokumen_rca
            ocr_valid, ocr_message, no_dokumen, nama_dok_ocr, usd_max = verifikasi_dokumen_rca(
                tmp_path, cn_sap, egi, serial_number,
                expected_no=EXPECTED_NO_DOKUMEN,
                expected_nama=EXPECTED_NAMA_DOKUMEN,
            )

        except Exception as ocr_err:
            ocr_valid    = False
            ocr_message  = f"Sistem OCR gagal dijalankan: {str(ocr_err)}"
            no_dokumen   = "-"
            nama_dok_ocr = "-"
            usd_max      = "-"

        finally:
            if 'tmp_path' in locals() and os.path.exists(tmp_path):
                os.remove(tmp_path)

        if not ocr_valid:
            return JsonResponse({
                'success':     False,
                'ocr_failed':   True,
                'ocr_valid':    False,
                'ocr_message':  ocr_message,
                'no_dokumen':   no_dokumen,
                'nama_dok_ocr': nama_dok_ocr,
                'usd_max':      usd_max,
                'cn_sap':       cn_sap,
                'doc_type':     doc_type,
            })

        doc_file.seek(0)

    # ============================================================
    # OCR SEBELUM SIMPAN — khusus dokumen Pengajuan Disposed
    # ============================================================
    elif doc_type == "pengajuan_disposed":
        try:
            import tempfile, os

            ext      = os.path.splitext(doc_file.name)[1].lower()
            tmp_file = tempfile.NamedTemporaryFile(delete=False, suffix=ext)
            for chunk in doc_file.chunks():
                tmp_file.write(chunk)
            tmp_file.close()
            tmp_path = tmp_file.name

            serial_number         = getattr(obj, "SN",  "") or ""
            egi                   = getattr(obj, "EGI", "") or ""
            EXPECTED_NO_DOKUMEN   = "PBA/14/F-003"
            EXPECTED_NAMA_DOKUMEN = "FORM PENGAJUAN DISPOSE EQUIPMENT"

            from .utils_ocr import verifikasi_dokumen_pengajuan_disposed

            ocr_valid, ocr_message, no_dokumen, nama_dok_ocr, no_pengajuan = verifikasi_dokumen_pengajuan_disposed(
                tmp_path, cn_sap, egi, serial_number,
                expected_no=EXPECTED_NO_DOKUMEN,
                expected_nama=EXPECTED_NAMA_DOKUMEN,
            )
            usd_max = no_pengajuan  # ✅ reuse usd_max untuk kirim no_pengajuan ke signal

        except Exception as ocr_err:
            ocr_valid    = False
            ocr_message  = f"Sistem OCR gagal dijalankan: {str(ocr_err)}"
            no_dokumen   = "-"
            nama_dok_ocr = "-"
            usd_max      = "-"

        finally:
            if 'tmp_path' in locals() and os.path.exists(tmp_path):
                os.remove(tmp_path)

        if not ocr_valid:
            return JsonResponse({
                'success':     False,
                'ocr_failed':   True,
                'ocr_valid':    False,
                'ocr_message':  ocr_message,
                'no_dokumen':   no_dokumen,
                'nama_dok_ocr': nama_dok_ocr,      
                'cn_sap':       cn_sap,
                'doc_type':     doc_type,
            })

        doc_file.seek(0)


    # ============================================================
    # 🌟 OCR SEBELUM SIMPAN — khusus dokumen Foto 4 Sisi Unit
    # ============================================================
    elif doc_type == "foto_4_sisi":
        try:
            import tempfile, os
            from .utils_ocr import extract_text_from_file, verifikasi_foto_empat_sisi

            ext      = os.path.splitext(doc_file.name)[1].lower()
            tmp_file = tempfile.NamedTemporaryFile(delete=False, suffix=ext)
            for chunk in doc_file.chunks():
                tmp_file.write(chunk)
            tmp_file.close()
            tmp_path = tmp_file.name

            serial_number = getattr(obj, "SN", "") or ""
            unit_model    = getattr(obj, "MODEL", "") or getattr(obj, "EGI", "")

            extracted_text, _, _ = extract_text_from_file(tmp_path)

            is_valid_foto, msg_foto, no_dok_foto, nama_dok_foto, detail_error_foto = verifikasi_foto_empat_sisi(
                file_path=tmp_path,
                target_cn=cn_sap,
                target_sn=serial_number,
                unit_model=unit_model,
                extracted_text=extracted_text
            )

            ocr_valid    = is_valid_foto
            ocr_message  = msg_foto
            no_dokumen   = no_dok_foto
            nama_dok_ocr = nama_dok_foto
            detail_foto_results = detail_error_foto

        except Exception as ocr_err:
            ocr_valid    = False
            ocr_message  = f"Sistem OCR gagal menganalisis foto: {str(ocr_err)}"
            detail_foto_results = {
                "tampak_depan": False,
                "tampak_belakang": False,
                "tampak_kanan": False,
                "tampak_kiri": False,
                "cn_status": False,
                "sn_status": False,
                "model_status": False
            }

        finally:
            if 'tmp_path' in locals() and os.path.exists(tmp_path):
                os.remove(tmp_path)

        if not ocr_valid:
            return JsonResponse({
                'success':     False,
                'ocr_failed':   True,
                'ocr_valid':    False,
                'ocr_message':  ocr_message,
                'cn_sap':       cn_sap,
                'doc_type':     doc_type,
                'detail_error': detail_foto_results 
            })

        doc_file.seek(0)

    # ============================================================
    # 🌟 OCR SEBELUM SIMPAN — khusus dokumen Inspeksi Unit (Check Sheet)
    # ============================================================
    elif doc_type == "inspeksi_unit":
        try:
            import tempfile, os
            from .utils_ocr import verifikasi_dokumen_inspeksi

            ext      = os.path.splitext(doc_file.name)[1].lower()
            tmp_file = tempfile.NamedTemporaryFile(delete=False, suffix=ext)
            for chunk in doc_file.chunks():
                tmp_file.write(chunk)
            tmp_file.close()
            tmp_path = tmp_file.name

            serial_number = getattr(obj, "SN", "") or ""
            unit_model    = getattr(obj, "MODEL", "") or getattr(obj, "EGI", "")

            ocr_valid, ocr_message, no_dokumen, nama_dok_ocr, _ = verifikasi_dokumen_inspeksi(
                file_path=tmp_path,
                target_cn=cn_sap,
                target_sn=serial_number,
                unit_model=unit_model,
                expected_nama="CHECK SHEET"
            )

        except Exception as ocr_err:
            ocr_valid    = False
            ocr_message  = f"Sistem OCR gagal menganalisis Check Sheet: {str(ocr_err)}"
            no_dokumen   = "-"
            nama_dok_ocr = "-"

        finally:
            if 'tmp_path' in locals() and os.path.exists(tmp_path):
                os.remove(tmp_path)

        if not ocr_valid:
            return JsonResponse({
                'success':     False,
                'ocr_failed':   True,
                'ocr_valid':    False,
                'ocr_message':  ocr_message,
                'no_dokumen':   no_dokumen,
                'nama_dok_ocr': nama_dok_ocr,      
                'cn_sap':       cn_sap,
                'doc_type':     doc_type,
            })

        doc_file.seek(0)


    # ============================================================
    # PROSES SIMPAN KE DATABASE (Fase 1 & Fase 2 Terintegrasi)
    # ============================================================
    try:
        setattr(obj, doc_type, doc_file)

        if hasattr(obj, f'{doc_type}_uploaded_at'):
            setattr(obj, f'{doc_type}_uploaded_at', timezone.now())
        if hasattr(obj, f'{doc_type}_uploaded_by'):
            setattr(obj, f'{doc_type}_uploaded_by', request.user)
        if hasattr(obj, 'updated_by'):
            obj.updated_by = request.user
        
        # ✅ Tempelkan data status validasi dasar ke atribut objek untuk dibaca signals.py
        obj._ocr_valid    = ocr_valid
        obj._ocr_message  = ocr_message
        obj._no_dokumen   = no_dokumen
        obj._nama_dok_ocr = nama_dok_ocr
        obj._usd_max      = usd_max       

        if doc_type == "foto_4_sisi" and detail_foto_results:
            obj._ocr_depan    = detail_foto_results.get("tampak_depan", False)
            obj._ocr_belakang = detail_foto_results.get("tampak_belakang", False)
            obj._ocr_kanan    = detail_foto_results.get("tampak_kanan", False)
            obj._ocr_kiri     = detail_foto_results.get("tampak_kiri", False)
        else:
            obj._ocr_depan    = True
            obj._ocr_belakang = True
            obj._ocr_kanan    = True
            obj._ocr_kiri     = True

        # 🌟 PENYESUAIAN DINAMIS: Cek apakah objek ini bagian dari Fase 1 atau Fase 2
        if issubclass(model_cls, AssetEquipmentPrepareDisposed):
            # ✅ Gunakan STATUS_EQUIPMENT sesuai nama kolom yang ada di model mandiri
            base_fields = ['EQUIPMENT_CONDITION', 'STATUS_EQUIPMENT', f'{doc_type}_uploaded_at', f'{doc_type}_uploaded_by', 'updated_by']
        else:
            base_fields = [f'{doc_type}_uploaded_at', f'{doc_type}_uploaded_by', 'updated_by']
        # ✅ Simpan secara dinamis berdasarkan update_fields masing-masing tipe dokumen
        if doc_type == "rca":
            obj.save(update_fields=['rca'] + base_fields)
        elif doc_type == "pengajuan_disposed":
            obj.save(update_fields=['pengajuan_disposed'] + base_fields)
        elif doc_type == "foto_4_sisi":
            obj.save(update_fields=['foto_4_sisi'] + base_fields)
        elif doc_type == "inspeksi_unit":
            obj.save(update_fields=['inspeksi_unit'] + base_fields)
        else:
            obj.save(update_fields=[doc_type] + base_fields)


             
        doc_label = model_cls.DOC_LABELS.get(doc_type, doc_type)
        
        return JsonResponse({
            'success':     True,
            'cn_sap':       cn_sap,
            'doc_type':     doc_type,
            'doc_label':    doc_label,
            'file_url':     getattr(obj, doc_type).url if getattr(obj, doc_type) else None,
            'ocr_valid':    ocr_valid,
            'ocr_message':  ocr_message,
            'usd_max':      usd_max,
            'no_pengajuan': usd_max if doc_type == 'pengajuan_disposed' else None,             
        })

    except Exception as e:
        import traceback
        traceback.print_exc()
        return JsonResponse({'success': False, 'error': f'Gagal menyimpan: {str(e)}'}, status=500)


@staff_member_required
@require_POST
def delete_quick_disposed(request):
    """
    Endpoint AJAX dinamis untuk menghapus/mengosongkan file dokumen disposal dan prepare.
    """
    cn_sap   = request.POST.get('cn_sap', '').strip()
    doc_type = request.POST.get('doc_type', '').strip()

    if not cn_sap or not doc_type:
        return JsonResponse({'success': False, 'error': 'Parameter tidak lengkap.'}, status=400)

    try:
        obj, model_cls = _get_model_and_object(doc_type, cn_sap)
        
        if not hasattr(obj, doc_type):
            return JsonResponse({'success': False, 'error': 'Field dokumen tidak valid pada model ini.'}, status=400)

        file_field = getattr(obj, doc_type)
        if file_field:
            try:
                file_field.delete(save=False)
            except Exception as file_err:
                print(f"[Warning] Gagal menghapus file fisik: {file_err}")
            
        setattr(obj, doc_type, None)
        
        update_fields = [doc_type]

        if hasattr(obj, f'{doc_type}_uploaded_at'):
            setattr(obj, f'{doc_type}_uploaded_at', None)
            update_fields.append(f'{doc_type}_uploaded_at')
            
        if hasattr(obj, f'{doc_type}_uploaded_by'):
            setattr(obj, f'{doc_type}_uploaded_by', None)
            update_fields.append(f'{doc_type}_uploaded_by')

        for status_field in ['EQUIPMENT_CONDITION', 'STATUS_EQUIPMENT_DISPOSED']:
            if hasattr(obj, status_field):
                update_fields.append(status_field)

        if hasattr(obj, 'updated_by'):
            obj.updated_by = request.user
            update_fields.append('updated_by')

        obj.save(update_fields=update_fields)

        doc_label = getattr(model_cls, 'DOC_LABELS', {}).get(doc_type, doc_type)

        return JsonResponse({
            'success': True,
            'cn_sap': cn_sap,
            'doc_label': doc_label,
            'file_url': None,
        })

    except model_cls.DoesNotExist:
        return JsonResponse({'success': False, 'error': 'Data unit tidak ditemukan pada fase ini.'}, status=404)
    except Exception as e:
        import traceback
        traceback.print_exc()
        return JsonResponse({'success': False, 'error': f'Gagal menghapus: {str(e)}'}, status=500)
    

#=====================================================================================================
#==================== END POINT UNTUK FORM FOTO 4 SISI UNIT DISPOSED =================================
#======================================================================================================


@login_required  
@require_POST
def upload_foto_4_sisi_disposed(request):
    if not request.user.is_staff:
        return JsonResponse({'status': 'error', 'message': 'Akses ditolak.'}, status=403)

    cn_sap = request.POST.get('cn_sap', '').strip()
    if not cn_sap:
        return JsonResponse({'status': 'error', 'message': 'CN_SAP tidak ditemukan.'}, status=400)

    file_depan    = request.FILES.get('tampak_depan')
    file_belakang = request.FILES.get('tampak_belakang')
    file_kanan    = request.FILES.get('tampak_samping_kanan')
    file_kiri     = request.FILES.get('tampak_samping_kiri')

    # Memastikan ke-4 file diunggah secara bersamaan
    if not all([file_depan, file_belakang, file_kanan, file_kiri]):
        return JsonResponse({
            'status': 'error',
            'message': 'Keempat foto (depan, belakang, kanan, kiri) wajib diunggah.'
        }, status=400)

    # Validasi ekstensi
    allowed_ext = ['.jpg', '.jpeg', '.png', '.pdf']
    for f in [file_depan, file_belakang, file_kanan, file_kiri]:
        ext = os.path.splitext(f.name)[1].lower()
        if ext not in allowed_ext:
            return JsonResponse({
                'status': 'error',
                'message': f'Format file tidak didukung: {f.name}. Gunakan JPG, PNG, atau PDF.'
            }, status=400)

    try:
        from .models import AssetEquipmentPrepareDisposed, AssetEquipmentDisposed

        # ── PERBAIKAN: Gunakan asset__CN_SAP__iexact agar aman jika PK berupa relasi ──
        obj = AssetEquipmentPrepareDisposed.objects.filter(
            asset__CN_SAP__iexact=cn_sap
        ).first()

        if not obj:
            disposed_obj = AssetEquipmentDisposed.objects.filter(
                asset__CN_SAP__iexact=cn_sap
            ).first()
            if disposed_obj:
                return JsonResponse({
                    'status': 'error',
                    'message': f'Unit {cn_sap} sudah berada di Disposed. Upload tidak diperlukan.'
                }, status=400)
            return JsonResponse({
                'status': 'error',
                'message': f'Data CN_SAP "{cn_sap}" tidak ditemukan di Prepare Disposed.'
            }, status=404)

        # ── 🧹 CLEANUP STORAGE: Hapus file fisik lama jika user me-replace foto ──
        old_files = [obj.tampak_depan, obj.tampak_belakang, obj.tampak_samping_kanan, obj.tampak_samping_kiri]
        for old_file in old_files:
            if old_file and hasattr(old_file, 'path') and os.path.exists(old_file.path):
                try:
                    os.remove(old_file.path)
                except Exception:
                    pass

        # ── 💾 ASSIGN FILE BARU ──
        obj.tampak_depan         = file_depan
        obj.tampak_belakang      = file_belakang
        obj.tampak_samping_kanan = file_kanan
        obj.tampak_samping_kiri  = file_kiri

        # Tetap gunakan metadata ini untuk memonitor kapan 4 foto di-upload
        obj.submitted_at            = timezone.now()
        obj.foto_4_sisi_uploaded_at = timezone.now()
        obj.foto_4_sisi_uploaded_by = request.user
        obj.updated_by              = request.user


        # ── 🔄 TAMBAHAN LOGIKA OTOMATIS: JIKA DI-REPLACE SAAT SUDAH APPROVED / REJECTED ──
        # Jika dokumen sebelumnya sudah disetujui (APPROVED) atau ditolak (REJECTED),
        # lalu user melakukan upload/ganti foto baru, maka alur approval di-reset ke WAITING
        if obj.status_approval in ['APPROVED', 'REJECTED']:
            # Ambil profil user untuk mencari atasan langsungnya kembali
            user_profile = getattr(request.user, 'userprofile', None)
            atasan_profile = user_profile.atasan_langsung if user_profile else None
            
            if atasan_profile and atasan_profile.user:
                obj.status_approval = 'WAITING'
                obj.current_approver = atasan_profile.user
                obj.submitted_at = timezone.now()      # Catat waktu submit ulang
                obj.submitted_by = request.user        # Catat siapa yang merevisi/submit ulang
                obj.approved_at = None                 # Bersihkan timestamp approve lama
                obj.approved_by = None
                obj.rejected_at = None                 # Bersihkan timestamp reject lama
                obj.rejected_by = None
            else:
                # Fallback jika atasan belum diset, kembalikan ke DRAFT agar tidak error
                obj.status_approval = 'DRAFT'
                obj.current_approver = None

        # 2. JIKA STATUSNYA MASIH DRAFT / KOSONG (Pertama kali upload):
        #    Biarkan tetap DRAFT sesuai keinginan Anda. Tidak ada perubahan status ke WAITING.
        elif not obj.status_approval or obj.status_approval == 'DRAFT':
            obj.status_approval = 'DRAFT'
            # Pastikan current_approver kosong karena belum disubmit
            obj.current_approver = None

        obj.save()

        return JsonResponse({
            'status':  'success',
            'cn_sap':  cn_sap,
            'message': 'Keempat foto berhasil diunggah dan disimpan.',
        })

    except Exception as e:
        import traceback
        traceback.print_exc()
        return JsonResponse({'status': 'error', 'message': str(e)}, status=500)


from django.contrib.auth.decorators import login_required
from django.views.decorators.http import require_POST
from django.http import HttpResponse, JsonResponse
from django.shortcuts import get_object_or_404
from .models import AssetEquipmentPrepareDisposed
from .utils_ocr import generate_foto_4_sisi_pdf  # Mengimpor modul utils yang baru dibuat

@login_required
def download_pdf_foto_4_sisi(request, cn_sap):
    if not request.user.is_staff:
        return HttpResponse('Akses ditolak.', status=403)

    obj = get_object_or_404(AssetEquipmentPrepareDisposed, asset__CN_SAP__iexact=cn_sap)

    # Validasi kelengkapan 4 foto
    if not all([obj.tampak_depan, obj.tampak_belakang, obj.tampak_samping_kanan, obj.tampak_samping_kiri]):
        return HttpResponse('Foto 4 sisi belum lengkap diunggah.', status=400)

    # Cek apakah ini mode print atau download murni
    is_print_mode = request.GET.get('print') == 'true'

    # Serahkan pembuatan PDF ke utils.py (pastikan fungsi utils Anda menangani parameter as_attachment/inline)
    response = generate_foto_4_sisi_pdf(obj, cn_sap, request=request, print_mode=is_print_mode)
    
    return response

@login_required
@require_POST
def submit_approval_disposed(request, cn_sap=None):
    if not cn_sap:
        cn_sap = request.POST.get('cn_sap', '').strip()
    else:
        cn_sap = cn_sap.strip()

    if not cn_sap:
        return JsonResponse({'status': 'error', 'message': 'CN_SAP tidak ditemukan.'}, status=400)

    obj = AssetEquipmentPrepareDisposed.objects.filter(asset__CN_SAP__iexact=cn_sap).first()
    if not obj:
        return JsonResponse({'status': 'error', 'message': 'Data unit tidak ditemukan.'}, status=404)

    # 1. JIKA ATASAN MELAKUKAN APPROVAL (Saat status sedang WAITING dan yang membuka adalah approver)
    if getattr(obj, 'foto_4_sisi_status', None) == 'WAITING' and getattr(obj, 'foto_4_sisi_approver', None) == request.user:
        now = timezone.now()
        
        # Update status khusus foto 4 sisi
        obj.foto_4_sisi_status = 'APPROVED'
        obj.foto_4_sisi_approved_at = now
        obj.foto_4_sisi_approved_by = request.user
        obj.foto_4_sisi_approver = None
        
        # Update status global/utama agar tabel halaman utama ikut berubah jadi Disetujui
        obj.status_approval = 'APPROVED'
        obj.approved_at = now
        obj.approved_by = request.user
        obj.current_approver = None
        
        obj.updated_by = request.user
        obj.save()
        
        return JsonResponse({
            'status': 'success',
            'message': 'Approval berhasil! Dokumen telah disetujui sepenuhnya.'
        })

    user_profile = getattr(request.user, 'userprofile', None)
    atasan_profile = user_profile.atasan_langsung if user_profile else None

    if not atasan_profile or not atasan_profile.user:
        return JsonResponse({
            'status': 'error', 
            'message': 'Atasan langsung Anda belum diatur di sistem User Profile. Silakan hubungi Administrator.'
        }, status=400, safe=False)

    now = timezone.now()

    # 2. JIKA USER BIASA MELAKUKAN SUBMIT DARI DRAFT KE WAITING
    # Update status khusus foto 4 sisi (ini juga dipantau signals.py untuk kirim email)
    obj.foto_4_sisi_status = 'WAITING'
    obj.foto_4_sisi_submitted_at = now
    obj.foto_4_sisi_submitted_by = request.user
    obj.foto_4_sisi_approver = atasan_profile.user  
    
    # Update status global/utama agar tabel halaman utama langsung berubah menjadi "Menunggu Approval Atasan"
    obj.status_approval = 'WAITING'
    obj.submitted_at = now
    obj.submitted_by = request.user
    obj.current_approver = atasan_profile.user  # Menyimpan nama atasan di kolom approver tabel

    obj.updated_by = request.user
    
    # Panggil save() -> Otomatis memicu post_save signal untuk kirim email & memperbarui database
    obj.save() 

    nama_atasan = atasan_profile.user.get_full_name() or atasan_profile.user.username
    jabatan_atasan = atasan_profile.jabatan_nama_resmi or atasan_profile.get_jabatan_level_display()

    return JsonResponse({
        'status': 'success',
        'message': f'Dokumen berhasil disubmit dan diteruskan ke atasan: {nama_atasan} ({jabatan_atasan}).'
    })

@staff_member_required
@require_POST
def api_delete_foto_4_sisi(request, cn_sap):
    try:
        prep_obj = AssetEquipmentPrepareDisposed.objects.filter(asset__CN_SAP=cn_sap).first()
        if not prep_obj:
            prep_obj = AssetEquipmentPrepareDisposed.objects.filter(pk=cn_sap).first()
            
        if not prep_obj:
            return JsonResponse({'status': 'error', 'message': 'Data tidak ditemukan.'}, status=404)

        # Tandai bahwa ini adalah perintah hapus paksa untuk mengosongkan foto
        prep_obj._force_clear_photos = True

        # Kosongkan field 4 foto terpisah secara eksplisit
        for field in prep_obj.FOTO_TERPISAH_FIELDS:
            setattr(prep_obj, field, None)
        
        prep_obj.foto_4_sisi = None
        prep_obj.foto_4_sisi_uploaded_at = None
        prep_obj.foto_4_sisi_uploaded_by = None

        # ⬅️ TAMBAHKAN INI AGAR BERSIH TOTAL SAAT DIRESET KE DRAFT
        prep_obj.submitted_at = None
        prep_obj.approved_at = None
        prep_obj.rejected_at = None

        # ── 🔄 RESET STATUS APPROVAL KEMBALI KE DRAFT / BELUM DISUBMIT ──
        # Sesuai permintaan: baik dari posisi Waiting maupun Rejected, jika didelete jadi Draft
        prep_obj.status_approval = 'DRAFT'  # Ubah ke '' atau 'DRAFT' tergantung skema database Anda

        # Simpan perubahan (method save() di model akan mengeksekusi penghapusan fisik & merubah kondisi)
        prep_obj.save()

        return JsonResponse({'status': 'success', 'message': 'Foto berhasil dihapus dan status direset ke Prog.'})
    
    except Exception as e:
        return JsonResponse({'status': 'error', 'message': str(e)}, status=500)


@login_required
@require_POST
def reject_approval_disposed(request, cn_sap):
    
    cn_sap = request.POST.get('cn_sap', '').strip()
    alasan = request.POST.get('alasan', '').strip()
    
    if not cn_sap:
        return JsonResponse({'status': 'error', 'message': 'CN_SAP tidak ditemukan.'}, status=400)
    
    if not alasan:
        return JsonResponse({'status': 'error', 'message': 'Alasan penolakan wajib diisi.'}, status=400)

    obj = AssetEquipmentPrepareDisposed.objects.filter(asset__CN_SAP__iexact=cn_sap).first()
    if not obj:
        return JsonResponse({'status': 'error', 'message': 'Data unit tidak ditemukan.'}, status=404)

    # Pastikan yang melakukan reject adalah current_approver yang berhak
    if obj.status_approval == 'WAITING' and obj.current_approver == request.user:
        obj.status_approval = 'REJECTED'
        obj.rejected_at = timezone.now()      # ⬅️ TAMBAHKAN INI
        obj.rejected_by = request.user
        obj.current_approver = None  # Lepas tanggungan approver
        
        # ── 📌 LETAKKAN KODE CATATAN REJECT DI SINI ──
        if hasattr(obj, 'catatan_reject'):
            obj.catatan_reject = alasan
            
        obj.updated_by = request.user
        obj.save()
        
        return JsonResponse({
            'status': 'success',
            'message': 'Dokumen telah ditolak dan dikembalikan ke pembuat untuk direvisi.'
        })

    return JsonResponse({
        'status': 'error',
        'message': 'Anda tidak memiliki hak atau dokumen tidak dalam status menunggu approval.'
    }, status=403)

@login_required
def detail_foto_disposed_api(request, cn_sap):
    try:
        obj = AssetEquipmentPrepareDisposed.objects.filter(asset__CN_SAP__iexact=cn_sap).first()
        if not obj:
            return JsonResponse({'status': 'error', 'message': 'Data tidak ditemukan.'}, status=404)

        asset_rel = getattr(obj, 'asset', None)
        
        # Ambil nilai dengan pengecekan berbagai variasi penamaan field
        cn_ellipse_val = (
            getattr(asset_rel, 'CN_ELLIPSE', None) or 
            getattr(asset_rel, 'cn_ellipse', None) or 
            getattr(obj, 'CN_ELLIPSE', None) or 
            getattr(obj, 'cn_ellipse', '-')
        )
        egi_val = (
            getattr(asset_rel, 'EGI', None) or 
            getattr(asset_rel, 'egi', None) or 
            getattr(obj, 'EGI', None) or 
            getattr(obj, 'egi', '-')
        )
        sn_val = (
            getattr(asset_rel, 'SN', None) or 
            getattr(asset_rel, 'sn', None) or 
            getattr(obj, 'SN', None) or 
            getattr(obj, 'sn', '-')
        )

        data = {
            'status': 'success',
            'cn_sap': cn_sap,
            'cn_ellipse': cn_ellipse_val,
            'sn': sn_val,
            'egi': egi_val,
            'tampak_depan': obj.tampak_depan.url if obj.tampak_depan and hasattr(obj.tampak_depan, 'url') else '',
            'tampak_belakang': obj.tampak_belakang.url if obj.tampak_belakang and hasattr(obj.tampak_belakang, 'url') else '',
            'tampak_samping_kanan': obj.tampak_samping_kanan.url if obj.tampak_samping_kanan and hasattr(obj.tampak_samping_kanan, 'url') else '',
            'tampak_samping_kiri': obj.tampak_samping_kiri.url if obj.tampak_samping_kiri and hasattr(obj.tampak_samping_kiri, 'url') else '',
        }
        return JsonResponse(data)
    except Exception as e:
        return JsonResponse({'status': 'error', 'message': str(e)}, status=500)



#=================================================================================
#=========== ENDPOINT UNTUK INSPEKSI UNIT ========================================
#=================================================================================

import json
import os
from django.http import JsonResponse, HttpResponse, Http404
from django.shortcuts import get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib.admin.views.decorators import staff_member_required
from django.views.decorators.http import require_POST, require_GET
from django.utils import timezone
from .models import AssetEquipmentPrepareDisposed
from data.models import InspectionTemplateItem
from .utils_ocr import generate_pdf_inspeksi_unit_file


def _get_prepare_obj(cn_sap):
    """Helper ambil AssetEquipmentPrepareDisposed berdasarkan CN_SAP."""
    return AssetEquipmentPrepareDisposed.objects.filter(
        asset__CN_SAP=cn_sap
    ).first()


@login_required
@require_GET
def api_get_inspection_items(request, cn_sap):
    """
    Mengambil data unit info dan daftar item check sheet berdasarkan EGI / tipe equipment.
    """
    try:
        prep_unit = get_object_or_404(AssetEquipmentPrepareDisposed, asset__CN_SAP=cn_sap)
        
        unit_info = {
            'type': prep_unit.TYPE or '-',
            'cn_sap': prep_unit.asset.CN_SAP if prep_unit.asset else '-',
            'egi': prep_unit.EGI or '-',
            'sn': prep_unit.SN or '-',
            'hm_smr': str(prep_unit.HM_SMR or '-'),
            'location': prep_unit.LOCATION or '-'
        }

        templates = InspectionTemplateItem.objects.filter(TYPE=prep_unit.TYPE)
        
        items_data = []
        for t in templates:
            items_data.append({
                'id': t.id,
                'item_group': getattr(t, 'ITEM_GROUP', '-'), 
                'item_name': getattr(t, 'ITEM_NAME', '-'),   
                'qty': getattr(t, 'QTY', '1')                
            })

        return JsonResponse({
            'status': 'success',
            'unit_info': unit_info,
            'items': items_data
        })
    except Exception as e:
        print(f"[DEBUG API INSPECTION ERROR] {str(e)}")
        return JsonResponse({'status': 'error', 'message': str(e)}, status=500)


@login_required
@require_POST
def api_save_inspection_items(request, cn_sap):
    """
    Menyimpan hasil checklist/inspeksi item unit dan memastikan statusnya DRAFT.
    """
    try:
        data = json.loads(request.body)
        inspections = data.get('inspections', [])

        prep_unit = get_object_or_404(AssetEquipmentPrepareDisposed, asset__CN_SAP=cn_sap)

        prep_unit.inspeksi_unit_uploaded_at = timezone.now()
        prep_unit.inspeksi_unit_uploaded_by = request.user
        
        # PASTIKAN STATUS KEMBALI KE DRAFT JIKA MASIH REJECTED ATAU BELUM ADA STATUS
        if prep_unit.inspeksi_status in ['REJECTED', ''] or prep_unit.inspeksi_status is None:
            prep_unit.inspeksi_status = 'DRAFT'

        prep_unit._active_form = 'inspeksi_unit'
        prep_unit.save()

        return JsonResponse({
            'status': 'success',
            'message': 'Data inspeksi unit berhasil disimpan sebagai Draft.'
        })
    except Exception as e:
        return JsonResponse({'status': 'error', 'message': str(e)}, status=500)


@login_required
@require_GET
def download_pdf_inspeksi_unit(request, cn_sap):
    """
    Handler untuk Download PDF Laporan Check Sheet Inspeksi Unit menggunakan ReportLab dari utils_ocr.
    """
    prep_unit = get_object_or_404(AssetEquipmentPrepareDisposed, asset__CN_SAP=cn_sap)

    try:
        pdf_path = generate_pdf_inspeksi_unit_file(prep_unit)
        
        if not pdf_path or not os.path.exists(pdf_path):
            raise Http404("Gagal menghasilkan file PDF laporan inspeksi.")

        with open(pdf_path, 'rb') as pdf_file:
            response = HttpResponse(pdf_file.read(), content_type='application/pdf')
            safe_cn = str(cn_sap).replace('/', '_')
            response['Content-Disposition'] = f'attachment; filename="Checksheet_Inspeksi_{safe_cn}.pdf"'
            
            return response
    except Exception as e:
        return HttpResponse(f"Terjadi kesalahan saat memproses PDF: {str(e)}", status=500)


@staff_member_required
@require_POST
def api_delete_inspection_items(request, cn_sap):
    try:
        asset_unit = AssetEquipmentPrepareDisposed.objects.filter(pk=cn_sap).first()
        
        if not asset_unit:
            return JsonResponse({'status': 'error', 'message': 'Data unit prepare disposed tidak ditemukan.'}, status=404)
            
        if asset_unit.inspeksi_status == 'APPROVED' and not request.user.is_superuser:
            return JsonResponse({'status': 'error', 'message': 'Form inspeksi yang sudah disetujui (Approved) tidak dapat dihapus.'}, status=400)

        if asset_unit.inspeksi_unit:
            if hasattr(asset_unit.inspeksi_unit, 'path') and os.path.exists(asset_unit.inspeksi_unit.path):
                try:
                    os.remove(asset_unit.inspeksi_unit.path)
                except Exception:
                    pass

        asset_unit.inspeksi_unit = None
        asset_unit.inspeksi_unit_uploaded_at = None
        asset_unit.inspeksi_unit_uploaded_by = None
        
        asset_unit.inspeksi_status = 'DRAFT'
        asset_unit.inspeksi_submitted_at = None
        asset_unit.inspeksi_submitted_by = None
        asset_unit.inspeksi_approver = None
        asset_unit.inspeksi_catatan_reject = None
        
        asset_unit.save()

        return JsonResponse({
            'status': 'success',
            'message': 'Data inspeksi unit berhasil dihapus dan status direset ke Draft.'
        })
        
    except Exception as e:
        return JsonResponse({'status': 'error', 'message': str(e)}, status=500)



# ── INSPEKSI UNIT (Wajib aktif dan dipakai oleh rute fetch JS) ──

@staff_member_required
@require_POST
def submit_inspeksi_unit(request, cn_sap):
    obj = _get_prepare_obj(cn_sap)
    if not obj:
        return JsonResponse({'status': 'error', 'message': f'Unit {cn_sap} tidak ditemukan.'}, status=404)

    # Validasi apakah check sheet sudah diisi/disimpan sebelumnya
    if not obj.inspeksi_unit_uploaded_at:
        return JsonResponse({'status': 'error', 'message': 'Check sheet inspeksi belum diisi atau disimpan!'}, status=400)

    if obj.inspeksi_status == 'WAITING':
        return JsonResponse({'status': 'error', 'message': 'Form sudah dalam status WAITING.'}, status=400)

    obj.inspeksi_status         = 'WAITING'
    obj.inspeksi_submitted_at = timezone.now()
    obj.inspeksi_submitted_by = request.user
    obj.inspeksi_approver       = obj.current_approver

    obj.save(update_fields=[
        'inspeksi_status',
        'inspeksi_submitted_at',
        'inspeksi_submitted_by',
        'inspeksi_approver',
    ])
    return JsonResponse({'status': 'success', 'message': f'Form Inspeksi Unit {cn_sap} berhasil disubmit.'})


@staff_member_required
@require_POST
def approve_inspeksi_unit(request, cn_sap):
    obj = _get_prepare_obj(cn_sap)
    if not obj:
        return JsonResponse({'status': 'error', 'message': f'Unit {cn_sap} tidak ditemukan.'}, status=404)

    if obj.inspeksi_status != 'WAITING':
        return JsonResponse({'status': 'error', 'message': 'Form tidak dalam status WAITING.'}, status=400)

    obj.inspeksi_status      = 'APPROVED'
    obj.inspeksi_approved_at = timezone.now()
    obj.inspeksi_approved_by = request.user

    obj.save(update_fields=[
        'inspeksi_status',
        'inspeksi_approved_at',
        'inspeksi_approved_by',
    ])
    return JsonResponse({'status': 'success', 'message': f'Form Inspeksi Unit {cn_sap} berhasil diapprove.'})


@staff_member_required
@require_POST
def reject_inspeksi_unit(request, cn_sap):
    obj = _get_prepare_obj(cn_sap)
    if not obj:
        return JsonResponse({'status': 'error', 'message': f'Unit {cn_sap} tidak ditemukan.'}, status=404)

    alasan = request.POST.get('alasan', '').strip()
    if not alasan:
        return JsonResponse({'status': 'error', 'message': 'Alasan penolakan wajib diisi.'}, status=400)

    obj.inspeksi_status         = 'REJECTED'
    obj.inspeksi_rejected_at    = timezone.now()
    obj.inspeksi_rejected_by    = request.user
    obj.inspeksi_catatan_reject = alasan

    obj.save(update_fields=[
        'inspeksi_status',
        'inspeksi_rejected_at',
        'inspeksi_rejected_by',
        'inspeksi_catatan_reject',
    ])
    return JsonResponse({'status': 'success', 'message': f'Form Inspeksi Unit {cn_sap} ditolak.'})


#==================================================================================================
#=========== DEF UNTUK APPROVAL ACTION VIA EMAIL ==================================================
#==================================================================================================

from django.shortcuts import get_object_or_404, render
from django.utils import timezone
from django.core.signing import TimestampSigner, SignatureExpired, BadSignature
from .models import AssetEquipmentPrepareDisposed

signer = TimestampSigner()

def email_approval_action(request, cn_sap, action):
    """
    Handler untuk proses Approve/Reject via link email dengan batas waktu 3 hari.
    """
    token = request.GET.get('token', '')
    
    try:
        original_data = signer.unsign(token, max_age=3 * 86400)
    except SignatureExpired:
        return render(request, 'admin/asset/partials/approval_response.html', {
            'success': False,
            'message': 'Masa berlaku link email ini telah habis (lebih dari 3 hari). Silakan login ke sistem untuk melakukan approval secara manual.'
        })
    except BadSignature:
        return render(request, 'admin/asset/partials/approval_response.html', {
            'success': False,
            'message': 'Token keamanan link tidak valid atau telah dimodifikasi.'
        })
    
    # Ambil data objek berdasarkan CN_SAP
    obj = get_object_or_404(AssetEquipmentPrepareDisposed, asset__CN_SAP=cn_sap)
    
    target_field = None
    current_status = None
    
    if getattr(obj, 'inspeksi_status', None) == 'WAITING':
        target_field = 'inspeksi'
        current_status = 'WAITING'
    elif getattr(obj, 'foto_4_sisi_status', None) == 'WAITING':
        target_field = 'foto_4_sisi'
        current_status = 'WAITING'
    else:
        current_status = getattr(obj, 'inspeksi_status', None) or getattr(obj, 'foto_4_sisi_status', None) or 'DRAFT'

    if not target_field:
        return render(request, 'admin/asset/partials/approval_response.html', {
            'success': False,
            'message': f'Dokumen ini sudah diproses sebelumnya dengan status: {current_status}.'
        })
    
    # Eksekusi aksi berdasarkan target field yang sedang WAITING
    if target_field == 'inspeksi':
        if action == 'approve':
            obj.inspeksi_status = 'APPROVED'
            obj.inspeksi_approved_at = timezone.now()
            
            # Sinkronisasi agar terbaca oleh utils_ocr.py lama (jika menggunakan skema global)
            obj.status_approval = 'APPROVED'
            obj.approved_at = timezone.now()
            
            message = f'Check Sheet Inspeksi Unit dengan CN SAP: {cn_sap} berhasil DISETUJUI.'
        elif action == 'reject':
            obj.inspeksi_status = 'REJECTED'
            obj.status_approval = 'REJECTED'
            message = f'Check Sheet Inspeksi Unit dengan CN SAP: {cn_sap} telah DITOLAK.'
        else:
            message = 'Aksi tidak dikenali.'
            
    elif target_field == 'foto_4_sisi':
        if action == 'approve':
            obj.foto_4_sisi_status = 'APPROVED'
            obj.foto_4_sisi_approved_at = timezone.now()
            
            ### PERBAIKAN DI SINI: Sinkronisasi ke status global agar tabel utama terupdate
            obj.status_approval = 'APPROVED'
            obj.approved_at = timezone.now()
            ###
            
            message = f'Form Foto 4 Sisi dengan CN SAP: {cn_sap} berhasil DISETUJUI.'
        elif action == 'reject':
            obj.foto_4_sisi_status = 'REJECTED'
            
            ### PERBAIKAN DI SINI: Sinkronisasi ke status global jika ditolak
            obj.status_approval = 'REJECTED'
            ###
            
            message = f'Form Foto 4 Sisi dengan CN SAP: {cn_sap} telah DITOLAK.'
        else:
            message = 'Aksi tidak dikenali.'

    obj.save()

    # ==========================================
    # TRIGGER WEBSOCKET KE BROWSER
    # ==========================================
    # Tentukan status akhir dan warna badge berdasarkan aksi
    if action == 'approve':
        new_status = 'APPROVED'
        status_text = 'APPROVED'
        badge_bg = '#d1e7dd'   # Hijau muda (contoh)
        badge_color = '#0f5132' # Hijau tua
    elif action == 'reject':
        new_status = 'REJECTED'
        status_text = 'REJECTED'
        badge_bg = '#f8d7da'   # Merah muda (contoh)
        badge_color = '#842029' # Merah tua
    else:
        new_status = 'UNKNOWN'
        status_text = 'UNKNOWN'
        badge_bg = '#e2e3e5'
        badge_color = '#383d41'

    # Panggil fungsi trigger WebSocket yang sudah Anda buat di bawah
    trigger_status_update_socket(cn_sap, new_status, status_text, badge_bg, badge_color)
    # ==========================================

    return render(request, 'admin/asset/partials/approval_response.html', {
        'success': True,
        'message': message,
        'cn_sap': cn_sap,
        'action': action
    })

from django.http import JsonResponse

def check_approval_status(request, cn_sap):
    obj = get_object_or_404(AssetEquipmentPrepareDisposed, asset__CN_SAP=cn_sap)
    return JsonResponse({
        'inspeksi_status': obj.inspeksi_status,
        'foto_4_sisi_status': obj.foto_4_sisi_status,
    })

#===========================================================================
#=== Trigger WebSocket saat Approval dari Email / Sistem ===================
#===========================================================================

from channels.layers import get_channel_layer
from asgiref.sync import async_to_sync

def trigger_status_update_socket(cn_sap, status, status_text, badge_bg, badge_color):
    channel_layer = get_channel_layer()
    async_to_sync(channel_layer.group_send)(
        f'status_{cn_sap}',
        {
            'type': 'send_status_update',
            'status': status,
            'status_text': status_text,
            'badge_bg': badge_bg,
            'badge_color': badge_color,
        }
    )