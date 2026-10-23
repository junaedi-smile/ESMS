from django.contrib.auth.models import User, Group
from import_export import resources, fields
from django.contrib import admin
from django.db import models
from django.contrib.admin import AdminSite
from datetime import datetime as dt, date
from import_export.admin import ImportExportModelAdmin
from django.utils.html import format_html
from django.urls import reverse
from django.utils.safestring import mark_safe
from import_export.formats.base_formats import CSV, XLS, XLSX, JSON
from django.contrib.admin import SimpleListFilter
from import_export.widgets import DateWidget, IntegerWidget, CharWidget, DecimalWidget, FloatWidget, ForeignKeyWidget
from import_export.fields import Field
from django.db.models import Count, Case, When,IntegerField# Pastikan Count & Q sudah terimpor!
from django.db.models.functions import ExtractMonth, ExtractYear # TANDAI: Pastikan ExtractMonth & ExtractYear sudah diimpor
import json
import datetime
from decimal import Decimal, InvalidOperation
from django.contrib.auth.decorators import login_required
from django.urls import path
from django.contrib.contenttypes.models import ContentType
from django.shortcuts import render, redirect, get_object_or_404
from django.db.models.functions import ExtractMonth, ExtractYear
from django.template.loader import select_template
from xhtml2pdf import pisa
from django.http import HttpResponse
from django.template.loader import render_to_string
from django.utils import timezone
from django.db.models import Count, Q
from django.contrib import messages
from .utils_ocr import verifikasi_dokumen_rca

from .models import (
    AssetMonthlyStatus, 
    AssetEquipment, 
    AssetEquipmentDisposed,   
    AssetEquipmentStandby,
    AssetEquipmentBreakdown,
    AssetEquipmentOperate,
    AssetMasterMonthlyStatus,
    AssetFinalMonthlyStatus,    
    )
from .models import AssetEquipmentPrepareDisposed
# Import model dari semua app
from data.models import MPS
from form.models import (
    FormPengajuanEquipmentDisposed,
    FormLampiranCapex,
    FormPengajuanDisposedSite,
    FormRepairCostAnalisis,   
    FormFotoKonditionUnit,
    ApprovalStep,
    ApprovalLog,
)
from form.forms import (
    PengajuanEquipmentDisposedForm,
    LampiranCapexForm,
    PengajuanDisposedSiteForm,
    RepairCostAnalisisForm, 
    FotoKonditionUnitForm,
)


# ---------------------------
# Membuat instance custom Admin Site
# ---------------------------
class InsideAdminSite(AdminSite):
    site_header = 'INSIDE Admin'
    site_title = 'INSIDE Admin Portal'
    index_title = 'Selamat Datang di INSIDE Dashboard'

    def index(self, request, extra_context=None):
        extra_context = extra_context or {}

        # ============================================================
        # 🌟 1. DETEKSI ROLE USER LOGIN (LOCATION & SECTION)
        # ============================================================
        user_lokasi = ""
        user_section = ""
        is_restricted_user = False

        if not request.user.is_superuser and hasattr(request.user, 'userprofile'):
            user_lokasi = request.user.userprofile.lokasi or ""
            user_section = request.user.userprofile.section or ""
            # ✅ FIX: User dianggap restricted HANYA jika lokasi terisi
            if user_lokasi:
                is_restricted_user = True

        extra_context.update({
            'user_lokasi': user_lokasi,
            'user_section': user_section,
            'is_restricted_user': is_restricted_user,
            # ✅ FIX: is_admin_view harus False jika is_restricted_user True
            'is_admin_view': request.user.is_superuser or (request.user.is_staff and not is_restricted_user)
        })

        # ============================================================
    # 🌟 2. KONFIGURASI TAMPILAN DASHBOARD BERDASARKAN ROLE
    # ============================================================
    
    # Default: semua section TAMPIL (untuk superuser/admin)
        dashboard_sections = {
            'show_summary_cards':    True,  # Card total/operate/breakdown/dll
            'show_pie_chart':        True,  # Chart persentase status equipment
            'show_bar_chart':        True,  # Chart perbandingan bulanan
            'show_conmon':           True,  # Tabel komponen healthy unit
            'show_direct_cost':      True,  # Tabel & grafik direct cost
            'show_foto_unit':        True,  # Box foto unit
            'show_monitoring_docs':  True,  # Tabel monitoring digital approval
            'show_disposed_table':   True,  # Tabel sub-location & EGI disposed
        }

        # ── Aturan per LOCATION ──────────────────────────────────────
        if is_restricted_user:
            lokasi_upper  = user_lokasi.upper()
            section_upper = user_section.upper()

            # -----------------------------------------------------------
            # LOCATION: ADMO
            # -----------------------------------------------------------
            if 'ADMO' in lokasi_upper:

                if 'MINING-PHW' in section_upper or 'MINING - PHW' in section_upper:
                    dashboard_sections.update({
                        'show_conmon':        False,  # Tidak perlu ConMon
                        'show_direct_cost':   False,  # Tidak perlu Direct Cost
                    })

                elif 'MINING-PSU' in section_upper or 'MINING - PSU' in section_upper:
                    dashboard_sections.update({
                        'show_conmon':        False,
                        'show_direct_cost':   False,
                    })

                elif 'PLANT' in section_upper:
                    # Section PLANT di ADMO: butuh ConMon tapi tidak butuh Direct Cost
                    dashboard_sections.update({
                        'show_conmon':       True,
                        'show_direct_cost':  False,
                    })

            # -----------------------------------------------------------
            # LOCATION: JAHO (contoh lokasi lain)
            # -----------------------------------------------------------
            elif 'JAHO' in lokasi_upper:
                dashboard_sections.update({
                    'show_conmon':       True,
                    'show_direct_cost':  True,
                    'show_disposed_table': False,  # JAHO tidak perlu tabel disposed
                })

            # -----------------------------------------------------------
            # LOCATION: Lainnya — tampilan minimal
            # -----------------------------------------------------------
            else:
                dashboard_sections.update({
                    'show_conmon':        False,
                    'show_direct_cost':   False,
                    'show_disposed_table': False,
                })

        extra_context['dashboard_sections'] = dashboard_sections

        # ============================================================
        # 🌟 3. HELPER FILTER TERPUSAT — GUNAKAN DI SEMUA QUERYSET
        # ============================================================
        # ✅ TAMBAHAN: Satu fungsi terpusat agar konsisten di semua query
        def apply_role_filter(qs, location_field='LOCATION', section_field='SECTION'):
            if is_restricted_user:
                filter_kwargs = {f'{location_field}__iexact': user_lokasi}
                if user_section:
                    filter_kwargs[f'{section_field}__iexact'] = user_section
                return qs.filter(**filter_kwargs)
            return qs

        # ============================================================
        # 🌟 4. QUERY UTAMA ASSET
        # ============================================================
        assets = apply_role_filter(AssetEquipment.objects.all())

        extra_context.update({
            'total_assets': assets.count(),
            'operate':   assets.filter(EQUIPMENT_CONDITION__iexact='OPERATE').count(),
            'breakdown': assets.filter(EQUIPMENT_CONDITION__iexact='BREAKDOWN').count(),
            'standby':   assets.filter(EQUIPMENT_CONDITION__iexact='STANDBY').count(),
            'disposed':  assets.filter(EQUIPMENT_CONDITION__iexact='DISPOSED').count(),
            'rfu':       assets.filter(BP__iexact='RFU').count(),
            'asset_list': assets[:10],
        })

        # ============================================================
        # 🌟 5. DISPOSED BY LOCATION
        # ============================================================
        disposed_location_qs = apply_role_filter(
            AssetEquipment.objects.filter(EQUIPMENT_CONDITION__iexact='DISPOSED')
        )
        disposed_by_location_data = list(
            disposed_location_qs.values('LOCATION')
            .annotate(count=Count('LOCATION'))
            .order_by('LOCATION')
        )
        extra_context['disposed_by_location_data'] = disposed_by_location_data

        # ============================================================
        # 🌟 6. BAR CHART BULANAN
        # ============================================================
        monthly_status_qs = apply_role_filter(AssetMonthlyStatus.objects.all())

        monthly_data_aggregated = (
            monthly_status_qs
            .annotate(
                month_number=ExtractMonth('MONTH'),
                year_number=ExtractYear('MONTH')
            )
            .values('year_number', 'month_number')
            .annotate(
                operate_count=Count(Case(When(EQUIPMENT_CONDITION='OPERATE', then=1), default=None, output_field=IntegerField())),
                breakdown_count=Count(Case(When(EQUIPMENT_CONDITION='BREAKDOWN', then=1), default=None, output_field=IntegerField())),
                standby_count=Count(Case(When(EQUIPMENT_CONDITION='STANDBY', then=1), default=None, output_field=IntegerField())),
                disposed_count=Count(Case(When(EQUIPMENT_CONDITION='DISPOSED', then=1), default=None, output_field=IntegerField())),
                rfu_count=Count(Case(When(BP='RFU', then=1), default=None, output_field=IntegerField())),
            )
            .order_by('year_number', 'month_number')
        )

        labels, operate_data, breakdown_data, standby_data, disposed_data, rfu_data = [], [], [], [], [], []
        month_names = {
            1:'Jan', 2:'Feb', 3:'Mar', 4:'Apr', 5:'Mei', 6:'Jun',
            7:'Jul', 8:'Agu', 9:'Sep', 10:'Okt', 11:'Nov', 12:'Des'
        }
        for data in monthly_data_aggregated:
            labels.append(f"{month_names.get(data['month_number'], '')} {data['year_number']}")
            operate_data.append(data['operate_count'])
            breakdown_data.append(data['breakdown_count'])
            standby_data.append(data['standby_count'])
            disposed_data.append(data['disposed_count'])
            rfu_data.append(data['rfu_count'])

        extra_context.update({
            'bar_chart_labels':         json.dumps(labels),
            'bar_chart_operate_data':   json.dumps(operate_data),
            'bar_chart_breakdown_data': json.dumps(breakdown_data),
            'bar_chart_standby_data':   json.dumps(standby_data),
            'bar_chart_disposed_data':  json.dumps(disposed_data),
            'bar_chart_rfu_data':       json.dumps(rfu_data),
        })

        # ============================================================
        # 🌟 7. SUB-LOCATION & EGI (AssetEquipmentDisposed)
        # ============================================================
        disposed_equipment_qs = apply_role_filter(AssetEquipmentDisposed.objects.all())

        disposed_by_sub_location_data = list(
            disposed_equipment_qs.values('SUB_LOCATION')
            .annotate(count=Count('SUB_LOCATION'))
            .order_by('SUB_LOCATION')
        )
        extra_context['disposed_by_sub_location_data'] = disposed_by_sub_location_data

        disposed_by_egi_data = list(
            disposed_equipment_qs.values('EGI', 'TYPE')
            .annotate(count=Count('EGI'))
            .order_by('EGI', 'TYPE')
        )
        extra_context['disposed_by_egi_data_json'] = json.dumps(disposed_by_egi_data)

        # ============================================================
        # 🌟 8. MONITORING DOKUMEN — TERFILTER BERDASARKAN CN_SAP YANG BERHAK DILIHAT
        # ============================================================
        STATUS_CHOICES = ['DRAFT', 'SUB', 'APR1', 'APR2', 'FIN', 'REJ']
        STATUS_LABELS  = {
            'DRAFT': 'Draft', 'SUB': 'Submitted', 'APR1': 'Approved L1',
            'APR2': 'Approved L2', 'FIN': 'Final', 'REJ': 'Rejected'
        }
        STATUS_COLORS  = {
            'DRAFT': '#888', 'SUB': '#1883ff', 'APR1': '#f57c00',
            'APR2': '#9c27b0', 'FIN': '#28a745', 'REJ': '#dc3545'
        }

        FORM_DEFINITIONS = [
            {'model': FormLampiranCapex, 'label': 'Lampiran Capex', 'url_name': 'form:lampiran_capex_detail', 'icon': '📋'},
            {'model': FormPengajuanEquipmentDisposed, 'label': 'PDE', 'url_name': None, 'icon': '📄'},
            {'model': FormPengajuanDisposedSite, 'label': 'PDS', 'url_name': None, 'icon': '📝'},
            {'model': FormRepairCostAnalisis, 'label': 'RCA', 'url_name': None, 'icon': '🔧'},
            {'model': FormFotoKonditionUnit, 'label': 'Foto Kondisi', 'url_name': None, 'icon': '📷'},
        ]

        # ✅ FIX: CN_SAP yang valid mengikuti assets yang sudah terfilter role
        valid_cn_saps = assets.values_list('CN_SAP', flat=True)

        summary_counts = {s: 0 for s in STATUS_CHOICES}
        total_docs = 0
        all_documents = []

        for form_def in FORM_DEFINITIONS:
            # ✅ FIX: Filter dokumen berdasarkan CN_SAP yang berhak dilihat user
            base_qs = form_def['model'].objects.filter(CN_SAP__in=valid_cn_saps)

            # Superuser/staff lihat semua; user biasa hanya dokumen milik sendiri
            if not (request.user.is_superuser or request.user.is_staff):
                base_qs = base_qs.filter(diajukan_oleh=request.user)

            # Hitung summary
            counts = base_qs.values('status').annotate(count=Count('id'))
            for row in counts:
                s = row['status']
                if s in summary_counts:
                    summary_counts[s] += row['count']
                    total_docs += row['count']

            # Ambil detail dokumen
            doc_qs = base_qs.select_related('diajukan_oleh').order_by('-updated_at')
            for doc in doc_qs:
                elapsed = '-'
                if doc.submitted_at:
                    delta = timezone.now() - doc.submitted_at
                    elapsed = f"{delta.days}h {delta.seconds // 3600}j" if delta.days > 0 else f"{delta.seconds // 3600}j"

                opt = doc._meta
                view_url = f"/admin/{opt.app_label}/{opt.model_name}/{doc.pk}/change/"

                all_documents.append({
                    'pk':           doc.pk,
                    'cn_sap':       getattr(doc, 'CN_SAP', '-'),
                    'form_type':    form_def['label'],
                    'form_icon':    form_def['icon'],
                    'status':       doc.status,
                    'status_label': STATUS_LABELS.get(doc.status, doc.status),
                    'status_color': STATUS_COLORS.get(doc.status, '#888'),
                    'diajukan_oleh': (doc.diajukan_oleh.get_full_name() or doc.diajukan_oleh.username) if doc.diajukan_oleh else '-',
                    'submitted_at': doc.submitted_at.strftime('%d/%m/%Y %H:%M') if doc.submitted_at else '-',
                    'updated_at':   doc.updated_at.strftime('%d/%m/%Y %H:%M'),
                    'elapsed':      elapsed,
                    'view_url':     view_url,
                })

        summary_cards = [
            {'status': s, 'label': STATUS_LABELS[s], 'count': summary_counts[s], 'color': STATUS_COLORS[s]}
            for s in STATUS_CHOICES
        ]

        all_documents.sort(key=lambda x: x['updated_at'], reverse=True)

        extra_context.update({
            'summary_cards':             summary_cards,
            'monitoring_documents_json': json.dumps(all_documents),
            'monitoring_total':          len(all_documents),
        })

        return super().index(request, extra_context=extra_context)
 
        
    

    def get_urls(self):
            urls = super().get_urls()
            custom_urls = [
                # URL Form Pengajuan
                path('form/pengajuan-disposed/', self.admin_view(self.form_pengajuan_disposed_view), name='form_pengajuan_disposed'),
                path('form/lampiran-capex/', self.admin_view(self.form_lampiran_capex_view), name='form_lampiran_capex'),
                path('form/pengajuan-disposed-site/', self.admin_view(self.form_pengajuan_disposed_site_view), name='form_pengajuan_disposed_site'),                
                path('form/periodical-inspection/', self.admin_view(self.form_periodical_inspection_view), name='form_periodical_inspection'),
                path('form/foto-kondition-unit/', self.admin_view(self.form_foto_kondition_unit_view), name='form_foto_kondition_unit'),               
                # URL Daftar Pengajuan
                path('daftar/pengajuan-disposed/', self.admin_view(self.daftar_pengajuan_disposed), name='daftar_pengajuan_disposed'),
                path('daftar/lampiran-capex/', self.admin_view(self.daftar_lampiran_capex), name='daftar_lampiran_capex'),
                path('daftar/pengajuan-disposed-site/', self.admin_view(self.daftar_pengajuan_disposed_site), name='daftar_pengajuan_disposed_site'),   
                path('daftar/foto-kondition-unit/', self.admin_view(self.daftar_foto_kondition_unit), name='daftar_foto_kondition_unit'),
                # URL Halaman Approval
                path('approval/disposed/<int:form_id>/', self.admin_view(self.approval_equipment_disposed_view), name='approval_equipment_disposed'),
                
                path('', self.admin_view(self.index), name='index'),
            ]
            return custom_urls + urls


    # VIEW UNTUK FORM PENGAJUAN
    @login_required
    def form_pengajuan_disposed_view(self, request):
        if request.method == 'POST':
            form = PengajuanEquipmentDisposedForm(request.POST)
            if form.is_valid():
                pengajuan = form.save(commit=False)
                pengajuan.diajukan_oleh = request.user
                pengajuan.save()
                return redirect('inside_admin:daftar_pengajuan_disposed')
        else:
            form = PengajuanEquipmentDisposedForm()
        
        context = self.each_context(request)
        context['form'] = form
        return render(request, 'form/form_pengajuan_disposed.html', context)
    
    @login_required
    def form_lampiran_capex_view(self, request):
        if request.method == 'POST':
            form = LampiranCapexForm(request.POST)
            if form.is_valid():
                pengajuan = form.save(commit=False)
                pengajuan.diajukan_oleh = request.user
                pengajuan.save()
                return redirect('inside_admin:daftar_lampiran_capex')
        else:
            form = LampiranCapexForm()
        
        context = self.each_context(request)
        context['form'] = form
        return render(request, 'form/form_lampiran_capex.html', context)

    @login_required
    def form_pengajuan_disposed_site_view(self, request):
        if request.method == 'POST':
            form = PengajuanDisposedSiteForm(request.POST)
            if form.is_valid():
                pengajuan = form.save(commit=False)
                pengajuan.diajukan_oleh = request.user
                pengajuan.save()
                return redirect('inside_admin:daftar_pengajuan_disposed_site')
        else:
            form = PengajuanDisposedSiteForm()
        context = self.each_context(request)
        context['form'] = form
        return render(request, 'form/form_pengajuan_disposed_site.html', context)
    
   

    @login_required
    def form_periodical_inspection_view(self, request):
        if request.method == 'POST':
            form = PeriodicalInspectionForm(request.POST)
            if form.is_valid():
                pengajuan = form.save(commit=False)
                pengajuan.diajukan_oleh = request.user
                pengajuan.save()
                return redirect('inside_admin:daftar_periodical_inspection')
        else:
            form = PeriodicalInspectionForm()
        context = self.each_context(request)
        context['form'] = form
        return render(request, 'form/form_periodical_inspection.html', context)

    @login_required
    def form_foto_kondition_unit_view(self, request):
        if request.method == 'POST':
            form = FotoKonditionUnitForm(request.POST, request.FILES) # Tambahkan request.FILES
            if form.is_valid():
                pengajuan = form.save(commit=False)
                pengajuan.diajukan_oleh = request.user
                pengajuan.save()
                return redirect('inside_admin:daftar_foto_kondition_unit')
        else:
            form = FotoKonditionUnitForm()
        context = self.each_context(request)
        context['form'] = form
        return render(request, 'form/form_foto_kondition_unit.html', context)


    # VIEW UNTUK DAFTAR PENGAJUAN
    @login_required
    def daftar_pengajuan_disposed(self, request):
        pengajuan_list = FormPengajuanEquipmentDisposed.objects.filter(diajukan_oleh=request.user).order_by('-created_at')
        context = self.each_context(request)
        context['pengajuan_list'] = pengajuan_list
        return render(request, 'form/daftar_pengajuan_disposed.html', context)
    
    @login_required
    def daftar_lampiran_capex(self, request):
        pengajuan_list = FormLampiranCapex.objects.filter(diajukan_oleh=request.user).order_by('-created_at')
        context = self.each_context(request)
        context['pengajuan_list'] = pengajuan_list
        return render(request, 'form/daftar_lampiran_capex.html', context)

    @login_required
    def daftar_pengajuan_disposed_site(self, request):
        pengajuan_list = FormPengajuanDisposedSite.objects.filter(diajukan_oleh=request.user).order_by('-created_at')
        context = self.each_context(request)
        context['pengajuan_list'] = pengajuan_list
        return render(request, 'form/daftar_pengajuan_disposed_site.html', context)
    
    @login_required
    def daftar_foto_kondition_unit(self, request):
        pengajuan_list = FormFotoKonditionUnit.objects.filter(diajukan_oleh=request.user).order_by('-created_at')
        context = self.each_context(request)
        context['pengajuan_list'] = pengajuan_list
        return render(request, 'form/daftar_foto_kondition_unit.html', context)
        

    # VIEW UNTUK PROSES APPROVAL
    @login_required
    def approval_equipment_disposed_view(self, request, form_id):
        form_pengajuan = get_object_or_404(FormPengajuanEquipmentDisposed, id=form_id)
        
        last_approved_log = ApprovalLog.objects.filter(
            content_type=ContentType.objects.get_for_model(form_pengajuan),
            object_id=form_pengajuan.id,
            disetujui=True
        ).order_by('-langkah__urutan').first()

        if last_approved_log:
            next_urutan = last_approved_log.langkah.urutan + 1
        else:
            next_urutan = 1

        try:
            current_step = ApprovalStep.objects.get(urutan=next_urutan)
        except ApprovalStep.DoesNotExist:
            current_step = None

        is_current_approver = current_step and (request.user == current_step.penanggung_jawab)

        if request.method == 'POST' and is_current_approver:
            if 'approve' in request.POST:
                ApprovalLog.objects.create(
                    form_pengajuan=form_pengajuan,
                    langkah=current_step,
                    disetujui=True,
                    komentar=request.POST.get('komentar')
                )
                
                if not ApprovalStep.objects.filter(urutan=next_urutan + 1).exists():
                    form_pengajuan.status = 'APPROVED'
                form_pengajuan.save()
                
                return redirect('inside_admin:daftar_pengajuan_disposed')

            elif 'reject' in request.POST:
                form_pengajuan.status = 'REJECTED'
                form_pengajuan.save()
                ApprovalLog.objects.create(
                    form_pengajuan=form_pengajuan,
                    langkah=current_step,
                    disetujui=False,
                    komentar=request.POST.get('komentar')
                )
                return redirect('inside_admin:daftar_pengajuan_disposed')

        logs = ApprovalLog.objects.filter(
            content_type=ContentType.objects.get_for_model(form_pengajuan),
            object_id=form_pengajuan.id
        ).order_by('langkah__urutan')
        
        context = self.each_context(request)
        context['form_pengajuan'] = form_pengajuan
        context['logs'] = logs
        context['current_step'] = current_step
        context['is_current_approver'] = is_current_approver
        return render(request, 'form/approval_equipment_disposed.html', context)


# Inisialisasi custom admin site
admin_site = InsideAdminSite(name='inside_admin')

#---Tandai: Awal penambahan untuk membuat bar Charts--#
#--Mengambil data bulanan dari AssetMonthlyStatus

        
#=======================================
#=====class untuk monthly report=======#
#=======================================

class AssetMonthlyStatusResource(resources.ModelResource):
    def clean_HM_DATE(self, value):
        if value is not None and str(value).strip().lower() == "midnight":
            return None
        return value

    def clean_PERSENTASE_SPO(self, value):
        if value is None or str(value).strip() == '' or str(value).strip().lower() == 'none':
            return None
        try:
            clean_value = str(value).replace(',', '.').strip()
            return float(clean_value)
        except ValueError:
            return None

    # --- SAVE INSTANCE ---
    def save_instance(self, instance, *args, dry_run=False, **kwargs):
        if not dry_run:
            instance.save()
        else:
            super().save_instance(instance, *args, dry_run=dry_run, **kwargs)

    # 🌟 PERBAIKAN IMPORT-EXPORT ROLE: Gunakan get_import_queryset atau filter manual di rilis data
    # (Method get_queryset yang salah di sini sudah saya hapus)

    No_Asset = fields.Field(column_name='Nomor Asset', attribute='No_Asset', widget=CharWidget())
    CN_SAP = fields.Field(column_name='Code Number', attribute='CN_SAP', widget=CharWidget())
    CN_ELLIPSE = fields.Field(column_name='Code Number Ellipse', attribute='CN_ELLIPSE', widget=CharWidget())
    EGI = fields.Field(column_name='EGI', attribute='EGI', widget=CharWidget())
    TYPE = fields.Field(column_name='Type', attribute='TYPE', widget=CharWidget())
    GROUP = fields.Field(column_name='Class', attribute='GROUP', widget=CharWidget())
    CLASS_WEIGHT = fields.Field(column_name='CN Class', attribute='CLASS_WEIGHT', widget=CharWidget())
    OWNERSHIP = fields.Field(column_name='Ownership', attribute='OWNERSHIP', widget=CharWidget())
    SECTION = fields.Field(column_name='PIC', attribute='SECTION', widget=CharWidget())
    LOCATION = fields.Field(column_name='Location', attribute='LOCATION', widget=CharWidget())
    SUB_SITE = fields.Field(column_name='Sub Site', attribute='SUB_SITE', widget=CharWidget())
    SUB_LOCATION = fields.Field(column_name='Sub Location', attribute='SUB_LOCATION', widget=CharWidget())
    BRAND = fields.Field(column_name='Brand', attribute='BRAND', widget=CharWidget())
    SN = fields.Field(column_name='Serial Number', attribute='SN', widget=CharWidget())
    HM_SMR = fields.Field(column_name='Hour Meter', attribute='HM_SMR', widget=CharWidget())
    HM_DATE = fields.Field(column_name='Hour Meter Date', attribute='HM_DATE', widget=DateWidget(format='%Y-%m-%d'))
    SPO_EQUIPMENT = fields.Field(column_name='SPO Equipment', attribute='SPO_EQUIPMENT', widget=IntegerWidget())
    PERSENTASE_SPO = fields.Field(column_name='% SPO Equipment', attribute='PERSENTASE_SPO', widget=FloatWidget()) 
    EQUIPMENT_CONDITION = fields.Field(column_name='Equipment Condition', attribute='EQUIPMENT_CONDITION', widget=CharWidget())
    STATUS_EQUIPMENT = fields.Field(column_name='Status Equipment', attribute='STATUS_EQUIPMENT', widget=CharWidget())
    STATUS_EQUIPMENT_DISPOSED = fields.Field(column_name='Status Equipment Disposed', attribute='STATUS_EQUIPMENT_DISPOSED', widget=CharWidget())
    NBV = fields.Field(column_name='NBV', attribute='NBV', widget=DecimalWidget())
    WEIGHT = fields.Field(column_name='WEIGHT', attribute='WEIGHT', widget=DecimalWidget())
    REFERENSI_NO_PDE = fields.Field(column_name='Referensi No PDE', attribute='REFERENSI_NO_PDE', widget=CharWidget())
    YEAR = fields.Field(column_name='Year', attribute='YEAR', widget=IntegerWidget())
    MONTH = fields.Field(column_name='Month', attribute='MONTH', widget=DateWidget(format='%Y-%m-%d'))
    BP = fields.Field(column_name='BP', attribute='BP', widget=CharWidget())

    class Meta:
        model = AssetMonthlyStatus
        import_id_fields = ['CN_SAP', 'MONTH', 'YEAR']
        fields = (
            'No_Asset', 'CN_SAP', 'CN_ELLIPSE', 'EGI', 'TYPE', 'GROUP', 'CLASS_WEIGHT',
            'OWNERSHIP', 'SECTION', 'LOCATION', 'SUB_SITE', 'SUB_LOCATION', 'BRAND',
            'SN', 'HM_SMR', 'HM_DATE', 'SPO_EQUIPMENT', 'PERSENTASE_SPO',
            'EQUIPMENT_CONDITION', 'STATUS_EQUIPMENT', 'STATUS_EQUIPMENT_DISPOSED', 'NBV', 'WEIGHT',
            'REFERENSI_NO_PDE', 'YEAR', 'MONTH', 'BP'
        )
        export_order = fields
        skip_unchanged = False  
        report_skipped = True


# --- FILTER KELAS (Month & Year) Tetap Sama ---
class MonthFilter(SimpleListFilter):
    title = 'Bulan Laporan'
    parameter_name = 'report_month'
    def lookups(self, request, model_admin):
        months = AssetMonthlyStatus.objects.values_list('MONTH', flat=True).distinct().order_by('MONTH')
        month_names = {1: 'Januari', 2: 'Februari', 3: 'Maret', 4: 'April', 5: 'Mei', 6: 'Juni', 7: 'Juli', 8: 'Agustus', 9: 'September', 10: 'Oktober', 11: 'November', 12: 'Desember'}
        return [(str(m.month), month_names.get(m.month, f"Bulan {m.month}")) for m in months if m is not None]
    def queryset(self, request, queryset):
        if self.value(): return queryset.filter(MONTH__month=self.value())
        return queryset

class YearFilter(SimpleListFilter):
    title = 'Tahun Laporan'
    parameter_name = 'report_year'
    def lookups(self, request, model_admin):
        years = AssetMonthlyStatus.objects.values_list('YEAR', flat=True).distinct().order_by('YEAR')
        return [(str(y), str(y)) for y in years if y is not None]
    def queryset(self, request, queryset):
        if self.value(): return queryset.filter(YEAR=self.value())
        return queryset

def hapus_semua_data_filtered(modeladmin, request, queryset):
    """
    Menghapus semua data yang saat ini terfilter/terpilih langsung di level database,
    sehingga terhindar dari error TooManyFieldsSent.
    """
    jumlah, _ = queryset.delete()
    modeladmin.message_user(request, f"Berhasil menghapus {jumlah} data sekaligus.")

# Berikan label teks yang akan muncul di dropdown Action Django Admin
hapus_semua_data_filtered.short_description = "🔥 Hapus Massal Data Terfilter"


@admin.register(AssetMonthlyStatus, site=admin_site)
class AssetMonthlyStatusAdmin(ImportExportModelAdmin):
    resource_class = AssetMonthlyStatusResource

    list_display = (
        "No_Asset", "CN_SAP", "CN_ELLIPSE", "EGI", "display_foto", "TYPE", "GROUP",
        "CLASS_WEIGHT", "OWNERSHIP", "SECTION", "LOCATION", "SUB_SITE", "SUB_LOCATION",
        "BRAND", "SN", "HM_SMR", "HM_DATE", "SPO_EQUIPMENT", "PERSENTASE_SPO_display",
        "EQUIPMENT_CONDITION", "STATUS_EQUIPMENT", "STATUS_EQUIPMENT_DISPOSED", "NBV", "WEIGHT",
        "REFERENSI_NO_PDE", "YEAR", "MONTH", "BP"
    )
    search_fields = ("CN_SAP", "CN_ELLIPSE", "EGI")
    list_filter = (YearFilter, MonthFilter, "EQUIPMENT_CONDITION", "SECTION", "EGI")
    list_per_page = 5

    # 2. DAFTARKAN FUNGSI DI ATAS KE DALAM ACTIONS SINI 🌟
    actions = [hapus_semua_data_filtered, 'delete_selected']
    # ================================================================
    # 🌟 HELPER TERPUSAT — dipanggil oleh get_queryset & get_export_queryset
    # ================================================================
    def _apply_role_filter(self, request, qs):
        if request.user.is_superuser:
            return qs
        if not hasattr(request.user, 'userprofile'):
            return qs.none()
        try:
            profile      = request.user.userprofile
            user_lokasi  = profile.lokasi or ""
            user_section = profile.section or ""
        except Exception:
            return qs.none()
        if not user_lokasi:
            return qs.none()
        qs = qs.filter(LOCATION__iexact=user_lokasi)
        if user_section:
            qs = qs.filter(SECTION__iexact=user_section)
        return qs

    def get_queryset(self, request):
        qs = super().get_queryset(request)
        return self._apply_role_filter(request, qs)

    def get_export_queryset(self, request):
        qs = super().get_export_queryset(request)
        return self._apply_role_filter(request, qs)

    # ================================================================
    # 🌟 KOREKSI: Semua user (staff & superuser) boleh IMPORT
    # ================================================================
    def has_import_permission(self, request):
        # ✅ Semua user yang sudah login dan berstatus staff boleh import
        return request.user.is_active and request.user.is_staff

    # ================================================================
    # 🌟 KOREKSI: Semua user (staff & superuser) boleh EXPORT
    # ================================================================
    def has_export_permission(self, request):
        # ✅ Semua user yang sudah login dan berstatus staff boleh export
        # Data yang diexport otomatis terfilter sesuai role via get_export_queryset
        return request.user.is_active and request.user.is_staff

    # ================================================================
    # 🌟 KOREKSI: Semua user boleh melihat tombol ADD (form tambah data)
    # ================================================================
    def has_add_permission(self, request):
        # ✅ Semua staff aktif boleh tambah data Monthly Eqp Report
        return request.user.is_active and request.user.is_staff

    # ================================================================
    # 🌟 TAMBAHAN: Batasi CHANGE hanya pada data milik role sendiri
    # ================================================================
    def has_change_permission(self, request, obj=None):
        # Semua staff boleh membuka form edit
        if not (request.user.is_active and request.user.is_staff):
            return False
        # Superuser boleh edit semua
        if request.user.is_superuser:
            return True
        # Jika obj spesifik dicek, pastikan obj milik lokasi & section user
        if obj is not None and hasattr(request.user, 'userprofile'):
            try:
                profile      = request.user.userprofile
                user_lokasi  = profile.lokasi or ""
                user_section = profile.section or ""
                if user_lokasi and obj.LOCATION.lower() != user_lokasi.lower():
                    return False  # ← Tidak bisa edit data lokasi lain
                if user_section and obj.SECTION.lower() != user_section.lower():
                    return False  # ← Tidak bisa edit data section lain
            except Exception:
                return False
        return True

    # ================================================================
    # 🌟 TAMBAHAN: Batasi DELETE hanya pada data milik role sendiri
    # ================================================================
    def has_delete_permission(self, request, obj=None):
        # Semua staff boleh melihat tombol delete di list
        if not (request.user.is_active and request.user.is_staff):
            return False
        # Superuser boleh hapus semua
        if request.user.is_superuser:
            return True
        # Jika obj spesifik dicek, pastikan obj milik lokasi & section user
        if obj is not None and hasattr(request.user, 'userprofile'):
            try:
                profile      = request.user.userprofile
                user_lokasi  = profile.lokasi or ""
                user_section = profile.section or ""
                if user_lokasi and obj.LOCATION.lower() != user_lokasi.lower():
                    return False
                if user_section and obj.SECTION.lower() != user_section.lower():
                    return False
            except Exception:
                return False
        return True
    # ================================================================

    # ── Kustomisasi tampilan (tidak berubah) ──────────────────────

    def PERSENTASE_SPO_display(self, obj):
        try:
            if obj.PERSENTASE_SPO is not None:
                return f"{float(obj.PERSENTASE_SPO) * 100:.2f}%"
            return "-"
        except (ValueError, TypeError):
            return "-"
    PERSENTASE_SPO_display.short_description = "PERSENTASE SPO"

    def display_foto(self, obj):
        if obj.FOTO:
            return format_html(
                '<div style="width: 100%; text-align: center; margin-top: 15px; '
                'margin-bottom: 15px; padding: 10px; border: 1px dashed #e0e0e0; '
                'border-radius: 8px;">'
                '<img src="{}" style="max-width: 60px; height: auto; display: block; '
                'margin: 0 auto; border-radius: 5px;" /></div>',
                obj.FOTO.url
            )
        return "Tidak ada foto"
    display_foto.short_description = "Foto Aset"

    readonly_fields = ('preview_foto',)

    fieldsets = (
        (None, {
            'fields': (('No_Asset', 'CN_SAP'), 'CN_ELLIPSE', 'EGI', 'TYPE', 'GROUP', 'CLASS_WEIGHT', 'FOTO',)
        }),
        ('Detail Kepemilikan & Lokasi', {
            'fields': ('OWNERSHIP', 'SECTION', 'LOCATION', 'SUB_SITE', 'SUB_LOCATION',),
            'description': 'Informasi terkait kepemilikan dan penempatan aset.'
        }),
        ('Spesifikasi & Kondisi Teknis', {
            'fields': ('BRAND', 'SN', 'HM_SMR', 'HM_DATE', 'SPO_EQUIPMENT', 'PERSENTASE_SPO'),
        }),
        ('Status & Referensi', {
            'fields': ('EQUIPMENT_CONDITION', 'STATUS_EQUIPMENT', 'STATUS_EQUIPMENT_DISPOSED',
                       'NBV', 'WEIGHT', 'REFERENSI_NO_PDE', 'BP'),
        }),       
    )

    def preview_foto(self, obj):
        if obj.FOTO:
            return format_html(
                '<div style="width: 100%; text-align: center; margin-top: 15px; '
                'margin-bottom: 15px; padding: 10px; border: 1px dashed #e0e0e0; '
                'border-radius: 8px;">'
                '<img src="{}" style="max-width: 60px; height: auto; display: block; '
                'margin: 0 auto; border-radius: 5px;" /></div>',
                obj.FOTO.url
            )
        return ""
    preview_foto.short_description = "Pratinjau Gambar"

    def _is_atasan(self, user):
        if not user or user.is_superuser:
            return False
        try:
            profile = user.userprofile
            level = str(profile.jabatan_level).upper() if profile.jabatan_level else ''
            nama_resmi = str(profile.jabatan_nama_resmi).upper() if profile.jabatan_nama_resmi else ''
            keyword_atasan = ['SECTION HEAD', 'DEPARTMENT HEAD', 'CHIEF', 'MANAGER', 'GM', 'HEAD']
            if any(k in level or k in nama_resmi for k in keyword_atasan):
                return True
        except Exception:
            pass
        return False

    def has_add_permission(self, request):
        """
        Aturan Add:
        1. Superuser: Bisa.
        2. Officer / Senior Officer: Bisa.
        3. Atasan: Tidak bisa.
        """
        if request.user.is_superuser:
            return True
        
        # Atasan tidak boleh tambah data
        if self._is_atasan(request.user):
            return False
            
        # Cek apakah Officer / Senior Officer
        if hasattr(request.user, 'userprofile'):
            jabatan_level = str(getattr(request.user.userprofile, 'jabatan_level', '')).upper()
            if jabatan_level in ['SENIOR_OFFICER', 'OFFICER', 'SENIOR OFFICER']:
                return True
                
        return False

    def has_import_permission(self, request):
        """
        Aturan Import:
        1. Superuser: Bisa.
        2. Officer / Senior Officer: Bisa.
        3. Atasan: Tidak bisa.
        """
        if request.user.is_superuser:
            return True
            
        # Atasan tidak boleh import data
        if self._is_atasan(request.user):
            return False
            
        # Cek apakah Officer / Senior Officer
        if hasattr(request.user, 'userprofile'):
            jabatan_level = str(getattr(request.user.userprofile, 'jabatan_level', '')).upper()
            if jabatan_level in ['SENIOR_OFFICER', 'OFFICER', 'SENIOR OFFICER']:
                return True
                
        return False

    def has_export_permission(self, request):
        """
        Aturan Export:
        1. Superuser: Bisa.
        2. Atasan: Bisa (hanya menampilkan export).
        3. Officer / Senior Officer: Bisa.
        """
        if request.user.is_superuser:
            return True
            
        # Atasan diizinkan melakukan export
        if self._is_atasan(request.user):
            return True
            
        # Cek apakah Officer / Senior Officer
        if hasattr(request.user, 'userprofile'):
            jabatan_level = str(getattr(request.user.userprofile, 'jabatan_level', '')).upper()
            if jabatan_level in ['SENIOR_OFFICER', 'OFFICER', 'SENIOR OFFICER']:
                return True
                
        return False



    def get_export_formats(self):
        return [CSV, XLSX, JSON]

    def get_actions(self, request):
        actions = super().get_actions(request)
        if 'export_admin_action' in actions:
            del actions['export_admin_action']
        return actions
    

# =======================================
# ===== class untuk master monthly report =======#
# =======================================

# 1. PENGAMAN UNTUK ANGKA (Integer)
class SafeIntegerWidget(IntegerWidget):
    def clean(self, value, row=None, **kwargs):
        if not value or str(value).strip().upper() in ['NA', 'NONE', '', 'NULL']:
            return 0  
        try:
            cleaned_value = str(value).split('.')[0] 
            return int(cleaned_value)
        except (ValueError, TypeError):
            return 0

# 2. PENGAMAN UNTUK TEKS (CharField)
class SafeCharWidget(CharWidget):
    def clean(self, value, row=None, **kwargs):
        if value is None or str(value).strip().upper() in ['NONE', 'NA', 'NULL', '']:
            return ""  
        return super().clean(value, row, **kwargs)

# 3. PENGAMAN UNTUK TANGGAL (DateField)
class SafeDateWidget(DateWidget):
    def __init__(self, format=None, *args, **kwargs):
        self.format = format or '%Y-%m-%d'
        super().__init__(format=self.format, *args, **kwargs)

    def clean(self, value, row=None, **kwargs):
        if not value or str(value).strip().upper() in ['NA', 'NONE', '', 'NULL', '0-JAN-00', '0000-00-00']:
            return None

        # ✅ Gunakan 'dt' bukan 'datetime' agar tidak ambigu
        if isinstance(value, dt):        # <-- FIX UTAMA
            return value.date()
        if isinstance(value, date):
            return value

        try:
            string_value = str(value).strip()
            if ' ' in string_value:
                string_value = string_value.split(' ')[0]
            return dt.strptime(string_value, '%Y-%m-%d').date()  # <-- FIX
        except Exception:
            try:
                return super().clean(string_value, row, **kwargs)
            except Exception:
                return None
        
# 4. PENGAMAN UNTUK ANGKA DESIMAL (Khusus Persentase/NBV)
class SafeFloatWidget(DecimalWidget): 
    def clean(self, value, row=None, **kwargs):
        if value is None or str(value).strip().upper() in ['NA', 'NONE', 'NULL', '']:
            return None  
        try:
            cleaned_value = str(value).strip().replace(',', '.')
            return Decimal(cleaned_value)  # 🌟 PERBAIKAN: Menggunakan Decimal agar sinkron dengan DecimalWidget
        except (ValueError, TypeError, InvalidOperation):
            return None

# ==================================================================
# ======================== RESOURCE CLASS ==========================
# ==================================================================

class AssetMasterMonthlyStatusResource(resources.ModelResource):

    def get_import_id_fields(self):
        """
        MEMAKSA DJANGO MENGGUNAKAN TIGA KUNCI UTAMA
        Ini mengunci agar Django tahu tolok ukur keunikan data adalah kombinasi 3 field ini,
        menghindari konfigurasi statis yang sering ter-bypass.
        """
        return ['CN_SAP', 'MONTH', 'YEAR']

    def import_row(self, row, instance_loader, **kwargs):
        """
        PENGAMAN TINGKAT TINGGI (Saran Optimal Bapak Junaedi):
        Melakukan normalisasi tanggal di awal untuk mencegah kebocoran data pada cache Django,
        memungkinkan penghapusan 'force_init_instance = True' demi efisiensi performa server INSIDE.
        """
        from datetime import datetime as dt, date
        from django.db import models

        # 1. Fungsi Pembantu: Mengambil nilai & nama key asli dari Excel (Case-Insensitive)
        def get_flexible_value(row_dict, target_name):
            target_clean = str(target_name).strip().lower()
            for key, val in row_dict.items():
                if str(key).strip().lower() == target_clean:
                    return val, key
            return None, None

        # 2. Fungsi Pembantu: Paksa apapun bentuk tanggalnya menjadi string 'YYYY-MM-DD'
        def normalize_date_to_str(value):
            if value is None:
                return None
            # Jika objek datetime/date dari openpyxl (pembaca Excel)
            if isinstance(value, dt):
                return value.strftime('%Y-%m-%d')
            if isinstance(value, date):
                return value.strftime('%Y-%m-%d')
            # Jika string mentah dengan timestamp jam "2026-06-30 00:00:00"
            string_val = str(value).strip()
            if ' ' in string_val:
                string_val = string_val.split(' ')[0]
            return string_val

        # 3. Ekstrak nilai kunci dari row
        cn_sap_value, cn_sap_key = get_flexible_value(row, 'Code Number')
        month_value, month_key   = get_flexible_value(row, 'Month')
        year_value, year_key     = get_flexible_value(row, 'Year')

        # 4. ✅ NORMALISASI UTAMA: Bersihkan data kolom MONTH & HM_DATE langsung di objek row
        if month_key and month_value:
            row[month_key] = normalize_date_to_str(month_value)

        hm_date_value, hm_date_key = get_flexible_value(row, 'Hour Meter Date')
        if hm_date_key and hm_date_value:
            row[hm_date_key] = normalize_date_to_str(hm_date_value)

        # 5. Logika Deteksi Data Eksisting untuk Mengubah Operasi menjadi UPDATE
        if cn_sap_value and month_value and year_value:
            cn_sap_clean = str(cn_sap_value).strip()
            
            try:
                year_clean = int(float(str(year_value).strip()))
            except (ValueError, TypeError):
                year_clean = None

            # Ambil nilai MONTH yang sudah bersih dari objek row
            month_str_short = row.get(month_key, '')

            if year_clean and month_str_short:
                # Cari data lama langsung ke database PostgreSQL
                existing_instance = AssetMasterMonthlyStatus.objects.filter(
                    CN_SAP=cn_sap_clean,
                    YEAR=year_clean
                ).filter(
                    models.Q(MONTH=month_str_short) |
                    models.Q(MONTH__contains=month_str_short)
                ).first()

                # 🌟 JIKA DATA LAMA DITEMUKAN: Suntik ID database asli agar Django melakukan UPDATE
                if existing_instance:
                    row['id'] = existing_instance.id

        # 6. Jalankan fungsi bawaan untuk memproses baris data yang sudah steril
        return super().import_row(row, instance_loader, **kwargs)


    def get_instance(self, instance_loader, row):
        """
        Menjamin jika row['id'] sudah kita set di atas, Django otomatis mengambil 
        objek lama dari database secara instan tanpa validasi berbelit.
        """
        if 'id' in row:
            try:
                return self._meta.model.objects.get(id=row['id'])
            except self._meta.model.DoesNotExist:
                return None
        return super().get_instance(instance_loader, row)

    def clean_HM_DATE(self, value):
        if value is not None and str(value).strip().lower() == "midnight":
            return None
        return value
    
    def clean_MONTH(self, value):
        if not value or str(value).strip().upper() in ['NA', 'NONE', '', 'NULL']:
            return None
        try:
            string_val = str(value).strip()
            if ' ' in string_val:
                string_val = string_val.split(' ')[0]
            return dt.strptime(string_val, '%Y-%m-%d').date()  # <-- pakai 'dt'
        except Exception:
            return value

    def clean_HM_DATE(self, value):  # Definisi TUNGGAL (hapus duplikat)
        if not value or str(value).strip().upper() in ['NA', 'NONE', '', 'NULL', 'MIDNIGHT']:
            return None
        try:
            string_val = str(value).strip()
            if ' ' in string_val:
                string_val = string_val.split(' ')[0]
            return dt.strptime(string_val, '%Y-%m-%d').date()  # <-- pakai 'dt'
        except Exception:
            return None

    def save_instance(self, instance, is_new, *args, **kwargs):
        super().save_instance(instance, is_new, *args, **kwargs)

    No_Asset = fields.Field(column_name='Nomor Asset', attribute='No_Asset', widget=SafeCharWidget())
    CN_SAP = fields.Field(column_name='Code Number', attribute='CN_SAP', widget=SafeCharWidget())
    CN_ELLIPSE = fields.Field(column_name='Code Number Ellipse', attribute='CN_ELLIPSE', widget=SafeCharWidget())
    EGI = fields.Field(column_name='EGI', attribute='EGI', widget=SafeCharWidget())
    TYPE = fields.Field(column_name='Type', attribute='TYPE', widget=SafeCharWidget())
    GROUP = fields.Field(column_name='Class', attribute='GROUP', widget=SafeCharWidget())
    CLASS_WEIGHT = fields.Field(column_name='CN Class', attribute='CLASS_WEIGHT', widget=SafeCharWidget())
    OWNERSHIP = fields.Field(column_name='Ownership', attribute='OWNERSHIP', widget=SafeCharWidget())
    SECTION = fields.Field(column_name='PIC', attribute='SECTION', widget=SafeCharWidget())
    LOCATION = fields.Field(column_name='Location', attribute='LOCATION', widget=SafeCharWidget())
    LOCATION_CODE_SAP = fields.Field(column_name='Location Code SAP', attribute='LOCATION_CODE_SAP', widget=SafeCharWidget())
    SUB_SITE = fields.Field(column_name='Sub Site', attribute='SUB_SITE', widget=SafeCharWidget())
    SUB_LOCATION = fields.Field(column_name='Sub Location', attribute='SUB_LOCATION', widget=SafeCharWidget())
    BRAND = fields.Field(column_name='Brand', attribute='BRAND', widget=SafeCharWidget())
    SN = fields.Field(column_name='Serial Number', attribute='SN', widget=SafeCharWidget())
    
    # 🌟 PERBAIKAN: Menggunakan SafeCharWidget menyesuaikan CharField pada models.py Bapak
    HM_SMR = fields.Field(column_name='Hour Meter', attribute='HM_SMR', widget=SafeCharWidget())
    
    HM_DATE = fields.Field(column_name='Hour Meter Date', attribute='HM_DATE', widget=SafeDateWidget(format='%Y-%m-%d'))
    SPO_EQUIPMENT = fields.Field(column_name='SPO Equipment', attribute='SPO_EQUIPMENT', widget=SafeIntegerWidget())
    PERSENTASE_SPO = fields.Field(column_name='% SPO Equipment', attribute='PERSENTASE_SPO', widget=SafeFloatWidget())
    
    EQUIPMENT_CONDITION = fields.Field(column_name='Equipment Condition', attribute='EQUIPMENT_CONDITION', widget=SafeCharWidget())
    STATUS_EQUIPMENT = fields.Field(column_name='Status Equipment', attribute='STATUS_EQUIPMENT', widget=SafeCharWidget())
    STATUS_SAP = fields.Field(column_name='Status SAP', attribute='STATUS_SAP', widget=SafeCharWidget())
    STATUS_EQUIPMENT_DISPOSED = fields.Field(column_name='Status Equipment Disposed', attribute='STATUS_EQUIPMENT_DISPOSED', widget=SafeCharWidget())
    
    REFERENSI_NO_PDE = fields.Field(column_name='Referensi No PDE', attribute='REFERENSI_NO_PDE', widget=SafeCharWidget())
    YEAR = fields.Field(column_name='Year', attribute='YEAR', widget=SafeIntegerWidget())
    MONTH = fields.Field(column_name='Month', attribute='MONTH', widget=SafeDateWidget(format='%Y-%m-%d'))
    BP = fields.Field(column_name='BP', attribute='BP', widget=SafeCharWidget())

    class Meta:
        model = AssetMasterMonthlyStatus
        import_id_fields = ['CN_SAP', 'MONTH', 'YEAR']
        fields = (
            'No_Asset', 'CN_SAP', 'CN_ELLIPSE', 'EGI', 'TYPE', 'GROUP', 'CLASS_WEIGHT',
            'OWNERSHIP', 'SECTION', 'LOCATION','LOCATION_CODE_SAP','SUB_SITE', 'SUB_LOCATION', 'BRAND',
            'SN', 'HM_SMR', 'HM_DATE', 'SPO_EQUIPMENT', 'PERSENTASE_SPO',
            'EQUIPMENT_CONDITION', 'STATUS_EQUIPMENT', 'STATUS_SAP', 'STATUS_EQUIPMENT_DISPOSED','REFERENSI_NO_PDE', 'YEAR', 'MONTH', 'BP',
        )
        export_order = fields      
        skip_unchanged = True
        report_skipped = True

# ==================================================================
# ======================== FILTER CLASSES ==========================
# ==================================================================

class MonthFilter(SimpleListFilter):
    title = 'Bulan Laporan'
    parameter_name = 'report_month'

    def lookups(self, request, model_admin):
        months = AssetMasterMonthlyStatus.objects.values_list('MONTH', flat=True).distinct().order_by('MONTH')
        month_names = {
            1: 'Januari', 2: 'Februari', 3: 'Maret', 4: 'April',
            5: 'Mei', 6: 'Juni', 7: 'Juli', 8: 'Agustus',
            9: 'September', 10: 'Oktober', 11: 'November', 12: 'Desember'
        }
        return [(str(m.month), month_names.get(m.month, f"Bulan {m.month}")) for m in months if m is not None]

    def queryset(self, request, queryset):
        if self.value():
            return queryset.filter(MONTH__month=self.value())
        return queryset

class YearFilter(SimpleListFilter):
    title = 'Tahun Laporan'
    parameter_name = 'report_year'

    def lookups(self, request, model_admin):
        years = AssetMasterMonthlyStatus.objects.values_list('YEAR', flat=True).distinct().order_by('YEAR')
        return [(str(y), str(y)) for y in years if y is not None]

    def queryset(self, request, queryset):
        if self.value():
            return queryset.filter(YEAR=self.value())
        return queryset


# ==================================================================
# ======================== ADMIN INTERFACE =========================
# ==================================================================

@admin.register(AssetMasterMonthlyStatus, site=admin_site)
class AssetMasterMonthlyStatusAdmin(ImportExportModelAdmin):
    resource_class = AssetMasterMonthlyStatusResource

    # 🌟 PERBAIKAN: Menghapus "NBV" dan "WEIGHT" agar tidak AttributeError
    list_display = (
        "No_Asset", "CN_SAP", "CN_ELLIPSE", "EGI", "display_foto", "TYPE", "GROUP",
        "CLASS_WEIGHT", "OWNERSHIP", "SECTION", "LOCATION","LOCATION_CODE_SAP","SUB_SITE", "SUB_LOCATION",
        "BRAND", "SN", "HM_SMR", "HM_DATE", "SPO_EQUIPMENT", "PERSENTASE_SPO_display",
        "EQUIPMENT_CONDITION", "STATUS_EQUIPMENT","STATUS_SAP", "STATUS_EQUIPMENT_DISPOSED","REFERENSI_NO_PDE", "YEAR", "MONTH","BP"
    )
    search_fields = ("CN_SAP", "CN_ELLIPSE", "EGI")
    list_filter = (YearFilter,MonthFilter,"EQUIPMENT_CONDITION","SECTION","EGI")
    list_per_page = 5


    # 🌟 KEY LOGIC: ROW-LEVEL SECURITY (HAK AKSES DATA) 🌟
    def get_queryset(self, request):
        qs = super().get_queryset(request)
        
        # 1. Jika Superuser (Bapak), tampilkan keseluruhan data tanpa filter
        if request.user.is_superuser:
            return qs
            
        # 2. Jika User biasa (Karyawan), pangkas data berdasarkan Lokasi & Section di UserProfile
        try:
            profile = request.user.userprofile  # Memanggil relasi profil dari accounts
            user_lokasi = profile.lokasi
            user_section = profile.section
            
            # Jika user memiliki setting lokasi dan section, filter data tabel
            if user_lokasi and user_section:
                return qs.filter(LOCATION=user_lokasi, SECTION=user_section)
                
        except AttributeError:
            # Jika user tidak sengaja terhapus/tidak punya profile, amankan dengan mengosongkan data
            return qs.none()
            
        return qs
    
    # ==================================================================
    # 🌟 KUSTOMISASI HAK AKSES TOMBOL IMPORT & EXPORT
    # ==================================================================

    def has_import_permission(self, request):
        """
        Menentukan siapa yang boleh melihat & menggunakan tombol IMPORT.
        """
        # Contoh 1: Hanya Superuser (Bapak) yang boleh Import data baru
        if request.user.is_superuser:
            return True
            
        # Untuk user biasa, matikan tombol Import
        return False


    def has_export_permission(self, request):
        """
        Menentukan siapa yang boleh melihat & menggunakan tombol EXPORT.
        """
        # Contoh 2: Baik Superuser maupun User Biasa boleh melakukan Export data
        # (Data yang diexport oleh user biasa otomatis tetap terfilter sesuai lokasinya)
        return True

    # ------------------ Kustomisasi Tampilan ------------------

    def PERSENTASE_SPO_display(self, obj):
        try:
            if obj.PERSENTASE_SPO is not None and obj.PERSENTASE_SPO != "":
                return f"{float(obj.PERSENTASE_SPO) * 100:.2f}%"
            return "-"
        except (ValueError, TypeError):
            return "-"
    PERSENTASE_SPO_display.short_description = "PERSENTASE SPO"

    def display_foto(self, obj):
        if hasattr(obj, 'FOTO') and obj.FOTO:
            return format_html(
                '<div style="width: 100%; text-align: center; margin-top: 15px; margin-bottom: 15px; padding: 10px; border: 1px dashed #e0e0e0; border-radius: 8px;">'
                '<img src="{}" style="max-width: 60px; height: auto; display: block; margin: 0 auto; border-radius: 5px;" />'
                '</div>', obj.FOTO.url)
        return "Tidak ada foto"
    display_foto.short_description = "Foto Aset"

    readonly_fields = ('preview_foto',)

    # 🌟 PERBAIKAN: Menyesuaikan isi fieldsets (menghapus NBV & WEIGHT)
    fieldsets = (
        (None, {
            'fields': (
                ('No_Asset', 'CN_SAP'),
                'CN_ELLIPSE', 'EGI', 'TYPE', 'GROUP', 'CLASS_WEIGHT',
            )
        }),
        ('Detail Kepemilikan & Lokasi', {
            'fields': ('OWNERSHIP', 'SECTION', 'LOCATION','LOCATION_CODE_SAP', 'SUB_SITE','SUB_LOCATION',),
            'description': 'Informasi terkait kepemilikan dan penempatan aset.'
        }),
        ('Spesifikasi & Kondisi Teknis', {
            'fields': ('BRAND', 'SN', 'HM_SMR', 'HM_DATE', 'SPO_EQUIPMENT', 'PERSENTASE_SPO'),
        }),
        ('Status & Referensi', {
            'fields': ('EQUIPMENT_CONDITION', 'STATUS_EQUIPMENT', 'STATUS_SAP','STATUS_EQUIPMENT_DISPOSED','REFERENSI_NO_PDE','BP'),
        }),
    )

    def preview_foto(self, obj):
        if hasattr(obj, 'FOTO') and obj.FOTO:
            return format_html(
                '<div style="width: 100%; text-align: center; margin-top: 15px; margin-bottom: 15px; padding: 10px; border: 1px dashed #e0e0e0; border-radius: 8px;">'
                '<img src="{}" style="max-width: 60px; height: auto; display: block; margin: 0 auto; border-radius: 5px;" />'
                '</div>',
                obj.FOTO.url
            )
        return ""
    preview_foto.short_description = "Pratinjau Gambar"

    def get_export_formats(self):
        return [CSV, XLSX, JSON]

    def get_actions(self, request):
        actions = super().get_actions(request)
        if 'export_admin_action' in actions:
            del actions['export_admin_action']
        return actions


# ==================================================================
# ======================== RESOURCE CLASS AseetFinalMonthlyReport ==========================
# ==================================================================

class AssetFinalMonthlyStatusResource(resources.ModelResource):

    def get_import_id_fields(self):
        """
        MEMAKSA DJANGO MENGGUNAKAN TIGA KUNCI UTAMA
        Ini mengunci agar Django tahu tolok ukur keunikan data adalah kombinasi 3 field ini,
        menghindari konfigurasi statis yang sering ter-bypass.
        """
        return ['CN_SAP', 'MONTH', 'YEAR']

    def import_row(self, row, instance_loader, **kwargs):
        """
        PENGAMAN TINGKAT TINGGI (Saran Optimal Bapak Junaedi):
        Melakukan normalisasi tanggal di awal untuk mencegah kebocoran data pada cache Django,
        memungkinkan penghapusan 'force_init_instance = True' demi efisiensi performa server INSIDE.
        """
        from datetime import datetime as dt, date
        from django.db import models

        # 1. Fungsi Pembantu: Mengambil nilai & nama key asli dari Excel (Case-Insensitive)
        def get_flexible_value(row_dict, target_name):
            target_clean = str(target_name).strip().lower()
            for key, val in row_dict.items():
                if str(key).strip().lower() == target_clean:
                    return val, key
            return None, None

        # 2. Fungsi Pembantu: Paksa apapun bentuk tanggalnya menjadi string 'YYYY-MM-DD'
        def normalize_date_to_str(value):
            if value is None:
                return None
            # Jika objek datetime/date dari openpyxl (pembaca Excel)
            if isinstance(value, dt):
                return value.strftime('%Y-%m-%d')
            if isinstance(value, date):
                return value.strftime('%Y-%m-%d')
            # Jika string mentah dengan timestamp jam "2026-06-30 00:00:00"
            string_val = str(value).strip()
            if ' ' in string_val:
                string_val = string_val.split(' ')[0]
            return string_val

        # 3. Ekstrak nilai kunci dari row
        cn_sap_value, cn_sap_key = get_flexible_value(row, 'Code Number')
        month_value, month_key   = get_flexible_value(row, 'Month')
        year_value, year_key     = get_flexible_value(row, 'Year')

        # 4. ✅ NORMALISASI UTAMA: Bersihkan data kolom MONTH & HM_DATE langsung di objek row
        if month_key and month_value:
            row[month_key] = normalize_date_to_str(month_value)

        hm_date_value, hm_date_key = get_flexible_value(row, 'Hour Meter Date')
        if hm_date_key and hm_date_value:
            row[hm_date_key] = normalize_date_to_str(hm_date_value)

        # 5. Logika Deteksi Data Eksisting untuk Mengubah Operasi menjadi UPDATE
        if cn_sap_value and month_value and year_value:
            cn_sap_clean = str(cn_sap_value).strip()
            
            try:
                year_clean = int(float(str(year_value).strip()))
            except (ValueError, TypeError):
                year_clean = None

            # Ambil nilai MONTH yang sudah bersih dari objek row
            month_str_short = row.get(month_key, '')

            if year_clean and month_str_short:
                # Cari data lama langsung ke database PostgreSQL
                existing_instance = AssetFinalMonthlyStatus.objects.filter(
                    CN_SAP=cn_sap_clean,
                    YEAR=year_clean
                ).filter(
                    models.Q(MONTH=month_str_short) |
                    models.Q(MONTH__contains=month_str_short)
                ).first()

                # 🌟 JIKA DATA LAMA DITEMUKAN: Suntik ID database asli agar Django melakukan UPDATE
                if existing_instance:
                    row['id'] = existing_instance.id

        # 6. Jalankan fungsi bawaan untuk memproses baris data yang sudah steril
        return super().import_row(row, instance_loader, **kwargs)


    def get_instance(self, instance_loader, row):
        """
        Menjamin jika row['id'] sudah kita set di atas, Django otomatis mengambil 
        objek lama dari database secara instan tanpa validasi berbelit.
        """
        if 'id' in row:
            try:
                return self._meta.model.objects.get(id=row['id'])
            except self._meta.model.DoesNotExist:
                return None
        return super().get_instance(instance_loader, row)

    def clean_HM_DATE(self, value):
        if value is not None and str(value).strip().lower() == "midnight":
            return None
        return value
    
    def clean_MONTH(self, value):
        if not value or str(value).strip().upper() in ['NA', 'NONE', '', 'NULL']:
            return None
        try:
            string_val = str(value).strip()
            if ' ' in string_val:
                string_val = string_val.split(' ')[0]
            return dt.strptime(string_val, '%Y-%m-%d').date()  # <-- pakai 'dt'
        except Exception:
            return value

    def clean_HM_DATE(self, value):  # Definisi TUNGGAL (hapus duplikat)
        if not value or str(value).strip().upper() in ['NA', 'NONE', '', 'NULL', 'MIDNIGHT']:
            return None
        try:
            string_val = str(value).strip()
            if ' ' in string_val:
                string_val = string_val.split(' ')[0]
            return dt.strptime(string_val, '%Y-%m-%d').date()  # <-- pakai 'dt'
        except Exception:
            return None

    def save_instance(self, instance, is_new, *args, **kwargs):
        super().save_instance(instance, is_new, *args, **kwargs)

    No_Asset = fields.Field(column_name='Nomor Asset', attribute='No_Asset', widget=SafeCharWidget())
    CN_SAP = fields.Field(column_name='Code Number', attribute='CN_SAP', widget=SafeCharWidget())
    CN_ELLIPSE = fields.Field(column_name='Code Number Ellipse', attribute='CN_ELLIPSE', widget=SafeCharWidget())
    EGI = fields.Field(column_name='EGI', attribute='EGI', widget=SafeCharWidget())
    TYPE = fields.Field(column_name='Type', attribute='TYPE', widget=SafeCharWidget())
    GROUP = fields.Field(column_name='Class', attribute='GROUP', widget=SafeCharWidget())
    CLASS_WEIGHT = fields.Field(column_name='CN Class', attribute='CLASS_WEIGHT', widget=SafeCharWidget())
    OWNERSHIP = fields.Field(column_name='Ownership', attribute='OWNERSHIP', widget=SafeCharWidget())
    SECTION = fields.Field(column_name='PIC', attribute='SECTION', widget=SafeCharWidget())
    LOCATION = fields.Field(column_name='Location', attribute='LOCATION', widget=SafeCharWidget())
    LOCATION_CODE_SAP = fields.Field(column_name='Location Code SAP', attribute='LOCATION_CODE_SAP', widget=SafeCharWidget())
    SUB_SITE = fields.Field(column_name='Sub Site', attribute='SUB_SITE', widget=SafeCharWidget())
    SUB_LOCATION = fields.Field(column_name='Sub Location', attribute='SUB_LOCATION', widget=SafeCharWidget())
    BRAND = fields.Field(column_name='Brand', attribute='BRAND', widget=SafeCharWidget())
    SN = fields.Field(column_name='Serial Number', attribute='SN', widget=SafeCharWidget())
    
    # 🌟 PERBAIKAN: Menggunakan SafeCharWidget menyesuaikan CharField pada models.py Bapak
    HM_SMR = fields.Field(column_name='Hour Meter', attribute='HM_SMR', widget=SafeCharWidget())
    
    HM_DATE = fields.Field(column_name='Hour Meter Date', attribute='HM_DATE', widget=SafeDateWidget(format='%Y-%m-%d'))
    SPO_EQUIPMENT = fields.Field(column_name='SPO Equipment', attribute='SPO_EQUIPMENT', widget=SafeIntegerWidget())
    PERSENTASE_SPO = fields.Field(column_name='% SPO Equipment', attribute='PERSENTASE_SPO', widget=SafeFloatWidget())
    
    EQUIPMENT_CONDITION = fields.Field(column_name='Equipment Condition', attribute='EQUIPMENT_CONDITION', widget=SafeCharWidget())
    STATUS_EQUIPMENT = fields.Field(column_name='Status Equipment', attribute='STATUS_EQUIPMENT', widget=SafeCharWidget())
    STATUS_SAP = fields.Field(column_name='Status SAP', attribute='STATUS_SAP', widget=SafeCharWidget())
    STATUS_EQUIPMENT_DISPOSED = fields.Field(column_name='Status Equipment Disposed', attribute='STATUS_EQUIPMENT_DISPOSED', widget=SafeCharWidget())
    
    REFERENSI_NO_PDE = fields.Field(column_name='Referensi No PDE', attribute='REFERENSI_NO_PDE', widget=SafeCharWidget())
    YEAR = fields.Field(column_name='Year', attribute='YEAR', widget=SafeIntegerWidget())
    MONTH = fields.Field(column_name='Month', attribute='MONTH', widget=SafeDateWidget(format='%Y-%m-%d'))
    BP = fields.Field(column_name='BP', attribute='BP', widget=SafeCharWidget())

    class Meta:
        model = AssetFinalMonthlyStatus
        import_id_fields = ['CN_SAP', 'MONTH', 'YEAR']
        fields = (
            'No_Asset', 'CN_SAP', 'CN_ELLIPSE', 'EGI', 'TYPE', 'GROUP', 'CLASS_WEIGHT',
            'OWNERSHIP', 'SECTION', 'LOCATION','LOCATION_CODE_SAP','SUB_SITE', 'SUB_LOCATION', 'BRAND',
            'SN', 'HM_SMR', 'HM_DATE', 'SPO_EQUIPMENT', 'PERSENTASE_SPO',
            'EQUIPMENT_CONDITION', 'STATUS_EQUIPMENT', 'STATUS_SAP', 'STATUS_EQUIPMENT_DISPOSED','REFERENSI_NO_PDE', 'YEAR', 'MONTH', 'BP',
        )
        export_order = fields      
        skip_unchanged = True
        report_skipped = True

# ==================================================================
# ======================== FILTER CLASSES ==========================
# ==================================================================

class MonthFilter(SimpleListFilter):
    title = 'Bulan Laporan'
    parameter_name = 'report_month'

    def lookups(self, request, model_admin):
        months = AssetFinalMonthlyStatus.objects.values_list('MONTH', flat=True).distinct().order_by('MONTH')
        month_names = {
            1: 'Januari', 2: 'Februari', 3: 'Maret', 4: 'April',
            5: 'Mei', 6: 'Juni', 7: 'Juli', 8: 'Agustus',
            9: 'September', 10: 'Oktober', 11: 'November', 12: 'Desember'
        }
        return [(str(m.month), month_names.get(m.month, f"Bulan {m.month}")) for m in months if m is not None]

    def queryset(self, request, queryset):
        if self.value():
            return queryset.filter(MONTH__month=self.value())
        return queryset

class YearFilter(SimpleListFilter):
    title = 'Tahun Laporan'
    parameter_name = 'report_year'

    def lookups(self, request, model_admin):
        years = AssetFinalMonthlyStatus.objects.values_list('YEAR', flat=True).distinct().order_by('YEAR')
        return [(str(y), str(y)) for y in years if y is not None]

    def queryset(self, request, queryset):
        if self.value():
            return queryset.filter(YEAR=self.value())
        return queryset


# ==================================================================
# ======================== ADMIN INTERFACE =========================
# ==================================================================

@admin.register(AssetFinalMonthlyStatus, site=admin_site)
class AssetFinalMonthlyStatusAdmin(ImportExportModelAdmin):
    resource_class = AssetFinalMonthlyStatusResource

    # 🌟 PERBAIKAN: Menghapus "NBV" dan "WEIGHT" agar tidak AttributeError
    list_display = (
        "No_Asset", "CN_SAP", "CN_ELLIPSE", "EGI", "display_foto", "TYPE", "GROUP",
        "CLASS_WEIGHT", "OWNERSHIP", "SECTION", "LOCATION","LOCATION_CODE_SAP","SUB_SITE", "SUB_LOCATION",
        "BRAND", "SN", "HM_SMR", "HM_DATE", "SPO_EQUIPMENT", "PERSENTASE_SPO_display",
        "EQUIPMENT_CONDITION", "STATUS_EQUIPMENT","STATUS_SAP", "STATUS_EQUIPMENT_DISPOSED","REFERENSI_NO_PDE", "YEAR", "MONTH","BP"
    )
    search_fields = ("CN_SAP", "CN_ELLIPSE", "EGI")
    list_filter = (YearFilter,MonthFilter,"EQUIPMENT_CONDITION","SECTION","EGI")
    list_per_page = 5


    # 🌟 KEY LOGIC: ROW-LEVEL SECURITY (HAK AKSES DATA) 🌟
    def get_queryset(self, request):
        qs = super().get_queryset(request)
        
        # 1. Jika Superuser (Bapak), tampilkan keseluruhan data tanpa filter
        if request.user.is_superuser:
            return qs
            
        # 2. Jika User biasa (Karyawan), pangkas data berdasarkan Lokasi & Section di UserProfile
        try:
            profile = request.user.userprofile  # Memanggil relasi profil dari accounts
            user_lokasi = profile.lokasi
            user_section = profile.section
            
            # Jika user memiliki setting lokasi dan section, filter data tabel
            if user_lokasi and user_section:
                return qs.filter(LOCATION=user_lokasi, SECTION=user_section)
                
        except AttributeError:
            # Jika user tidak sengaja terhapus/tidak punya profile, amankan dengan mengosongkan data
            return qs.none()
            
        return qs
    
    # ==================================================================
    # 🌟 KUSTOMISASI HAK AKSES TOMBOL IMPORT & EXPORT
    # ==================================================================

    def has_import_permission(self, request):
        """
        Menentukan siapa yang boleh melihat & menggunakan tombol IMPORT.
        """
        # Contoh 1: Hanya Superuser (Bapak) yang boleh Import data baru
        if request.user.is_superuser:
            return True
            
        # Untuk user biasa, matikan tombol Import
        return False


    def has_export_permission(self, request):
        """
        Menentukan siapa yang boleh melihat & menggunakan tombol EXPORT.
        """
        # Contoh 2: Baik Superuser maupun User Biasa boleh melakukan Export data
        # (Data yang diexport oleh user biasa otomatis tetap terfilter sesuai lokasinya)
        return True

    # ------------------ Kustomisasi Tampilan ------------------

    def PERSENTASE_SPO_display(self, obj):
        try:
            if obj.PERSENTASE_SPO is not None and obj.PERSENTASE_SPO != "":
                return f"{float(obj.PERSENTASE_SPO) * 100:.2f}%"
            return "-"
        except (ValueError, TypeError):
            return "-"
    PERSENTASE_SPO_display.short_description = "PERSENTASE SPO"

    def display_foto(self, obj):
        if hasattr(obj, 'FOTO') and obj.FOTO:
            return format_html(
                '<div style="width: 100%; text-align: center; margin-top: 15px; margin-bottom: 15px; padding: 10px; border: 1px dashed #e0e0e0; border-radius: 8px;">'
                '<img src="{}" style="max-width: 60px; height: auto; display: block; margin: 0 auto; border-radius: 5px;" />'
                '</div>', obj.FOTO.url)
        return "Tidak ada foto"
    display_foto.short_description = "Foto Aset"

    readonly_fields = ('preview_foto',)

    # 🌟 PERBAIKAN: Menyesuaikan isi fieldsets (menghapus NBV & WEIGHT)
    fieldsets = (
        (None, {
            'fields': (
                ('No_Asset', 'CN_SAP'),
                'CN_ELLIPSE', 'EGI', 'TYPE', 'GROUP', 'CLASS_WEIGHT',
            )
        }),
        ('Detail Kepemilikan & Lokasi', {
            'fields': ('OWNERSHIP', 'SECTION', 'LOCATION','LOCATION_CODE_SAP', 'SUB_SITE','SUB_LOCATION',),
            'description': 'Informasi terkait kepemilikan dan penempatan aset.'
        }),
        ('Spesifikasi & Kondisi Teknis', {
            'fields': ('BRAND', 'SN', 'HM_SMR', 'HM_DATE', 'SPO_EQUIPMENT', 'PERSENTASE_SPO'),
        }),
        ('Status & Referensi', {
            'fields': ('EQUIPMENT_CONDITION', 'STATUS_EQUIPMENT', 'STATUS_SAP','STATUS_EQUIPMENT_DISPOSED','REFERENSI_NO_PDE','BP'),
        }),
    )

    def preview_foto(self, obj):
        if hasattr(obj, 'FOTO') and obj.FOTO:
            return format_html(
                '<div style="width: 100%; text-align: center; margin-top: 15px; margin-bottom: 15px; padding: 10px; border: 1px dashed #e0e0e0; border-radius: 8px;">'
                '<img src="{}" style="max-width: 60px; height: auto; display: block; margin: 0 auto; border-radius: 5px;" />'
                '</div>',
                obj.FOTO.url
            )
        return ""
    preview_foto.short_description = "Pratinjau Gambar"

    def get_export_formats(self):
        return [CSV, XLSX, JSON]

    def get_actions(self, request):
        actions = super().get_actions(request)
        if 'export_admin_action' in actions:
            del actions['export_admin_action']
        return actions




# ===========================================
# ---- Resource untuk AssetEquipment -----
# ============================================
class AssetEquipmentResource(resources.ModelResource):
    def clean_HM_DATE(self, value):
        if value is not None and str(value).lower() == "midnight":
            # Jika HM_DATE di model adalah DateField, ini harus dikonversi ke tanggal yang valid.
            # Mengembalikan None jika "midnight" tidak masuk akal untuk DateField
            return None
        return value

    def clean_PERSENTASE_SPO(self, value):
        if value is None or str(value).strip() == '':
            return None
        try:
            return float(str(value).replace(',', '.'))
        except ValueError:
            raise ValueError(f"'{value}' bukan angka yang valid untuk PERSENTASE_SPO.")

    No_Asset = fields.Field(column_name='No Asset', attribute='No_Asset', widget=CharWidget())
    CN_SAP = fields.Field(column_name='Code Number', attribute='CN_SAP', widget=CharWidget())
    CN_ELLIPSE = fields.Field(column_name='Code Number Ellipse', attribute='CN_ELLIPSE', widget=CharWidget())
    TYPE = fields.Field(column_name='Type', attribute='TYPE', widget=CharWidget())
    GROUP = fields.Field(column_name='Class Equipment', attribute='GROUP', widget=CharWidget())
    CLASS_WEIGHT = fields.Field(column_name='Class Weight', attribute='CLASS_WEIGHT', widget=CharWidget())
    OWNERSHIP = fields.Field(column_name='Ownership', attribute='OWNERSHIP', widget=CharWidget())
    SECTION = fields.Field(column_name='Section', attribute='SECTION', widget=CharWidget())
    LOCATION = fields.Field(column_name='Location', attribute='LOCATION', widget=CharWidget())
    SUB_SITE = fields.Field(column_name='Sub Site', attribute='SUB_SITE', widget=CharWidget())
    SUB_LOCATION = fields.Field(column_name='Sub Location', attribute='SUB_LOCATION', widget=CharWidget())
    BRAND = fields.Field(column_name='Brand', attribute='BRAND', widget=CharWidget())
    SN = fields.Field(column_name='Serial Number', attribute='SN', widget=CharWidget())
    HM_SMR = fields.Field(column_name='Hour Meter', attribute='HM_SMR', widget=CharWidget())
    HM_DATE = fields.Field(column_name='Hour Meter Date', attribute='HM_DATE', widget=DateWidget(format='%Y-%m-%d'))
    SPO_EQUIPMENT = fields.Field(column_name='SPO Equipment', attribute='SPO_EQUIPMENT', widget=IntegerWidget())
    PERSENTASE_SPO = fields.Field(column_name='% SPO Equipment', attribute='PERSENTASE_SPO', widget=CharWidget())
    EQUIPMENT_CONDITION = fields.Field(column_name='Equipment Condition', attribute='EQUIPMENT_CONDITION', widget=CharWidget())
    STATUS_EQUIPMENT = fields.Field(column_name='Status Equipment', attribute='STATUS_EQUIPMENT', widget=CharWidget())
    STATUS_EQUIPMENT_DISPOSED = fields.Field(column_name='Status Equipment Disposed', attribute='STATUS_EQUIPMENT_DISPOSED', widget=CharWidget())
    REFERENSI_NO_PDE = fields.Field(column_name='Referensi No PDE', attribute='REFERENSI_NO_PDE', widget=CharWidget())

    class Meta:
        model = AssetEquipment
        import_id_fields = ['CN_SAP']
        fields = (
            'No_Asset', 'CN_SAP', 'CN_ELLIPSE', 'EGI', 'TYPE', 'GROUP', 'CLASS_WEIGHT',
            'OWNERSHIP', 'SECTION', 'LOCATION', 'SUB_SITE', 'SUB_LOCATION', 'BRAND',
            'SN', 'HM_SMR', 'HM_DATE', 'SPO_EQUIPMENT', 'PERSENTASE_SPO',
            'EQUIPMENT_CONDITION', 'STATUS_EQUIPMENT', 'STATUS_EQUIPMENT_DISPOSED',
            'REFERENSI_NO_PDE',
        )
        export_order = fields
        skip_unchanged = True
        report_skipped = True


@admin.register(AssetEquipment, site=admin_site)
class AssetEquipmentAdmin(ImportExportModelAdmin):
    resource_class = AssetEquipmentResource

    list_display = (
        "CN_SAP", "No_Asset", "display_foto", 'EGI', 'TYPE', 'GROUP', 'CLASS_WEIGHT',
            'OWNERSHIP', 'SECTION', 'LOCATION', 'SUB_SITE', 'SUB_LOCATION', 'BRAND',
            'SN', 'HM_SMR', 'HM_DATE', 'SPO_EQUIPMENT', 'PERSENTASE_SPO',
            'EQUIPMENT_CONDITION', 'STATUS_EQUIPMENT', 'STATUS_EQUIPMENT_DISPOSED',
            'REFERENSI_NO_PDE', "LAST_UPDATED_MONTH", "LAST_UPDATED_YEAR", "UPDATED_AT",
    )
    search_fields = ("CN_SAP", "No_Asset", "REFERENSI_NO_PDE")
    list_filter = ("LOCATION", "EQUIPMENT_CONDITION", "LAST_UPDATED_YEAR", "LAST_UPDATED_MONTH")
    list_per_page = 5
    
    # Satukan semua field readonly ke dalam satu Tuple agar tidak saling menimpa
    readonly_fields = ('UPDATED_AT', 'LAST_UPDATED_MONTH', 'LAST_UPDATED_YEAR', 'preview_foto',)

    fieldsets = (
        (None, {
            'fields': (
                ('CN_SAP', 'No_Asset', 'CN_ELLIPSE'),
                'EGI', 'TYPE', 'GROUP', 'CLASS_WEIGHT',
            )
        }),
        ('Lampiran Foto Utama', {
            'fields': ('FOTO', 'preview_foto'),
        }),
        ('Detail Kepemilikan & Lokasi', {
            'fields': ('OWNERSHIP', 'SECTION', 'LOCATION', 'SUB_SITE', 'SUB_LOCATION'),
        }),
        ('Spesifikasi & Kondisi Teknis (Terakhir Diketahui)', {
            'fields': ('BRAND', 'SN', 'HM_SMR', 'HM_DATE', 'SPO_EQUIPMENT', 'PERSENTASE_SPO'),
        }),
        ('Status Disposal', {
            'fields': ('EQUIPMENT_CONDITION', 'STATUS_EQUIPMENT', 'STATUS_EQUIPMENT_DISPOSED', 'REFERENSI_NO_PDE'),
        }),
        ('Informasi Pembaruan Sistem', {
            'fields': ('LAST_UPDATED_MONTH', 'LAST_UPDATED_YEAR', 'UPDATED_AT'),
            'classes': ('collapse',),
        }),
    )

    def PERSENTASE_SPO_display(self, obj):
        try:
            if obj.PERSENTASE_SPO is not None:
                return f"{float(obj.PERSENTASE_SPO) * 100:.2f}%"
            return "-"
        except (ValueError, TypeError):
            return "-"
    PERSENTASE_SPO_display.short_description = "PERSENTASE SPO"

    actions = ['delete_selected']

    def display_foto(self, obj):
        if obj.FOTO:
            return format_html(
                '<img src="{}" style="max-height: 40px; width: auto; border-radius: 4px; border: 1px solid #ccc;" />', 
                obj.FOTO.url
            )
        return format_html('<span style="color: #999; font-style: italic;">Tidak ada foto</span>')
    display_foto.short_description = "Foto Aset"

    def preview_foto(self, obj):
        if obj.FOTO:
            return format_html(
                '<div style="max-width: 300px; padding: 10px; border: 1px dashed #e0e0e0; border-radius: 8px; background-color: #f9f9f9;">'
                '<img src="{}" style="max-width: 100%; height: auto; display: block; border-radius: 5px;" />'
                '</div>',
                obj.FOTO.url
            )
        return format_html('<span style="color: #999; font-style: italic;">Belum ada gambar yang diunggah</span>')
    preview_foto.short_description = "Pratinjau Gambar"

    # 🌟 FILTERING VIEW BERDASARKAN ROLE LOKASI & SECTION USER LOGIN
    def get_queryset(self, request):
        qs = super().get_queryset(request)
        
        # 1. Jika superuser / admin HO, buka akses penuh tanpa filter
        if request.user.is_superuser:
            return qs
            
        # 2. Ambil parameter lokasi dan section dari UserProfile secara taktis
        if hasattr(request.user, 'userprofile'):
            profile = request.user.userprofile
            user_site = profile.lokasi
            user_section = profile.section
            
            # Skenario A: Jika user punya aturan Lokasi DAN Section (Filter Paling Ketat)
            if user_site and user_section:
                return qs.filter(
                    LOCATION__iexact=user_site,
                    SECTION__iexact=user_section
                )
            
            # Skenario B: Jika user hanya di-set Lokasi-nya saja (Akses all section di site tersebut)
            if user_site:
                return qs.filter(LOCATION__iexact=user_site)

        # 3. Skenario Cadangan: Jika filter menggunakan Django Groups
        user_groups = request.user.groups.values_list('name', flat=True)
        if user_groups:
            return qs.filter(LOCATION__in=user_groups)

        return qs

    # 🌟 FILTERING EXPORT BERDASARKAN ROLE LOGIN USER (Tambahan Pengaman)
    def get_export_queryset(self, request):
        """Memastikan data yang diekspor ke Excel/CSV terkunci pada lokasi yang sama dengan view"""
        return self.get_queryset(request)

    def _is_atasan(self, user):
        if not user or user.is_superuser:
            return False
        try:
            profile = user.userprofile
            level = str(profile.jabatan_level).upper() if profile.jabatan_level else ''
            nama_resmi = str(profile.jabatan_nama_resmi).upper() if profile.jabatan_nama_resmi else ''
            keyword_atasan = ['SECTION HEAD', 'DEPARTMENT HEAD', 'CHIEF', 'MANAGER', 'GM', 'HEAD']
            if any(k in level or k in nama_resmi for k in keyword_atasan):
                return True
        except Exception:
            pass
        return False

    def has_add_permission(self, request):
        return request.user.is_superuser

    def has_import_permission(self, request):
        return request.user.is_superuser

    def has_export_permission(self, request):
        if request.user.is_superuser:
            return True
        if self._is_atasan(request.user):
            return False
        if hasattr(request.user, 'userprofile'):
            jabatan_level = str(getattr(request.user.userprofile, 'jabatan_level', '')).upper()
            if jabatan_level in ['SENIOR_OFFICER', 'OFFICER', 'SENIOR OFFICER']:
                return True
        return False


    def get_export_formats(self):
        return [CSV, XLSX, JSON]

    def get_actions(self, request):
        actions = super().get_actions(request)
        if 'export_admin_action' in actions:
            del actions['export_admin_action']
        return actions



# ===========================================================
# ======= RESOURCE UNTUK EXPORT IMPORT DATA =================
# ===========================================================
class AssetEquipmentDisposedResource(resources.ModelResource):
    def clean_PERSENTASE_SPO(self, value):
        if value is None or str(value).strip() == '':
            return None
        try:
            return float(str(value).replace(',', '.'))
        except ValueError:
            raise ValueError(f"'{value}' bukan angka yang valid untuk PERSENTASE_SPO.")

    No_Asset = fields.Field(column_name='No Asset', attribute='No_Asset', widget=CharWidget())
    CN_SAP = fields.Field(column_name='Code Number', attribute='CN_SAP', widget=CharWidget())
    CN_ELLIPSE = fields.Field(column_name='Code Number Ellipse', attribute='CN_ELLIPSE', widget=CharWidget())
    TYPE = fields.Field(column_name='Type', attribute='TYPE', widget=CharWidget())
    GROUP = fields.Field(column_name='Class Equipment', attribute='GROUP', widget=CharWidget())
    CLASS_WEIGHT = fields.Field(column_name='Class Weight', attribute='CLASS_WEIGHT', widget=CharWidget())
    OWNERSHIP = fields.Field(column_name='Ownership', attribute='OWNERSHIP', widget=CharWidget())
    SECTION = fields.Field(column_name='Section', attribute='SECTION', widget=CharWidget())
    LOCATION = fields.Field(column_name='Location', attribute='LOCATION', widget=CharWidget())
    SUB_SITE = fields.Field(column_name='Sub Site', attribute='SUB_SITE', widget=CharWidget())
    SUB_LOCATION = fields.Field(column_name='Sub Location', attribute='SUB_LOCATION', widget=CharWidget())
    BRAND = fields.Field(column_name='Brand', attribute='BRAND', widget=CharWidget())
    SN = fields.Field(column_name='Serial Number', attribute='SN', widget=CharWidget())
    HM_SMR = fields.Field(column_name='Hour Meter', attribute='HM_SMR', widget=CharWidget())
    HM_DATE = fields.Field(column_name='Hour Meter Date', attribute='HM_DATE', widget=DateWidget(format='%Y-%m-%d'))
    SPO_EQUIPMENT = fields.Field(column_name='SPO Equipment', attribute='SPO_EQUIPMENT', widget=IntegerWidget())
    PERSENTASE_SPO = fields.Field(column_name='% SPO Equipment', attribute='PERSENTASE_SPO', widget=CharWidget())
    EQUIPMENT_CONDITION = fields.Field(column_name='Equipment Condition', attribute='EQUIPMENT_CONDITION', widget=CharWidget())
    STATUS_EQUIPMENT = fields.Field(column_name='Status Equipment', attribute='STATUS_EQUIPMENT', widget=CharWidget())
    STATUS_EQUIPMENT_DISPOSED = fields.Field(column_name='Status Equipment Disposed', attribute='STATUS_EQUIPMENT_DISPOSED', widget=CharWidget())
    REFERENSI_NO_PDE = fields.Field(column_name='Referensi No PDE', attribute='REFERENSI_NO_PDE', widget=CharWidget())
    nbv_disposed = fields.Field(column_name='NBV', attribute='nbv_disposed', widget=DecimalWidget())

    class Meta:
        model = AssetEquipmentDisposed
        import_id_fields = ['CN_SAP']
        fields = (
            'No_Asset', 'CN_SAP', 'CN_ELLIPSE', 'EGI', 'TYPE', 'GROUP', 'CLASS_WEIGHT',
            'OWNERSHIP', 'SECTION', 'LOCATION', 'SUB_SITE', 'SUB_LOCATION', 'BRAND',
            'SN', 'HM_SMR', 'HM_DATE', 'SPO_EQUIPMENT', 'PERSENTASE_SPO',
            'EQUIPMENT_CONDITION', 'STATUS_EQUIPMENT', 'STATUS_EQUIPMENT_DISPOSED',
            'REFERENSI_NO_PDE', 'nbv_disposed',
        )
        export_order = fields
        skip_unchanged = True
        report_skipped = True


# ===========================================================
# ======= CLASS ADMIN PANEL EQUIPMENT DISPOSED ==============
# ===========================================================
@admin.register(AssetEquipmentDisposed, site=admin_site)
class AssetEquipmentDisposedAdmin(ImportExportModelAdmin):
    resource_class = AssetEquipmentDisposedResource
    actions = ['delete_selected'] 
    list_per_page = 5

    # ── TAMPILAN MATRIKS KOLOM UTAMA DI TABEL ADMIN ──────────────────
    list_display = (
        "asset_cn_sap", "No_Asset", "EGI","SN", "TYPE","SECTION", "LOCATION", "EQUIPMENT_CONDITION",
        "REFERENSI_NO_PDE", "nbv_disposed", 
        'status_foto_4_sisi', 'status_inspeksi_unit', 'status_rca',
        'status_pengajuan_disposed', 'status_lampiran_capex', 'status_pde', 'status_summary_pde',
        'progress_bar_dokumen', 'UPDATED_AT',"action_lampiran_capex",
    )
    search_fields = ("asset__CN_SAP", "EGI", "No_Asset", "REFERENSI_NO_PDE",)
    list_filter = ("SUB_LOCATION", "LAST_UPDATED_YEAR", "LAST_UPDATED_MONTH", "EGI", "LOCATION")

    readonly_fields = (
        'UPDATED_AT', 'LAST_UPDATED_MONTH', 'LAST_UPDATED_YEAR',
        'foto_4_sisi_uploaded_at', 'foto_4_sisi_uploaded_by',
        'inspeksi_unit_uploaded_at', 'inspeksi_unit_uploaded_by',
        'rca_uploaded_at', 'rca_uploaded_by',
        'pengajuan_disposed_uploaded_at', 'pengajuan_disposed_uploaded_by',
        'lampiran_capex_uploaded_at', 'lampiran_capex_uploaded_by',
        'pde_uploaded_at', 'pde_uploaded_by',
        'summary_pde_uploaded_at', 'summary_pde_uploaded_by',
    )

    class Media:
        js = (
            'js/forms/capex_lampiran.js',        # Eksisting Form Capex Anda
            'js/forms/quick_upload_disposed.js',  # Script Baru untuk RCA, PDE, dll
        )

    def get_queryset(self, request):
        qs = super().get_queryset(request).select_related('asset')
        qs = qs.filter(EQUIPMENT_CONDITION__iexact='DISPOSED')

        if request.user.is_superuser:
            return qs

        if not hasattr(request.user, 'userprofile'):
            return qs.none()
        try:
            profile = request.user.userprofile
            user_lokasi = profile.lokasi or ""
            user_section = profile.section or ""
        except Exception:
            return qs.none()

        if not user_lokasi:
            return qs.none()

        qs = qs.filter(LOCATION__iexact=user_lokasi)
        if user_section:
            qs = qs.filter(SECTION__iexact=user_section)
        return qs

    def save_model(self, request, obj, form, change):
        """Otomatis mendeteksi file baru yang diupload langsung pada baris data unit."""
        now = timezone.now()

        #ekstrak data pembanding unit dari object unit
        cn_sap = obj.asset.CN_SAP if obj.asset else ""
        serial_number = obj.SN or ""
        egi = obj.EGI or ""

        for field in AssetEquipmentDisposed.DOC_FIELDS:
            if field in form.changed_data:
                if getattr(obj, field):  
                    setattr(obj, f'{field}_uploaded_at', now)
                    setattr(obj, f'{field}_uploaded_by', request.user)

                else:  
                    setattr(obj, f'{field}_uploaded_at', None)
                    setattr(obj, f'{field}_uploaded_by', None)

        super().save_model(request, obj, form, change)
        # == eksekusi khusus untuk validasi dokumen rca
        # ✅ OCR dijalankan SETELAH save — file sudah tersimpan, URL tersedia
        if 'rca' in form.changed_data and obj.rca:
            try:
                from .utils_ocr import verifikasi_dokumen_rca

                # ✅ Gunakan URL Cloudinary (bukan .path)
                file_source   = obj.rca.url
                cn_sap        = obj.asset.CN_SAP if obj.asset else ""
                egi           = obj.EGI or ""
                serial_number = obj.SN or ""

                is_valid, ocr_message = verifikasi_dokumen_rca(
                    file_source, cn_sap, egi, serial_number
                )

                if is_valid:
                    self.message_user(
                        request,
                        f"✅ OCR Sukses ({cn_sap}): {ocr_message}",
                        messages.SUCCESS,
                    )
                else:
                    self.message_user(
                        request,
                        f"⚠️ Peringatan OCR RCA ({cn_sap}): {ocr_message}",
                        messages.WARNING,
                    )
            except Exception as ocr_err:
                self.message_user(
                    request,
                    f"⚠️ OCR tidak dapat dijalankan: {str(ocr_err)}",
                    messages.WARNING,
                )
                
                        
      

    fieldsets = (
        (None, {
            'fields': (
                ('No_Asset', 'CN_ELLIPSE'),
                'EGI', 'TYPE', 'GROUP', 'CLASS_WEIGHT',
            )
        }),
        ('Detail Kepemilikan & Lokasi', {
            'fields': ('OWNERSHIP', 'SECTION', 'LOCATION', 'SUB_SITE', 'SUB_LOCATION'),
        }),
        ('Spesifikasi & Kondisi Teknis', {
            'fields': ('BRAND', 'SN', 'HM_SMR', 'HM_DATE', 'SPO_EQUIPMENT', 'PERSENTASE_SPO'),
        }),
        ('Status Disposal & Finansial', {
            'fields': ('EQUIPMENT_CONDITION', 'STATUS_EQUIPMENT', 'STATUS_EQUIPMENT_DISPOSED', 'REFERENSI_NO_PDE', 'nbv_disposed'),
        }),
        ('📂 Upload Digital Dokumen Lampiran Disposal', {
            'fields': (
                'foto_4_sisi', ('foto_4_sisi_uploaded_at', 'foto_4_sisi_uploaded_by'),
                'inspeksi_unit', ('inspeksi_unit_uploaded_at', 'inspeksi_unit_uploaded_by'),
                'rca', ('rca_uploaded_at', 'rca_uploaded_by'),
                'pengajuan_disposed', ('pengajuan_disposed_uploaded_at', 'pengajuan_disposed_uploaded_by'),
                'lampiran_capex', ('lampiran_capex_uploaded_at', 'lampiran_capex_uploaded_by'),
                'pde', ('pde_uploaded_at', 'pde_uploaded_by'),
                'summary_pde', ('summary_pde_uploaded_at', 'summary_pde_uploaded_by'),
            ),
        }),
        ('Informasi Pembaruan Sistem', {
            'fields': ('LAST_UPDATED_MONTH', 'LAST_UPDATED_YEAR', 'UPDATED_AT'),
            'classes': ('collapse',),
        }),
    )

    # ── 🌟 REVISI UTAMA: GENERATOR TOMBOL UPLOAD & BADGE STATUS ──
    # admin.py (Di dalam class AssetEquipmentDisposedAdmin)
    def _document_action_cell(self, obj, field_name, label_name):
        """
        Helper dinamis untuk menghasilkan tombol Upload/Lihat berdampingan dengan badge progress.
        Sekarang menampilkan tanggal upload di bawah badge Complete pada kolom yang sama.
        """
        cn_sap = obj.asset.CN_SAP if obj.asset else ''
        file_obj = getattr(obj, field_name, None)

        if file_obj:
            # 1. Ambil data datetime kapan file diupload
            uploaded_at = getattr(obj, f'{field_name}_uploaded_at', None)
            
            # 2. Format tanggal menjadi string (Contoh: 30/06/2026 14:52)
            # Jika jam tidak diperlukan, ganti formatnya menjadi '%d/%m/%Y' saja
            if uploaded_at:
                local_time = timezone.localtime(uploaded_at)
                date_str = local_time.strftime('%d/%m/%Y %H:%M')
            else:
                date_str = '-'

            # ── KONDISI COMPLETE: Kita sediakan tombol Lihat, Ganti, dan Hapus ──
            return format_html(
                '<div style="display:flex; flex-direction:column; gap:4px; min-width:140px;">'
                    # Baris Atas: Tombol Utama
                    '<div style="display:flex; align-items:center; gap:4px; white-space:nowrap;">'
                        '<a href="{url}" target="_blank" class="button" style="background:#28a745; color:white; padding:3px 6px; border-radius:4px; font-size:10px; text-decoration:none; font-weight:600;">✓ Lihat</a>'
                        '<button onclick="event.preventDefault(); event.stopPropagation(); openUploadModal(\'{cn_sap}\', \'{field_name}\', \'{label_name}\');" '
                        'style="background:#ffc107; color:#212529; border:none; padding:3px 6px; border-radius:4px; font-size:10px; font-weight:600; cursor:pointer;">✏️ Ganti</button>'
                        '<button onclick="event.preventDefault(); event.stopPropagation(); deleteDocument(\'{cn_sap}\', \'{field_name}\', \'{label_name}\');" '
                        'style="background:#dc3545; color:white; border:none; padding:3px 6px; border-radius:4px; font-size:10px; font-weight:600; cursor:pointer;">🗑️</button>'
                    '</div>'
                    # Baris Bawah: Badge Info Status & Tanggal
                    '<div style="display:flex; align-items:center; gap:6px;">'
                        '<span style="background:#d4edda; color:#155724; padding:1px 4px; border-radius:3px; font-size:9px; font-weight:bold;">Complete</span>'
                        '<span style="font-size:9px; color:#6c757d; font-family:monospace;">📅 {date}</span>'
                    '</div>'
                '</div>',
                url=file_obj.url,
                date=date_str,
                cn_sap=cn_sap,
                field_name=field_name,
                label_name=label_name
            )
        else:
            # ── KONDISI PROGRESS (KOSONG): Tetap tampilkan tombol Upload awal ──
            return format_html(
                '<div style="display:flex; align-items:center; gap:6px; white-space:nowrap;">'
                '<button onclick="event.preventDefault(); event.stopPropagation(); openUploadModal(\'{cn_sap}\', \'{field_name}\', \'{label_name}\');" '
                'style="background:#1883ff; color:white; border:none; padding:4px 8px; border-radius:4px; font-size:11px; font-weight:600; cursor:pointer;">📤 Upload</button>'
                '<span style="background:#fff3cd; color:#856404; padding:3px 6px; border-radius:4px; font-size:10px; font-weight:bold;">Prog</span>'
                '</div>',
                cn_sap=cn_sap, field_name=field_name, label_name=label_name
            )

    
    def status_foto_4_sisi(self, obj): 
        return self._document_action_cell(obj, 'foto_4_sisi', 'Foto 4 Sisi')
    status_foto_4_sisi.short_description = "Foto 4 Sisi"

    def status_inspeksi_unit(self, obj): 
        return self._document_action_cell(obj, 'inspeksi_unit', 'Inspeksi Unit')
    status_inspeksi_unit.short_description = "Inspeksi"

    def status_rca(self, obj): 
        return self._document_action_cell(obj, 'rca', 'RCA')
    status_rca.short_description = "RCA"

    def status_pengajuan_disposed(self, obj): 
        return self._document_action_cell(obj, 'pengajuan_disposed', 'Pengajuan Disposed')
    status_pengajuan_disposed.short_description = "Pengajuan"

    def status_lampiran_capex(self, obj): 
        return self._document_action_cell(obj, 'lampiran_capex', 'Lampiran Capex')
    status_lampiran_capex.short_description = "Capex"

    def status_pde(self, obj): 
        return self._document_action_cell(obj, 'pde', 'PDE')
    status_pde.short_description = "PDE"

    def status_summary_pde(self, obj): 
        return self._document_action_cell(obj, 'summary_pde', 'Summary PDE')
    status_summary_pde.short_description = "Sum PDE"

    # ── PROGRESS BAR & INTEGRASI LAINNYA ─────────────────────────────
    def progress_bar_dokumen(self, obj):
        pct = obj.persentase_complete
        done = obj.jumlah_complete
        total = obj.total_dokumen
        color = '#28a745' if pct == 100 else ('#ffc107' if pct >= 50 else '#dc3545')
        return format_html(
            '<div style="width:100px;background:#f0f0f0;border-radius:10px;overflow:hidden;margin-bottom:2px;">'
            '<div style="width:{}%;background:{};height:10px;border-radius:10px;"></div></div>'
            '<span style="font-size:11px;color:{};font-weight:600;">{}/{} ({}%)</span>',
            pct, color, color, done, total, pct
        )
    progress_bar_dokumen.short_description = "Progress Dokumen"

    def asset_cn_sap(self, obj):
        return obj.asset.CN_SAP if obj.asset else '-'
    asset_cn_sap.short_description = "CN SAP"
    asset_cn_sap.admin_order_field = "asset__CN_SAP"

    def action_lampiran_capex(self, obj):
        cn_sap = obj.asset.CN_SAP if obj.asset else ''
        existing = FormLampiranCapex.objects.filter(CN_SAP=cn_sap).first()

        if existing:
            url = reverse('form:lampiran_capex_detail', args=[existing.pk])
            status_colors = {'DRAFT': '#888', 'SUB': '#1883ff', 'APR1': '#f57c00', 'APR2': '#9c27b0', 'FIN': '#28a745', 'REJ': '#dc3545'}
            color = status_colors.get(existing.status, '#888')

            return format_html(
                '<div style="display:flex;flex-direction:column;align-items:center;gap:4px;">'
                '<a href="{url}" style="display:inline-block;padding:5px 12px;background:#f0f9f0;color:#28a745;'
                'border:1.5px solid #28a745;border-radius:6px;font-size:11px;font-weight:600;text-decoration:none;white-space:nowrap;">'
                '📄 Lihat Form</a><span style="font-size:10px;color:{color};font-weight:600;">● {status}</span></div>',
                url=url, color=color, status=existing.get_status_display()
            )
        else:
            return format_html(
                '<button onclick="event.preventDefault(); event.stopPropagation(); openCapexModal(\'{cn_sap}\');" '
                'style="padding:5px 12px;background:#1883ff;color:white;border:none;border-radius:6px;'
                'font-size:11px;font-weight:600;cursor:pointer;white-space:nowrap;">📋 Create Form</button>',
                cn_sap=cn_sap
            )
    action_lampiran_capex.short_description = "Form Capex"

    def get_urls(self):
        urls = super().get_urls()
        custom_urls = [
            path('lampiran-capex/<int:capex_id>/pdf/', self.admin_site.admin_view(self.cetak_capex_pdf_view), name='asset_equipment_disposed_capex_pdf'),
        ]
        return custom_urls + urls

    def cetak_capex_pdf_view(self, request, capex_id):
        capex = get_object_or_404(FormLampiranCapex, id=capex_id)
        context = {'capex': capex, 'waktu_cetak': datetime.now().strftime('%d-%m-%Y %H:%M')}
        html_string = render_to_string('modal_capex_disposed.html', context)
        response = HttpResponse(content_type='application/pdf')
        response['Content-Disposition'] = f'inline; filename="Lampiran_CAPEX_{capex.CN_SAP}.pdf"'
        pisa_status = pisa.CreatePDF(html_string, dest=response)
        if pisa_status.err:
            return HttpResponse('Gagal membuat dokumen PDF', status=500)
        return response

   

    def get_import_resource_kwargs(self, request, *args, **kwargs):
        kwargs = super().get_import_resource_kwargs(request, *args, **kwargs)
        kwargs.update({'request': request})
        return kwargs

    def _is_atasan(self, user):
        if not user or user.is_superuser:
            return False
        try:
            profile = user.userprofile
            level = str(profile.jabatan_level).upper() if profile.jabatan_level else ''
            nama_resmi = str(profile.jabatan_nama_resmi).upper() if profile.jabatan_nama_resmi else ''
            keyword_atasan = ['SECTION HEAD', 'DEPARTMENT HEAD', 'CHIEF', 'MANAGER', 'GM', 'HEAD']
            if any(k in level or k in nama_resmi for k in keyword_atasan):
                return True
        except Exception:
            pass
        return False

    def has_add_permission(self, request):
        return request.user.is_superuser

    def has_import_permission(self, request):
        return request.user.is_superuser

    def has_export_permission(self, request):
        if request.user.is_superuser:
            return True
        if self._is_atasan(request.user):
            return False
        if hasattr(request.user, 'userprofile'):
            jabatan_level = str(getattr(request.user.userprofile, 'jabatan_level', '')).upper()
            if jabatan_level in ['SENIOR_OFFICER', 'OFFICER', 'SENIOR OFFICER']:
                return True
        return False

    def get_export_formats(self):
        return [CSV, XLSX, JSON]

    def get_actions(self, request):
        actions = super().get_actions(request)
        if 'export_admin_action' in actions:
            del actions['export_admin_action']
        return actions
 




    
#-----------------------------------------------------------
#===========================================================
# =======Class untuk Equipment Standby ====================
#===========================================================
# ---------------------------------------------------------- 

class AssetEquipmentStandbyResource(resources.ModelResource):
    def clean_PERSENTASE_SPO(self, value):
        if value is None or str(value).strip() == '':
            return None
        try:
            return float(str(value).replace(',', '.'))
        except ValueError:
            raise ValueError(f"'{value}' bukan angka yang valid untuk PERSENTASE_SPO.")

    No_Asset = fields.Field(column_name='No Asset', attribute='No_Asset', widget=CharWidget())
    CN_SAP = fields.Field(column_name='Code Number', attribute='CN_SAP', widget=CharWidget())
    CN_ELLIPSE = fields.Field(column_name='Code Number Ellipse', attribute='CN_ELLIPSE', widget=CharWidget())
    TYPE = fields.Field(column_name='Type', attribute='TYPE', widget=CharWidget())
    GROUP = fields.Field(column_name='Class Equipment', attribute='GROUP', widget=CharWidget())
    CLASS_WEIGHT = fields.Field(column_name='Class Weight', attribute='CLASS_WEIGHT', widget=CharWidget())
    OWNERSHIP = fields.Field(column_name='Ownership', attribute='OWNERSHIP', widget=CharWidget())
    SECTION = fields.Field(column_name='Section', attribute='SECTION', widget=CharWidget())
    LOCATION = fields.Field(column_name='Location', attribute='LOCATION', widget=CharWidget())
    SUB_SITE = fields.Field(column_name='Sub Site', attribute='SUB_SITE', widget=CharWidget())
    SUB_LOCATION = fields.Field(column_name='Sub Location', attribute='SUB_LOCATION', widget=CharWidget())
    BRAND = fields.Field(column_name='Brand', attribute='BRAND', widget=CharWidget())
    SN = fields.Field(column_name='Serial Number', attribute='SN', widget=CharWidget())
    HM_SMR = fields.Field(column_name='Hour Meter', attribute='HM_SMR', widget=CharWidget())
    HM_DATE = fields.Field(column_name='Hour Meter Date', attribute='HM_DATE', widget=DateWidget(format='%Y-%m-%d'))
    SPO_EQUIPMENT = fields.Field(column_name='SPO Equipment', attribute='SPO_EQUIPMENT', widget=IntegerWidget())
    PERSENTASE_SPO = fields.Field(column_name='% SPO Equipment', attribute='PERSENTASE_SPO', widget=CharWidget())
    EQUIPMENT_CONDITION = fields.Field(column_name='Equipment Condition', attribute='EQUIPMENT_CONDITION', widget=CharWidget())
    STATUS_EQUIPMENT = fields.Field(column_name='Status Equipment', attribute='STATUS_EQUIPMENT', widget=CharWidget())
    STATUS_EQUIPMENT_DISPOSED = fields.Field(column_name='Status Equipment Disposed', attribute='STATUS_EQUIPMENT_DISPOSED', widget=CharWidget())
    REFERENSI_NO_PDE = fields.Field(column_name='Referensi No PDE', attribute='REFERENSI_NO_PDE', widget=CharWidget())
    nbv_disposed  = fields.Field(column_name='NBV', attribute='nbv_disposed', widget=DecimalWidget())

    class Meta:
        model = AssetEquipmentStandby
        import_id_fields = ['CN_SAP']
        fields = (
            'No_Asset', 'CN_SAP', 'CN_ELLIPSE', 'EGI', 'TYPE', 'GROUP', 'CLASS_WEIGHT',
            'OWNERSHIP', 'SECTION', 'LOCATION', 'SUB_SITE', 'SUB_LOCATION', 'BRAND',
            'SN', 'HM_SMR', 'HM_DATE', 'SPO_EQUIPMENT', 'PERSENTASE_SPO',
            'EQUIPMENT_CONDITION', 'STATUS_EQUIPMENT', 'STATUS_EQUIPMENT_DISPOSED',
            'REFERENSI_NO_PDE','nbv_disposed',

        )
        export_order = fields
        skip_unchanged = True
        report_skipped = True




@admin.register(AssetEquipmentStandby, site=admin_site)
class AssetEquipmentStandbyAdmin(ImportExportModelAdmin):
    resource_class = AssetEquipmentStandbyResource

    # ✅ LIST DISPLAY: Tetap dipertahankan sesuai struktur Bapak
    list_display = (
        "asset_cn_sap", "No_Asset", "EGI", "TYPE", "GROUP", "LOCATION", "SUB_SITE","SUB_LOCATION","EQUIPMENT_CONDITION",
        "REFERENSI_NO_PDE","nbv_disposed","ba_standby_cell","LAST_UPDATED_MONTH", "LAST_UPDATED_YEAR","UPDATED_AT",
    )
    search_fields = ("asset__CN_SAP", "No_Asset", "REFERENSI_NO_PDE")
    list_filter = ("SUB_LOCATION", "LAST_UPDATED_YEAR", "LAST_UPDATED_MONTH")
    list_per_page = 5
    readonly_fields = ('UPDATED_AT', 'LAST_UPDATED_MONTH', 'LAST_UPDATED_YEAR',)

    # ✅ FILTER QUERYSET BERDASARKAN KONDISI STANDBY
    def get_queryset(self, request):
        qs = super().get_queryset(request)
        qs = qs.filter(EQUIPMENT_CONDITION__iexact='STANDBY')

        if request.user.is_superuser:
            return qs

        if not hasattr(request.user, 'userprofile'):
            return qs.none()
        try:
            profile      = request.user.userprofile
            user_lokasi  = profile.lokasi or ""
            user_section = profile.section or ""
        except Exception:
            return qs.none()

        if not user_lokasi:
            return qs.none()

        qs = qs.filter(LOCATION__iexact=user_lokasi)
        if user_section:
            qs = qs.filter(SECTION__iexact=user_section)
        return qs

    def get_import_resource_kwargs(self, request, *args, **kwargs):
        kwargs = super().get_import_resource_kwargs(request, *args, **kwargs)
        kwargs.update({'request': request})
        return kwargs
    
    # ── 🌟 CELL GENERATOR REVISI (DILOKALISASI KE STANDBY) ──
    def _document_action_cell(self, obj, field_name, label_name):
        cn_sap = obj.asset.CN_SAP if obj.asset else ''
        file_obj = getattr(obj, field_name, None)

        if file_obj:
            uploaded_at = getattr(obj, f'{field_name}_uploaded_at', None)
            if uploaded_at:
                local_time = timezone.localtime(uploaded_at)
                date_str = local_time.strftime('%d/%m/%Y %H:%M')
            else:
                date_str = '-'

            return format_html(
                '<div style="display:flex; flex-direction:column; gap:4px; min-width:140px;">'
                    '<div style="display:flex; align-items:center; gap:4px; white-space:nowrap;">'
                        '<a href="{url}" target="_blank" class="button" style="background:#28a745; color:white; padding:3px 6px; border-radius:4px; font-size:10px; text-decoration:none; font-weight:600;">✓ Lihat</a>'
                        '<button onclick="event.preventDefault(); event.stopPropagation(); openUploadModal(\'{cn_sap}\', \'{field_name}\', \'{label_name}\');" '
                        'style="background:#ffc107; color:#212529; border:none; padding:3px 6px; border-radius:4px; font-size:10px; font-weight:600; cursor:pointer;">✏️ Ganti</button>'
                        '<button onclick="event.preventDefault(); event.stopPropagation(); deleteDocument(\'{cn_sap}\', \'{field_name}\', \'{label_name}\');" '
                        'style="background:#dc3545; color:white; border:none; padding:3px 6px; border-radius:4px; font-size:10px; font-weight:600; cursor:pointer;">🗑️</button>'
                    '</div>'
                    '<div style="display:flex; align-items:center; gap:6px;">'
                        '<span style="background:#d4edda; color:#155724; padding:1px 4px; border-radius:3px; font-size:9px; font-weight:bold;">Complete</span>'
                        '<span style="font-size:9px; color:#6c757d; font-family:monospace;">📅 {date}</span>'
                    '</div>'
                '</div>',
                url=file_obj.url, date=date_str, cn_sap=cn_sap, field_name=field_name, label_name=label_name
            )
        else:
            return format_html(
                '<div style="display:flex; align-items:center; gap:6px; white-space:nowrap;">'
                '<button onclick="event.preventDefault(); event.stopPropagation(); openUploadModal(\'{cn_sap}\', \'{field_name}\', \'{label_name}\');" '
                'style="background:#1883ff; color:white; border:none; padding:4px 8px; border-radius:4px; font-size:11px; font-weight:600; cursor:pointer;">📤 Upload</button>'
                '<span style="background:#fff3cd; color:#856404; padding:3px 6px; border-radius:4px; font-size:10px; font-weight:bold;">Prog</span>'
                '</div>',
                cn_sap=cn_sap, field_name=field_name, label_name=label_name
            )

    def ba_standby_cell(self, obj):
        return self._document_action_cell(obj, 'ba_standby', 'BA Standby')
    ba_standby_cell.short_description = 'BA Standby'

      

    def changelist_view(self, request, extra_context=None):
        extra_context = extra_context or {}
        return super().changelist_view(request, extra_context=extra_context)

    def asset_cn_sap(self, obj):
        return obj.asset.CN_SAP if obj.asset else '-'
    asset_cn_sap.short_description = "CN SAP"
    asset_cn_sap.admin_order_field = "asset__CN_SAP"

    
    fieldsets = (
        (None, {'fields': (('No_Asset', 'CN_ELLIPSE'), 'EGI', 'TYPE', 'GROUP', 'CLASS_WEIGHT',)}),
        ('Detail Kepemilikan & Lokasi', {'fields': ('OWNERSHIP', 'SECTION', 'LOCATION', 'SUB_SITE', 'SUB_LOCATION'),}),
        ('Spesifikasi & Kondisi Teknis (Terakhir Diketahui)', {'fields': ('BRAND', 'SN', 'HM_SMR', 'HM_DATE', 'SPO_EQUIPMENT', 'PERSENTASE_SPO'),}),
        ('Status Disposal', {'fields': ('EQUIPMENT_CONDITION', 'STATUS_EQUIPMENT', 'STATUS_EQUIPMENT_DISPOSED', 'REFERENSI_NO_PDE','nbv_disposed'),}),
        ('Informasi Pembaruan Sistem', {'fields': ('LAST_UPDATED_MONTH', 'LAST_UPDATED_YEAR', 'UPDATED_AT'), 'classes': ('collapse',),}),
    )

    def _is_atasan(self, user):
        if not user or user.is_superuser:
            return False
        try:
            profile = user.userprofile
            level = str(profile.jabatan_level).upper() if profile.jabatan_level else ''
            nama_resmi = str(profile.jabatan_nama_resmi).upper() if profile.jabatan_nama_resmi else ''
            keyword_atasan = ['SECTION HEAD', 'DEPARTMENT HEAD', 'CHIEF', 'MANAGER', 'GM', 'HEAD']
            if any(k in level or k in nama_resmi for k in keyword_atasan):
                return True
        except Exception:
            pass
        return False

    def has_add_permission(self, request):
        return request.user.is_superuser

    def has_import_permission(self, request):
        return request.user.is_superuser

    def has_export_permission(self, request):
        if request.user.is_superuser:
            return True
        if self._is_atasan(request.user):
            return False
        if hasattr(request.user, 'userprofile'):
            jabatan_level = str(getattr(request.user.userprofile, 'jabatan_level', '')).upper()
            if jabatan_level in ['SENIOR_OFFICER', 'OFFICER', 'SENIOR OFFICER']:
                return True
        return False

    def get_export_formats(self): return [CSV, XLSX, JSON]

    def get_actions(self, request):
        actions = super().get_actions(request)
        if 'export_admin_action' in actions: del actions['export_admin_action']
        return actions

    def PERSENTASE_SPO_display(self, obj):
        try:
            if obj.PERSENTASE_SPO is not None: return f"{float(obj.PERSENTASE_SPO) * 100:.2f}%"
            return "-"
        except (ValueError, TypeError): return "-"
    PERSENTASE_SPO_display.short_description = "PERSENTASE SPO"

    actions = ['delete_selected']

    # 🌟 TAMBAHAN UTAMA: CLASS MEDIA UNTUK LOAD JAVASCRIPT ASSET MANAGEMENT 🌟
    class Media:
        js = (
            'js/forms/quick_upload_disposed.js',
        )



#-----------------------------------------------------------
#===========================================================
# =======Class untuk Equipment Breakdown ====================
#===========================================================
# ---------------------------------------------------------- 

class AssetEquipmentBreakdownResource(resources.ModelResource):
    def clean_PERSENTASE_SPO(self, value):
        if value is None or str(value).strip() == '':
            return None
        try:
            return float(str(value).replace(',', '.'))
        except ValueError:
            raise ValueError(f"'{value}' bukan angka yang valid untuk PERSENTASE_SPO.")

    No_Asset = fields.Field(column_name='No Asset', attribute='No_Asset', widget=CharWidget())
    CN_SAP = fields.Field(column_name='Code Number', attribute='CN_SAP', widget=CharWidget())
    CN_ELLIPSE = fields.Field(column_name='Code Number Ellipse', attribute='CN_ELLIPSE', widget=CharWidget())
    TYPE = fields.Field(column_name='Type', attribute='TYPE', widget=CharWidget())
    GROUP = fields.Field(column_name='Class Equipment', attribute='GROUP', widget=CharWidget())
    CLASS_WEIGHT = fields.Field(column_name='Class Weight', attribute='CLASS_WEIGHT', widget=CharWidget())
    OWNERSHIP = fields.Field(column_name='Ownership', attribute='OWNERSHIP', widget=CharWidget())
    SECTION = fields.Field(column_name='Section', attribute='SECTION', widget=CharWidget())
    LOCATION = fields.Field(column_name='Location', attribute='LOCATION', widget=CharWidget())
    SUB_SITE = fields.Field(column_name='Sub Site', attribute='SUB_SITE', widget=CharWidget())
    SUB_LOCATION = fields.Field(column_name='Sub Location', attribute='SUB_LOCATION', widget=CharWidget())
    BRAND = fields.Field(column_name='Brand', attribute='BRAND', widget=CharWidget())
    SN = fields.Field(column_name='Serial Number', attribute='SN', widget=CharWidget())
    HM_SMR = fields.Field(column_name='Hour Meter', attribute='HM_SMR', widget=CharWidget())
    HM_DATE = fields.Field(column_name='Hour Meter Date', attribute='HM_DATE', widget=DateWidget(format='%Y-%m-%d'))
    SPO_EQUIPMENT = fields.Field(column_name='SPO Equipment', attribute='SPO_EQUIPMENT', widget=IntegerWidget())
    PERSENTASE_SPO = fields.Field(column_name='% SPO Equipment', attribute='PERSENTASE_SPO', widget=CharWidget())
    EQUIPMENT_CONDITION = fields.Field(column_name='Equipment Condition', attribute='EQUIPMENT_CONDITION', widget=CharWidget())
    STATUS_EQUIPMENT = fields.Field(column_name='Status Equipment', attribute='STATUS_EQUIPMENT', widget=CharWidget())
    STATUS_EQUIPMENT_DISPOSED = fields.Field(column_name='Status Equipment Disposed', attribute='STATUS_EQUIPMENT_DISPOSED', widget=CharWidget())
    REFERENSI_NO_PDE = fields.Field(column_name='Referensi No PDE', attribute='REFERENSI_NO_PDE', widget=CharWidget())
    nbv_disposed  = fields.Field(column_name='NBV', attribute='nbv_disposed', widget=DecimalWidget())

    class Meta:
        model = AssetEquipmentBreakdown
        import_id_fields = ['CN_SAP']
        fields = (
            'No_Asset', 'CN_SAP', 'CN_ELLIPSE', 'EGI', 'TYPE', 'GROUP', 'CLASS_WEIGHT',
            'OWNERSHIP', 'SECTION', 'LOCATION', 'SUB_SITE', 'SUB_LOCATION', 'BRAND',
            'SN', 'HM_SMR', 'HM_DATE', 'SPO_EQUIPMENT', 'PERSENTASE_SPO',
            'EQUIPMENT_CONDITION', 'STATUS_EQUIPMENT', 'STATUS_EQUIPMENT_DISPOSED',
            'REFERENSI_NO_PDE','nbv_disposed',

        )
        export_order = fields
        skip_unchanged = True
        report_skipped = True



@admin.register(AssetEquipmentBreakdown, site=admin_site)
class AssetEquipmentBreakdownAdmin(ImportExportModelAdmin):
    resource_class = AssetEquipmentBreakdownResource

    # ✅ TETAP SAMA
    list_display = (
        "asset_cn_sap", "No_Asset", "EGI", "TYPE", "GROUP", "LOCATION", "SUB_SITE","SUB_LOCATION","EQUIPMENT_CONDITION",
        "REFERENSI_NO_PDE","nbv_disposed","LAST_UPDATED_MONTH", "LAST_UPDATED_YEAR", "UPDATED_AT",'ba_breakdown_cell',"action_lampiran_capex",
    )
    search_fields = ("asset__CN_SAP", "No_Asset", "REFERENSI_NO_PDE")
    list_filter = ("SUB_LOCATION", "LAST_UPDATED_YEAR", "LAST_UPDATED_MONTH")
    list_per_page = 5
    readonly_fields = ('UPDATED_AT', 'LAST_UPDATED_MONTH', 'LAST_UPDATED_YEAR',)

    def get_queryset(self, request):
        qs = super().get_queryset(request)
        qs = qs.filter(EQUIPMENT_CONDITION__iexact='BREAKDOWN')

        if request.user.is_superuser:
            return qs

        if not hasattr(request.user, 'userprofile'):
            return qs.none()
        try:
            profile      = request.user.userprofile
            user_lokasi  = profile.lokasi or ""
            user_section = profile.section or ""
        except Exception:
            return qs.none()

        if not user_lokasi:
            return qs.none()

        qs = qs.filter(LOCATION__iexact=user_lokasi)
        if user_section:
            qs = qs.filter(SECTION__iexact=user_section)
        return qs

    def get_import_resource_kwargs(self, request, *args, **kwargs):
        kwargs = super().get_import_resource_kwargs(request, *args, **kwargs)
        kwargs.update({'request': request})
        return kwargs

    # ── 🌟 CELL GENERATOR DILOKALISASI KE BREAKDOWN ADMIN ──
    def _document_action_cell(self, obj, field_name, label_name):
        cn_sap = obj.asset.CN_SAP if obj.asset else ''
        file_obj = getattr(obj, field_name, None)

        if file_obj:
            uploaded_at = getattr(obj, f'{field_name}_uploaded_at', None)
            if uploaded_at:
                local_time = timezone.localtime(uploaded_at)
                date_str = local_time.strftime('%d/%m/%Y %H:%M')
            else:
                date_str = '-'

            return format_html(
                '<div style="display:flex; flex-direction:column; gap:4px; min-width:140px;">'
                    '<div style="display:flex; align-items:center; gap:4px; white-space:nowrap;">'
                        '<a href="{url}" target="_blank" class="button" style="background:#28a745; color:white; padding:3px 6px; border-radius:4px; font-size:10px; text-decoration:none; font-weight:600;">✓ Lihat</a>'
                        '<button onclick="event.preventDefault(); event.stopPropagation(); openUploadModal(\'{cn_sap}\', \'{field_name}\', \'{label_name}\');" '
                        'style="background:#ffc107; color:#212529; border:none; padding:3px 6px; border-radius:4px; font-size:10px; font-weight:600; cursor:pointer;">✏️ Ganti</button>'
                        '<button onclick="event.preventDefault(); event.stopPropagation(); deleteDocument(\'{cn_sap}\', \'{field_name}\', \'{label_name}\');" '
                        'style="background:#dc3545; color:white; border:none; padding:3px 6px; border-radius:4px; font-size:10px; font-weight:600; cursor:pointer;">🗑️</button>'
                    '</div>'
                    '<div style="display:flex; align-items:center; gap:6px;">'
                        '<span style="background:#d4edda; color:#155724; padding:1px 4px; border-radius:3px; font-size:9px; font-weight:bold;">Complete</span>'
                        '<span style="font-size:9px; color:#6c757d; font-family:monospace;">📅 {date}</span>'
                    '</div>'
                '</div>',
                url=file_obj.url,
                date=date_str,
                cn_sap=cn_sap,
                field_name=field_name,
                label_name=label_name
            )
        else:
            return format_html(
                '<div style="display:flex; align-items:center; gap:6px; white-space:nowrap;">'
                '<button onclick="event.preventDefault(); event.stopPropagation(); openUploadModal(\'{cn_sap}\', \'{field_name}\', \'{label_name}\');" '
                'style="background:#1883ff; color:white; border:none; padding:4px 8px; border-radius:4px; font-size:11px; font-weight:600; cursor:pointer;">📤 Upload</button>'
                '<span style="background:#fff3cd; color:#856404; padding:3px 6px; border-radius:4px; font-size:10px; font-weight:bold;">Prog</span>'
                '</div>',
                cn_sap=cn_sap, field_name=field_name, label_name=label_name
            )

    def ba_breakdown_cell(self, obj):
        return self._document_action_cell(obj, 'ba_breakdown', 'BA Breakdown')
    ba_breakdown_cell.short_description = 'BA Breakdown'

    # kunci otomatis save user upload dokumen
    # ✅ Perbaikan nama fungsi: save_model
    def save_model(self, request, obj, form, change):
        """
        Fungsi ini otomatis berjalan saat user menekan tombol save / upload.
        """
        # ✅ Perbaikan nama field: updated_by
        obj.updated_by = request.user 
        super().save_model(request, obj, form, change)

    def get_urls(self):
        urls = super().get_urls()
        custom_urls = [
            path(
                'lampiran-capex/<int:capex_id>/pdf/',
                self.admin_site.admin_view(self.cetak_capex_pdf_view),
                name='asset_equipment_breakdown_capex_pdf'
            ),
        ]
        return custom_urls + urls

    def cetak_capex_pdf_view(self, request, capex_id):
        capex = get_object_or_404(FormLampiranCapex, id=capex_id)
        context = {
            'capex': capex,
            'waktu_cetak': timezone.now().strftime('%d-%m-%Y %H:%M'),
        }
        html_string = render_to_string('modal_capex_disposed.html', context)
        response = HttpResponse(content_type='application/pdf')
        response['Content-Disposition'] = f'inline; filename="Lampiran_CAPEX_{capex.CN_SAP}.pdf"'
        pisa_status = pisa.CreatePDF(html_string, dest=response)
        if pisa_status.err:
            return HttpResponse('Gagal membuat dokumen PDF', status=500)
        return response

    changelist_template = "modal_capex_disposed.html"

    def changelist_view(self, request, extra_context=None):
        extra_context = extra_context or {}
        return super().changelist_view(request, extra_context=extra_context)

    def asset_cn_sap(self, obj):
        return obj.asset.CN_SAP if obj.asset else '-'
    asset_cn_sap.short_description = "CN SAP"
    asset_cn_sap.admin_order_field = "asset__CN_SAP"
    
    def action_lampiran_capex(self, obj):
        cn_sap = obj.asset.CN_SAP if obj.asset else ''
        existing = FormLampiranCapex.objects.filter(CN_SAP=cn_sap).first()

        if existing:
            url = reverse('form:lampiran_capex_detail', args=[existing.pk])
            status_colors = {
                'DRAFT': '#888', 'SUB': '#1883ff', 'APR1': '#f57c00',
                'APR2': '#9c27b0', 'FIN': '#28a745', 'REJ': '#dc3545',
            }
            color = status_colors.get(existing.status, '#888')

            return format_html(
                '''
                <div style="display:flex;flex-direction:column;align-items:center;gap:4px;">
                    <a href="{url}" style="display:inline-block;padding:5px 12px;background:#f0f9f0;color:#28a745;border:1.5px solid #28a745;border-radius:6px;font-size:11px;font-weight:600;text-decoration:none;white-space:nowrap;">📄 Lihat Form</a>
                    <span style="font-size:10px;color:{color};font-weight:600;">● {status}</span>
                </div>
                ''',
                url=url, color=color, status=existing.get_status_display(),
            )
        else:
            return format_html(
                '''
                <button onclick="event.preventDefault(); event.stopPropagation(); openCapexModal('{cn_sap}');"
                    style="padding:5px 12px;background:#1883ff;color:white;border:none;border-radius:6px;font-size:11px;font-weight:600;cursor:pointer;white-space:nowrap;">📋 Create Form</button>
                ''',
                cn_sap=cn_sap,
            )

    # 🌟 FIX: Ubah short_description ini agar tidak bentrok dengan kolom dokumen upload!
    action_lampiran_capex.short_description = "Form Lampiran Capex"

    # --- FIELDSETS & KONFIGURASI LAIN TETAP SAMA ---
    fieldsets = (
        (None, {'fields': (('No_Asset', 'CN_ELLIPSE'), 'EGI', 'TYPE', 'GROUP', 'CLASS_WEIGHT',)}),
        ('Detail Kepemilikan & Lokasi', {'fields': ('OWNERSHIP', 'SECTION', 'LOCATION', 'SUB_SITE', 'SUB_LOCATION'),}),
        ('Spesifikasi & Kondisi Teknis (Terakhir Diketahui)', {'fields': ('BRAND', 'SN', 'HM_SMR', 'HM_DATE', 'SPO_EQUIPMENT', 'PERSENTASE_SPO'),}),
        ('Status Disposal', {'fields': ('EQUIPMENT_CONDITION', 'STATUS_EQUIPMENT', 'STATUS_EQUIPMENT_DISPOSED', 'REFERENSI_NO_PDE','nbv_disposed'),}),
        ('Informasi Pembaruan Sistem', {'fields': ('LAST_UPDATED_MONTH', 'LAST_UPDATED_YEAR', 'UPDATED_AT'), 'classes': ('collapse',),}),
    )

    def _is_atasan(self, user):
        if not user or user.is_superuser:
            return False
        try:
            profile = user.userprofile
            level = str(profile.jabatan_level).upper() if profile.jabatan_level else ''
            nama_resmi = str(profile.jabatan_nama_resmi).upper() if profile.jabatan_nama_resmi else ''
            keyword_atasan = ['SECTION HEAD', 'DEPARTMENT HEAD', 'CHIEF', 'MANAGER', 'GM', 'HEAD']
            if any(k in level or k in nama_resmi for k in keyword_atasan):
                return True
        except Exception:
            pass
        return False

    def has_add_permission(self, request):
        return request.user.is_superuser

    def has_import_permission(self, request):
        return request.user.is_superuser

    def has_export_permission(self, request):
        if request.user.is_superuser:
            return True
        if self._is_atasan(request.user):
            return False
        if hasattr(request.user, 'userprofile'):
            jabatan_level = str(getattr(request.user.userprofile, 'jabatan_level', '')).upper()
            if jabatan_level in ['SENIOR_OFFICER', 'OFFICER', 'SENIOR OFFICER']:
                return True
        return False


    def get_export_formats(self): return [CSV, XLSX, JSON]

    def get_actions(self, request):
        actions = super().get_actions(request)
        if 'export_admin_action' in actions: del actions['export_admin_action']
        return actions

    def PERSENTASE_SPO_display(self, obj):
        try:
            if obj.PERSENTASE_SPO is not None: return f"{float(obj.PERSENTASE_SPO) * 100:.2f}%"
            return "-"
        except (ValueError, TypeError): return "-"
    PERSENTASE_SPO_display.short_description = "PERSENTASE SPO"

    actions = ['delete_selected']

    class Media:
        js = (
            'js/forms/quick_upload_disposed.js',  # Pastikan path ini sesuai dengan folder static Bapak
        )


#=======================================
#=====class untuk equipment operate =====
#========================================

class AssetEquipmentOperateResource(resources.ModelResource):
    # ✅ FIX IMPORT: Definisikan relasi ForeignKey/OneToOne ke model induk melalui CN_SAP
    asset = fields.Field(
        column_name='Code Number',
        attribute='asset',
        widget=ForeignKeyWidget(AssetEquipment, field='CN_SAP')
    )

    def clean_HM_DATE(self, value):
        if value is not None and str(value).strip().lower() == "midnight":
            return None
        return value

    def clean_PERSENTASE_SPO(self, value):
        if value is None or str(value).strip() == '':
            return None
        try:
            return float(str(value).replace(',', '.'))
        except ValueError:
            raise ValueError(f"'{value}' bukan angka yang valid untuk PERSENTASE_SPO.")

    def save_instance(self, instance, *args, dry_run=False, **kwargs):
        if not dry_run:
            instance.save()

    No_Asset = fields.Field(column_name='No Asset', attribute='No_Asset', widget=CharWidget())
    CN_ELLIPSE = fields.Field(column_name='Code Number Ellipse', attribute='CN_ELLIPSE', widget=CharWidget())
    TYPE = fields.Field(column_name='Type', attribute='TYPE', widget=CharWidget())
    GROUP = fields.Field(column_name='Class Equipment', attribute='GROUP', widget=CharWidget())
    CLASS_WEIGHT = fields.Field(column_name='Class Weight', attribute='CLASS_WEIGHT', widget=CharWidget())
    OWNERSHIP = fields.Field(column_name='Ownership', attribute='OWNERSHIP', widget=CharWidget())
    SECTION = fields.Field(column_name='Section', attribute='SECTION', widget=CharWidget())
    LOCATION = fields.Field(column_name='Location', attribute='LOCATION', widget=CharWidget())
    SUB_SITE = fields.Field(column_name='Sub Site', attribute='SUB_SITE', widget=CharWidget())
    SUB_LOCATION = fields.Field(column_name='Sub Location', attribute='SUB_LOCATION', widget=CharWidget())
    BRAND = fields.Field(column_name='Brand', attribute='BRAND', widget=CharWidget())
    SN = fields.Field(column_name='Serial Number', attribute='SN', widget=CharWidget())
    HM_SMR = fields.Field(column_name='Hour Meter', attribute='HM_SMR', widget=CharWidget())
    
    HM_DATE = fields.Field(
        column_name='Hour Meter Date',
        attribute='HM_DATE',
        widget=DateWidget(format='%Y-%m-%d')
    )
    SPO_EQUIPMENT = fields.Field(column_name='SPO Equipment', attribute='SPO_EQUIPMENT', widget=IntegerWidget())
    PERSENTASE_SPO = fields.Field(column_name='% SPO Equipment', attribute='PERSENTASE_SPO', widget=CharWidget())
    EQUIPMENT_CONDITION = fields.Field(column_name='Equipment Condition', attribute='EQUIPMENT_CONDITION', widget=CharWidget())
    STATUS_EQUIPMENT = fields.Field(column_name='Status Equipment', attribute='STATUS_EQUIPMENT', widget=CharWidget())
    STATUS_EQUIPMENT_DISPOSED = fields.Field(column_name=' Status Equipment Disposed', attribute='STATUS_EQUIPMENT_DISPOSED', widget=CharWidget())
    NBV = fields.Field(column_name='NBV', attribute='NBV', widget=DecimalWidget())
    WEIGHT = fields.Field(column_name='WEIGHT', attribute='WEIGHT', widget=DecimalWidget())
    REFERENSI_NO_PDE = fields.Field(column_name='Referensi No PDE', attribute='REFERENSI_NO_PDE', widget=CharWidget())
    YEAR = fields.Field(column_name='Year', attribute='YEAR', widget=IntegerWidget())
    MONTH = fields.Field(column_name='Month', attribute='MONTH', widget=DateWidget(format='%Y-%m-%d'))
    BP = fields.Field(column_name='BP', attribute='BP', widget=CharWidget())

    class Meta:
        model = AssetEquipmentOperate
        # ✅ FIX: Menggunakan 'asset' sebagai ganti 'CN_SAP' karena field mapping mengarah ke object asset
        import_id_fields = ['asset', 'MONTH', 'YEAR']
        fields = (
            'asset','No_Asset', 'CN_ELLIPSE', 'EGI', 'TYPE', 'GROUP', 'CLASS_WEIGHT',
            'OWNERSHIP', 'SECTION', 'LOCATION', 'SUB_SITE', 'SUB_LOCATION', 'BRAND',
            'SN', 'HM_SMR', 'HM_DATE', 'SPO_EQUIPMENT', 'PERSENTASE_SPO',
            'EQUIPMENT_CONDITION', 'STATUS_EQUIPMENT', 'STATUS_EQUIPMENT_DISPOSED','NBV','WEIGHT',
            'REFERENSI_NO_PDE', 'YEAR', 'MONTH','BP'
        )
        export_order = fields
        skip_unchanged = True
        report_skipped = True


# --- Filter Klaster Bulan & Tahun ---
class MonthFilter(SimpleListFilter):
    title = 'Bulan Laporan'
    parameter_name = 'report_month'

    def lookups(self, request, model_admin):
        months = AssetEquipmentOperate.objects.values_list('MONTH', flat=True).distinct().order_by('MONTH')
        month_names = {
            1: 'Januari', 2: 'Februari', 3: 'Maret', 4: 'April',
            5: 'Mei', 6: 'Juni', 7: 'Juli', 8: 'Agustus',
            9: 'September', 10: 'Oktober', 11: 'November', 12: 'Desember'
        }
        return [(str(m.month), month_names.get(m.month, f"Bulan {m.month}")) for m in months if m is not None]

    def queryset(self, request, queryset):
        if self.value():
            return queryset.filter(MONTH__month=self.value())
        return queryset

class YearFilter(SimpleListFilter):
    title = 'Tahun Laporan'
    parameter_name = 'report_year'

    def lookups(self, request, model_admin):
        years = AssetEquipmentOperate.objects.values_list('YEAR', flat=True).distinct().order_by('YEAR')
        return [(str(y), str(y)) for y in years if y is not None]

    def queryset(self, request, queryset):
        if self.value():
            return queryset.filter(YEAR=self.value())
        return queryset


@admin.register(AssetEquipmentOperate, site=admin_site)
class AssetEquipmentOperateAdmin(ImportExportModelAdmin):
    resource_class = AssetEquipmentOperateResource

    list_display = (
        "asset_cn_sap", "No_Asset", "CN_ELLIPSE", "EGI", "display_foto", "TYPE", "GROUP",
        "CLASS_WEIGHT", "OWNERSHIP", "SECTION", "LOCATION", "SUB_SITE", "SUB_LOCATION",
        "BRAND", "SN", "HM_SMR", "HM_DATE", "SPO_EQUIPMENT", "PERSENTASE_SPO_display",
        "EQUIPMENT_CONDITION", "STATUS_EQUIPMENT", "STATUS_EQUIPMENT_DISPOSED", "NBV", "WEIGHT",
        "REFERENSI_NO_PDE", "YEAR", "MONTH", "BP"
    )
    search_fields = ("asset__CN_SAP", "CN_ELLIPSE", "EGI")
    list_filter = (YearFilter, MonthFilter, "EQUIPMENT_CONDITION", "SECTION", "EGI")
    list_per_page = 5  # Direkomendasikan naik dari 5 agar data lebih scannable

    # ✅ FIX LOGIKA: Ubah dari BREAKDOWN menjadi OPERATE sesuai peruntukan tabel anak ini
    def get_queryset(self, request):
        qs = super().get_queryset(request)
        qs = qs.filter(EQUIPMENT_CONDITION__iexact='OPERATE')

        if request.user.is_superuser:
            return qs

        if not hasattr(request.user, 'userprofile'):
            return qs.none()
        try:
            profile = request.user.userprofile
            user_lokasi = profile.lokasi or ""
            user_section = profile.section or ""
        except Exception:
            return qs.none()

        if not user_lokasi:
            return qs.none()

        qs = qs.filter(LOCATION__iexact=user_lokasi)
        if user_section:
            qs = qs.filter(SECTION__iexact=user_section)
        return qs

    # ✅ FIX: Daftarkan metode asset_cn_sap agar list_display tidak error
    def asset_cn_sap(self, obj):
        return obj.asset_id
    asset_cn_sap.short_description = "Code Number (SAP)"
    asset_cn_sap.admin_order_field = "asset__CN_SAP"

    def get_import_resource_kwargs(self, request, *args, **kwargs):
        kwargs = super().get_import_resource_kwargs(request, *args, **kwargs)
        kwargs.update({'request': request})
        return kwargs

    def PERSENTASE_SPO_display(self, obj):
        try:
            if obj.PERSENTASE_SPO is not None:
                return f"{float(obj.PERSENTASE_SPO) * 100:.2f}%"
            return "-"
        except (ValueError, TypeError):
            return "-"
    PERSENTASE_SPO_display.short_description = "PERSENTASE SPO"

    def display_foto(self, obj):
        if obj.FOTO:
            return format_html('<img src="{}" style="max-width: 50px; height: auto; border-radius: 4px;" />', obj.FOTO.url)
        return "Tidak ada foto"
    display_foto.short_description = "Foto Aset"

    # Menyertakan preview_foto ke dalam halaman form detail
    readonly_fields = ('preview_foto',)

    fieldsets = (
        (None, {
            'fields': (
                ('No_Asset', 'CN_ELLIPSE'),
                'EGI', 'TYPE', 'GROUP', 'CLASS_WEIGHT', 'FOTO', 'preview_foto',
            )
        }),
        ('Detail Kepemilikan & Lokasi', {
            'fields': ('OWNERSHIP', 'SECTION', 'LOCATION', 'SUB_SITE', 'SUB_LOCATION',),
            'description': 'Informasi terkait kepemilikan dan penempatan aset.'
        }),
        ('Spesifikasi & Kondisi Teknis', {
            'fields': ('BRAND', 'SN', 'HM_SMR', 'HM_DATE', 'SPO_EQUIPMENT', 'PERSENTASE_SPO'),
        }),
        ('Status & Referensi', {
            'fields': ('EQUIPMENT_CONDITION', 'STATUS_EQUIPMENT', 'STATUS_EQUIPMENT_DISPOSED', 'NBV', 'WEIGHT', 'REFERENSI_NO_PDE', 'BP', 'YEAR', 'MONTH'),
        }),
    )

    def preview_foto(self, obj):
        if obj.FOTO:
            return format_html('<img src="{}" style="max-width: 200px; height: auto; border-radius: 5px;" />', obj.FOTO.url)
        return "Belum ada foto diupload"
    preview_foto.short_description = "Pratinjau Gambar"


    def _is_atasan(self, user):
        if not user or user.is_superuser:
            return False
        try:
            profile = user.userprofile
            level = str(profile.jabatan_level).upper() if profile.jabatan_level else ''
            nama_resmi = str(profile.jabatan_nama_resmi).upper() if profile.jabatan_nama_resmi else ''
            keyword_atasan = ['SECTION HEAD', 'DEPARTMENT HEAD', 'CHIEF', 'MANAGER', 'GM', 'HEAD']
            if any(k in level or k in nama_resmi for k in keyword_atasan):
                return True
        except Exception:
            pass
        return False

    def has_add_permission(self, request):
        return request.user.is_superuser

    def has_import_permission(self, request):
        return request.user.is_superuser

    def has_export_permission(self, request):
        if request.user.is_superuser:
            return True
        if self._is_atasan(request.user):
            return False
        if hasattr(request.user, 'userprofile'):
            jabatan_level = str(getattr(request.user.userprofile, 'jabatan_level', '')).upper()
            if jabatan_level in ['SENIOR_OFFICER', 'OFFICER', 'SENIOR OFFICER']:
                return True
        return False



    def get_export_formats(self):
        return [CSV, XLSX, JSON]

    def get_actions(self, request):
        actions = super().get_actions(request)
        if 'export_admin_action' in actions:
            del actions['export_admin_action']
        return actions 

#--------------------------------------------------------
#========================================================
#-------------Register foto_konsidi unit-----------------
#========================================================
#--------------------------------------------------------


try:
    admin.site.unregister(User)
    admin.site.unregister(Group)
except admin.sites.NotRegistered:
    pass



class EquipmentConditionFilter(SimpleListFilter):
    title = 'equipment condition'
    parameter_name = 'equipment_condition'

    def lookups(self, request, model_admin):
        conditions = set(
            AssetEquipment.objects.values_list('EQUIPMENT_CONDITION', flat=True).distinct()
        )
        return [(c, c) for c in conditions if c]

    def queryset(self, request, queryset):
        if self.value():
            return queryset.filter(asset__EQUIPMENT_CONDITION=self.value())
        return queryset

class NoAssetFilter(SimpleListFilter):
    title = 'No Asset'
    parameter_name = 'no_asset'

    def lookups(self, request, model_admin):
        no_assets = AssetEquipment.objects.values_list('No_Asset', flat=True).distinct()
        return [(no_asset, no_asset) for no_asset in no_assets if no_asset]

    def queryset(self, request, queryset):
        if self.value():
            return queryset.filter(asset__No_Asset=self.value())
        return queryset


#--------------------------------------------------------
#========================================================
#-------------Register prepare for disposed unit-----------------
#========================================================
#--------------------------------------------------------

from django.contrib import admin
from django.utils import timezone
from django.utils.html import format_html
from import_export.admin import ImportExportModelAdmin
# Sesuaikan import export formats jika diperlukan sesuai project Anda
# from import_export.formats.base_formats import CSV, XLSX, JSON

# 1. Menu untuk Fase 1 (Prepare for Disposed)
@admin.register(AssetEquipmentPrepareDisposed, site=admin_site)
class PrepareDisposedAdmin(ImportExportModelAdmin):

    change_list_template = "admin/change_list.html"

    list_display = (
        "asset_cn_sap", "No_Asset", "EGI", "SN", "TYPE", "GROUP", "LOCATION", "SUB_SITE", "SUB_LOCATION", "EQUIPMENT_CONDITION",
        "REFERENSI_NO_PDE", "foto_4_sisi_cell", "form_foto_4_sisi_cell",
        "inspeksi_unit_cell","form_inspeksi_unit_cell","rca_cell", "pengajuan_disposed_cell",
    )
    search_fields = ("asset__CN_SAP", "No_Asset", "REFERENSI_NO_PDE",)
    list_filter = ("SUB_LOCATION", "LOCATION", "EGI", "status_approval",)
    list_per_page = 5    

    def get_queryset(self, request):
        qs = super().get_queryset(request)
        # Karena ini model mandiri khusus Prepare, filter EQUIPMENT_CONDITION opsional 
        qs = qs.filter(EQUIPMENT_CONDITION__iexact='PREPARE FOR DISPOSED')

        # Superuser melihat semuanya
        if request.user.is_superuser:
            return qs

        # Validasi profil user
        if not hasattr(request.user, 'userprofile'):
            return qs.none()
        
        try:
            profile      = request.user.userprofile
            user_lokasi  = profile.lokasi or ""
            user_section = profile.section or ""
            jabatan_level = getattr(profile, 'jabatan_level', '') or ""
        except Exception:
            return qs.none()

        if not user_lokasi:
            return qs.none()

        # Filter lokasi wajib untuk semua user non-superuser
        qs = qs.filter(LOCATION__iexact=user_lokasi)


        # ── LOGIKA FILTER BERDASARKAN PERAN ──
        list_level_atasan = ['DEPT_HEAD', 'SECTION_HEAD', 'PROJECT_MANAGER', 'MANAGER']

        if jabatan_level in list_level_atasan:
            # ATASAN: Hanya melihat yang sudah disubmit (WAITING) dan di section yang sama
            
            qs = qs.filter(status_approval='WAITING')
            if user_section:
                qs = qs.filter(SECTION__iexact=user_section)
                
        elif user_section and jabatan_level in ['SENIOR_OFFICER', 'OFFICER']:
            # Jika yang login adalah pembuat (Officer/Senior Officer seperti Ibram)
            qs = qs.filter(SECTION__iexact=user_section)
            
        return qs

        

    def get_import_resource_kwargs(self, request, *args, **kwargs):
        kwargs = super().get_import_resource_kwargs(request, *args, **kwargs)
        kwargs.update({'request': request})
        return kwargs

    # ── 🌟 CELL GENERATOR DILOKALISASI KE BREAKDOWN ADMIN ──
    def _document_action_cell(self, obj, field_name, label_name):
        cn_sap = obj.asset.CN_SAP if obj.asset else ""
        file_obj = getattr(obj, field_name, None)

        if file_obj:
            uploaded_at = getattr(obj, f'{field_name}_uploaded_at', None)
            if uploaded_at:
                local_time = timezone.localtime(uploaded_at)
                date_str = local_time.strftime('%d/%m/%Y %H:%M')
            else:
                date_str = '-'

            return format_html(
                '<div style="display:flex; flex-direction:column; gap:4px; min-width:140px;">'
                    '<div style="display:flex; align-items:center; gap:4px; white-space:nowrap;">'
                        '<a href="{url}" target="_blank" class="button" style="background:#28a745; color:white; padding:3px 6px; border-radius:4px; font-size:10px; text-decoration:none; font-weight:600;">✓ Lihat</a>'
                        '<button onclick="event.preventDefault(); event.stopPropagation(); openUploadModal(\'{cn_sap}\', \'{field_name}\', \'{label_name}\');" '
                        'style="background:#ffc107; color:#212529; border:none; padding:3px 6px; border-radius:4px; font-size:10px; font-weight:600; cursor:pointer;">✏️ Ganti</button>'
                        '<button onclick="event.preventDefault(); event.stopPropagation(); deleteDocument(\'{cn_sap}\', \'{field_name}\', \'{label_name}\');" '
                        'style="background:#dc3545; color:white; border:none; padding:3px 6px; border-radius:4px; font-size:10px; font-weight:600; cursor:pointer;">🗑️</button>'
                    '</div>'
                    '<div style="display:flex; align-items:center; gap:6px;">'
                        '<span style="background:#d4edda; color:#155724; padding:1px 4px; border-radius:3px; font-size:9px; font-weight:bold;">Complete</span>'
                        '<span style="font-size:9px; color:#6c757d; font-family:monospace;">📅 {date}</span>'
                    '</div>'
                '</div>',
                url=file_obj.url,
                date=date_str,
                cn_sap=cn_sap,
                field_name=field_name,
                label_name=label_name
            )
        else:
            return format_html(
                '<div style="display:flex; align-items:center; gap:6px; white-space:nowrap;">'
                '<button onclick="event.preventDefault(); event.stopPropagation(); openUploadModal(\'{cn_sap}\', \'{field_name}\', \'{label_name}\');" '
                'style="background:#1883ff; color:white; border:none; padding:4px 8px; border-radius:4px; font-size:11px; font-weight:600; cursor:pointer;">📤 Upload</button>'
                '<span style="background:#fff3cd; color:#856404; padding:3px 6px; border-radius:4px; font-size:10px; font-weight:bold;">Prog</span>'
                '</div>',
                cn_sap=cn_sap, field_name=field_name, label_name=label_name
            )

    def foto_4_sisi_cell(self, obj): return self._document_action_cell(obj, 'foto_4_sisi', 'Foto 4 Sisi (PDF)')
    foto_4_sisi_cell.short_description = 'Foto 4 Sisi (PDF)'

    
    def _is_atasan(self, user):
        """
        Helper untuk mengecek apakah user adalah atasan (Section Head / Dept Head / Chief).
        Superuser TIDAK masuk kategori ini agar bisa ditangani secara terpisah.
        """
        if not user:
            return False
            
        # Superuser ditangani secara terpisah, jadi di sini kembalikan False untuk superuser
        if user.is_superuser:
            return False
            
        try:
            profile = user.userprofile
            level = str(profile.jabatan_level).upper() if profile.jabatan_level else ''
            nama_resmi = str(profile.jabatan_nama_resmi).upper() if profile.jabatan_nama_resmi else ''
            
            keyword_atasan = ['SECTION HEAD', 'DEPARTMENT HEAD', 'CHIEF', 'MANAGER', 'GM', 'HEAD']
            if any(k in level or k in nama_resmi for k in keyword_atasan):
                return True
            
        except Exception:
            pass
        return False

    from django.template.loader import render_to_string
    from django.utils.html import format_html
   

    def form_foto_4_sisi_cell(self, obj):
        """
        Tampilkan status 4 foto, tombol Lihat/Ganti, tombol Submit Approval, dan informasi waktu.
        """

        from django.utils import timezone as tz
        from django.urls import reverse, NoReverseMatch
        
        cn_sap     = obj.asset.CN_SAP if obj.asset else ''
        cn_ellipse = obj.CN_ELLIPSE    or '-'
        sn         = obj.SN            or '-'
        egi        = obj.EGI           or '-'

        # ✅ Cek kelengkapan 4 foto & jumlahnya
        semua_lengkap = obj.foto_4_sisi_terpisah_lengkap
        jumlah_foto = sum(
            1 for f in AssetEquipmentPrepareDisposed.FOTO_TERPISAH_FIELDS
            if getattr(obj, f)
        )
        total_foto = len(AssetEquipmentPrepareDisposed.FOTO_TERPISAH_FIELDS)

        # 🔄 Penentuan waktu aktif berdasarkan status approval
        active_time = None
        if obj.status_approval == 'APPROVED' and obj.approved_at:
            active_time = obj.approved_at
        elif obj.status_approval == 'REJECTED' and obj.rejected_at:
            active_time = obj.rejected_at
        elif obj.status_approval == 'WAITING' and obj.submitted_at:
            active_time = obj.submitted_at
        else:
            active_time = obj.foto_4_sisi_uploaded_at

        info_waktu = tz.localtime(active_time).strftime('%d/%m/%Y %H:%M') if active_time else '-'

        # Ambil URL foto lama
        url_depan    = obj.tampak_depan.url if obj.tampak_depan else ''
        url_belakang = obj.tampak_belakang.url if obj.tampak_belakang else ''
        url_kanan    = obj.tampak_samping_kanan.url if obj.tampak_samping_kanan else ''
        url_kiri     = obj.tampak_samping_kiri.url if obj.tampak_samping_kiri else ''

        foto_data_json = f"{{{{depan:'{url_depan}', belakang:'{url_belakang}', kanan:'{url_kanan}', kiri:'{url_kiri}'}}}}"

        # Generate URL PDF & Print
        try:
            pdf_base_url = reverse('download_pdf_foto_4_sisi', args=[cn_sap])
        except NoReverseMatch:
            try:
                pdf_base_url = reverse('asset:download_pdf_foto_4_sisi', args=[cn_sap])
            except NoReverseMatch:
                pdf_base_url = f"/asset/api/prepare-disposed/download-pdf/{cn_sap}/"

        print_url = f"{pdf_base_url}?print=true"
        pdf_url = pdf_base_url

        # ── CEK ROLE USER ──
        current_user   = getattr(self, 'current_user', None)
        is_superuser   = current_user and current_user.is_superuser
        is_atasan_user = self._is_atasan(current_user)
        is_atasan_only = is_atasan_user and not is_superuser

        submit_info_tooltip  = f"Disubmit oleh: {obj.submitted_by.username}" if obj.submitted_by else ""
        approve_info_tooltip = f"Disetujui oleh: {obj.approved_by.username}" if obj.approved_by else ""

        # Badge Status
        status_badge_bg = "#e2e3e5"
        status_badge_color = "#383d41"
        status_text = "Draft / Belum Disubmit"

        if obj.status_approval == 'WAITING':
            status_badge_bg = "#fff3cd"
            status_badge_color = "#856404"
            status_text = "Menunggu Approval Atasan"
        elif obj.status_approval == 'REJECTED':
            status_badge_bg = "#f8d7da"
            status_badge_color = "#721c24"
            status_text = "Revisi / Ditolak"
        elif obj.status_approval == 'APPROVED':
            status_badge_bg = "#d1e7dd"
            status_badge_color = "#0f5132"
            status_text = "Disetujui"
        elif obj.status_approval == 'DRAFT':
            status_badge_bg = "#e2e3e5"
            status_badge_color = "#383d41"
            status_text = "Draft / Belum Disubmit"

        approver_name = ""
        if obj.status_approval == 'WAITING' and getattr(obj, 'current_approver', None):
            approver_name = obj.current_approver.get_full_name() or obj.current_approver.username

        # ── SIAPKAN CONTEXT UNTUK TEMPLATE ──
        context = {
            'cn_sap': cn_sap,
            'cn_ellipse': cn_ellipse,
            'sn': sn,
            'egi': egi,
            'foto_data_json': foto_data_json,
            
            'semua_lengkap': semua_lengkap,
            'jumlah_foto': jumlah_foto,
            'total_foto': total_foto,
            'status': obj.status_approval,
            
            'pdf_url': pdf_url,
            'print_url': print_url,
            'info_waktu': info_waktu,
            
            'is_superuser': is_superuser,
            'is_atasan_only': is_atasan_only,
            
            'submit_info_tooltip': submit_info_tooltip,
            'approve_info_tooltip': approve_info_tooltip,
            'approver_name': approver_name,
            
            'badge_bg': status_badge_bg,
            'badge_color': status_badge_color,
            'status_text': status_text,
        }

        html_string = render_to_string('admin/asset/partials/foto_4_sisi_cell.html', context)
        return format_html(html_string)

    form_foto_4_sisi_cell.short_description = "4 Foto Terpisah"

    # ── Update progress_dokumen untuk pakai total_required ──────
    def progress_dokumen(self, obj):
        lengkap = obj.jumlah_lengkap
        total   = obj.total_required  
        pct     = obj.persentase_lengkap
        color   = '#28a745' if pct == 100 else ('#ffc107' if pct >= 50 else '#dc3545')

        return format_html(
            '<div style="width:80px;background:#e9ecef;border-radius:10px;'
            'overflow:hidden;display:inline-block;vertical-align:middle;">'
            '<div style="width:{}%;background:{};height:8px;border-radius:10px;"></div>'
            '</div>'
            '<span style="font-size:10px;color:{};font-weight:700;'
            'margin-left:6px;vertical-align:middle;">{}/{}</span>',
            pct, color, color, lengkap, total
        )
    progress_dokumen.short_description = "Progress (4 syarat)"

    def rca_cell(self, obj): return self._document_action_cell(obj, 'rca', 'RCA')
    rca_cell.short_description = 'RCA'

    def inspeksi_unit_cell(self, obj): return self._document_action_cell(obj, 'inspeksi_unit', 'Inspeksi Unit')
    inspeksi_unit_cell.short_description = 'Inspeksi Unit'

 
    def form_inspeksi_unit_cell(self, obj):
        """
        Tampilkan status check sheet inspeksi unit, tombol Aksi, Lihat, Print, Download,
        Submit Approval, serta role approval digital ke atasan.
        """
        cn_sap         = obj.asset.CN_SAP if obj.asset else ''
        cn_ellipse     = obj.CN_ELLIPSE    or '-'
        sn             = obj.SN            or '-'
        egi            = obj.EGI           or '-'
        equipment_type = obj.TYPE          or '-'

        # Cek apakah inspeksi item sudah diisi
        sudah_diisi = bool(obj.inspeksi_unit_uploaded_at)

        from django.utils import timezone as tz
        
        # ── PENENTUAN WAKTU AKTIF ── berdasarkan status approval
        active_time = None
        if obj.inspeksi_status == 'APPROVED' and obj.approved_at:
            active_time = obj.approved_at
        elif obj.inspeksi_status == 'REJECTED' and obj.rejected_at:
            active_time = obj.rejected_at
        elif obj.inspeksi_status == 'WAITING' and obj.submitted_at:
            active_time = obj.submitted_at
        else:
            active_time = obj.inspeksi_unit_uploaded_at

        info_waktu = tz.localtime(active_time).strftime('%d/%m/%Y %H:%M') if active_time else '-'

        # ── GENERATE URL PDF & PRINT ──
        from django.urls import reverse, NoReverseMatch

        try:
            pdf_base_url = reverse('download_pdf_inspeksi_unit', args=[cn_sap])
        except NoReverseMatch:
            try:
                pdf_base_url = reverse('asset:download_pdf_inspeksi_unit', args=[cn_sap])
            except NoReverseMatch:
                pdf_base_url = f"/asset/api/prepare-disposed/download-pdf-inspeksi/{cn_sap}/"

        print_url = f"{pdf_base_url}?print=true"
        pdf_url = pdf_base_url

        # ── CEK ROLE USER (ATASAN / SUPERUSER) ──
        current_user   = getattr(self, 'current_user', None)
        is_superuser   = current_user and current_user.is_superuser
        is_atasan_user = self._is_atasan(current_user)
        is_atasan_only = is_atasan_user and not is_superuser

        submit_info_tooltip   = f"Disubmit oleh: {obj.submitted_by.username}" if obj.submitted_by else ""
        approve_info_tooltip = f"Disetujui oleh: {obj.approved_by.username}" if obj.approved_by else ""


        status_badge_bg = "#e2e3e5"
        status_badge_color = "#383d41"
        status_text = "Draft / Belum Disubmit"
        
        if obj.inspeksi_status == 'WAITING':
            status_badge_bg = "#fff3cd"
            status_badge_color = "#856404"
            status_text = "Menunggu Approval Atasan"
        elif obj.inspeksi_status == 'REJECTED':
            status_badge_bg = "#f8d7da"
            status_badge_color = "#721c24"
            status_text = "Revisi / Ditolak"
        elif obj.inspeksi_status == 'APPROVED':
            status_badge_bg = "#d1e7dd"
            status_badge_color = "#0f5132"
            status_text = "Disetujui"

        # Nama Approver
        approver_name = ""
        if obj.inspeksi_status == 'WAITING' and getattr(obj, 'current_approver', None):
            approver_name = obj.current_approver.get_full_name() or obj.current_approver.username


        # ── SIAPKAN CONTEXT UNTUK TEMPLATE ──
        context = {
            'cn_sap': cn_sap,
            'egi': egi,
            'equipment_type': equipment_type,
            'sudah_diisi': sudah_diisi,
            'status': obj.inspeksi_status,
            
            'pdf_url': pdf_url,
            'print_url': print_url,
            'info_waktu': info_waktu,
            
            'is_superuser': is_superuser,
            'is_atasan_only': is_atasan_only,
            
            'submit_info_tooltip': submit_info_tooltip,
            'approve_info_tooltip': approve_info_tooltip,
            'approver_name': approver_name,
            
            'badge_bg': status_badge_bg,
            'badge_color': status_badge_color,
            'status_text': status_text,
        }

        # Render dari file template terpisah
        html_string = render_to_string('admin/asset/partials/inspeksi_unit_cell.html', context)
        return format_html(html_string)
        
    form_inspeksi_unit_cell.short_description = "Inspeksi Unit Check"


    def pengajuan_disposed_cell(self, obj): return self._document_action_cell(obj, 'pengajuan_disposed', 'Pengajuan Disposed')
    pengajuan_disposed_cell.short_description = 'Pengajuan'

    def save_model(self, request, obj, form, change):
        """
        Fungsi ini otomatis berjalan saat user menekan tombol save / upload.
        """
        obj.updated_by = request.user 
        super().save_model(request, obj, form, change)

    def changelist_view(self, request, extra_context=None):

        self.current_user = request.user
        
        extra_context = extra_context or {}
        return super().changelist_view(request, extra_context=extra_context)

    def asset_cn_sap(self, obj):
        return obj.asset.CN_SAP if obj.asset else "-"
    asset_cn_sap.short_description = "CN SAP"
    asset_cn_sap.admin_order_field = "asset__CN_SAP"


    # ── 🌟 FUNGSI HELPER UNTUK TAMPILAN ADMIN ──
    def status_approval_colored(self, obj):
        colors = {
                'DRAFT': '#6c757d',     # Abu-abu
                'WAITING': '#ffc107',   # Kuning/Oranye
                'APPROVED': '#28a745',  # Hijau
                'REJECTED': '#dc3545'   # Merah
            }
        color = colors.get(obj.status_approval, '#6c757d')
        return format_html(
            '<span style="background:{}; color:white; padding:3px 6px; border-radius:4px; font-size:10px; font-weight:bold;">{}</span>',
            color, obj.get_status_approval_display()
        )
    status_approval_colored.short_description = "Status Approval"

    def current_approver_name(self, obj):
        if obj.current_approver:
            return obj.current_approver.get_full_name() or obj.current_approver.username
        return "-"
    current_approver_name.short_description = "Current Approver"

    # --- FIELDSETS DISESUAIKAN DENGAN KOLOM MODEL MANDIRI & FOTO BARU ---
    fieldsets = (
        (None, {'fields': (('No_Asset', 'CN_ELLIPSE'), 'EGI', 'TYPE', 'GROUP', 'CLASS_WEIGHT',)}),
        ('Detail Kepemilikan & Lokasi', {'fields': ('OWNERSHIP', 'SECTION', 'LOCATION', 'SUB_SITE', 'SUB_LOCATION'),}),
        ('Spesifikasi & Kondisi Teknis (Terakhir Diketahui)', {'fields': ('BRAND', 'SN', 'HM_SMR', 'HM_DATE', 'SPO_EQUIPMENT', 'PERSENTASE_SPO'),}),
        ('Status Disposal', {'fields': ('EQUIPMENT_CONDITION', 'STATUS_EQUIPMENT', 'REFERENSI_NO_PDE', 'nbv_prepare','catatan_reject'),}),
        ('Dokumen & Foto 4 Sisi', {'fields': ('foto_4_sisi', 'tampak_depan', 'tampak_belakang', 'tampak_samping_kanan', 'tampak_samping_kiri', 'inspeksi_unit', 'form_inspeksi_unit_cell','rca', 'pengajuan_disposed'),}),
    )

    # ── 🔒 KONTROL HAK AKSES TOMBOL ADD, IMPORT, DAN EXPORT ──

    def has_add_permission(self, request):
        """
        Hanya Superuser yang bisa melihat tombol 'Add'
        """
        return request.user.is_superuser

    def has_import_permission(self, request):
        """
        Hanya Superuser yang bisa melihat tombol 'Import'
        """
        return request.user.is_superuser

    def has_export_permission(self, request):
        """
        Aturan tombol 'Export':
        1. Superuser: Bisa melihat.
        2. Atasan (Manager, dll): TIDAK bisa melihat.
        3. Pembuat (Officer / Senior Officer): Bisa melihat.
        """
        # 1. Superuser selalu bisa export
        if request.user.is_superuser:
            return True
        
        # 2. Cek apakah user adalah atasan menggunakan fungsi helper yang sudah Anda buat
        if self._is_atasan(request.user):
            return False
            
        # 3. Cek apakah user adalah pembuat (Officer / Senior Officer)
        if hasattr(request.user, 'userprofile'):
            jabatan_level = getattr(request.user.userprofile, 'jabatan_level', '') or ""
            jabatan_level = str(jabatan_level).upper()
            
            # Pastikan string jabatan sesuai dengan data Anda di database
            if jabatan_level in ['SENIOR_OFFICER', 'OFFICER', 'SENIOR OFFICER']:
                return True
                
        # Jika bukan superuser, bukan pembuat, dan tidak terdefinisi, default sembunyikan
        return False

    def get_export_formats(self): 
        # Sesuaikan dengan format yang tersedia di project Anda
        return []
      
    def get_actions(self, request):
        actions = super().get_actions(request)
        if 'export_admin_action' in actions: del actions['export_admin_action']
        return actions

    def PERSENTASE_SPO_display(self, obj):
        try:
            if obj.PERSENTASE_SPO is not None: return f"{float(obj.PERSENTASE_SPO) * 100:.2f}%"
            return "-"
        except (ValueError, TypeError): return "-"
    PERSENTASE_SPO_display.short_description = "PERSENTASE SPO"

    actions = ['delete_selected']

    class Media:
        js = (
            'js/forms/quick_upload_disposed.js', 
            'js/forms/form_foto_4_sisi_disposed.js',
            'js/forms/form_inspeksi_unit_disposed.js',
            'js/forms/status_polling.js',  
        )

#=========================================================
#------------- Register untuk User Profile ----------------
#=========================================================

from accounts.models import UserProfile

@admin.register(UserProfile, site=admin_site)
class UserProfileAdmin(ImportExportModelAdmin):
    list_display = (
        'user_username', 'user_full_name', 'lokasi', 'department', 
        'section', 'jabatan_level', 'jabatan_nama_resmi', 'atasan_langsung', 'tanda_tangan_preview'
    )
    search_fields = ('user__username', 'user__first_name', 'user__last_name', 'jabatan_nama_resmi')
    list_filter = ('lokasi', 'department', 'jabatan_level')
    list_per_page = 10

    fieldsets = (
        ('Informasi Pengguna', {
            'fields': ('user', 'lokasi', 'department', 'section')
        }),
        ('Struktur Jabatan', {
            'fields': ('jabatan_level', 'jabatan_nama_resmi', 'atasan_langsung')
        }),
        ('Tanda Tangan Digital', {
            'fields': ('tanda_tangan',)
        }),
    )

    def user_username(self, obj):
        return obj.user.username
    user_username.short_description = 'Username / NIK'
    user_username.admin_order_field = 'user__username'

    def user_full_name(self, obj):
        return obj.user.get_full_name() or '-'
    user_full_name.short_description = 'Nama Lengkap'

    def tanda_tangan_preview(self, obj):
        if obj.tanda_tangan:
            return format_html('<img src="{}" style="height: 30px; width: auto;" />', obj.tanda_tangan.url)
        return '-'
    tanda_tangan_preview.short_description = 'Preview Tanda Tangan'


# ✅ Queryset atasan: tampilkan unit yang punya MINIMAL SATU form WAITING
# Unit hilang dari list atasan hanya jika SEMUA form sudah APPROVED/REJECTED

class ApprovalAtasanAdmin(admin.ModelAdmin):

    def get_queryset(self, request):
        qs = super().get_queryset(request)
        # ✅ Tampilkan jika ada form yang masih WAITING
        return qs.filter(
            models.Q(foto_4_sisi_status='WAITING') |
            models.Q(inspeksi_status='WAITING')
        )

    list_display = (
        'asset_cn_sap',
        'get_egi',
        # ✅ Status per form — independen
        'badge_foto_4_sisi_status',
        'badge_inspeksi_status',
        'action_approve_foto',
        'action_approve_inspeksi',
    )

    def badge_foto_4_sisi_status(self, obj):
        status = obj.foto_4_sisi_status
        colors = {
            'DRAFT':    ('#888', '#f0f0f0'),
            'WAITING':  ('#856404', '#fff3cd'),
            'APPROVED': ('#155724', '#d4edda'),
            'REJECTED': ('#721c24', '#f8d7da'),
        }
        color, bg = colors.get(status, ('#333', '#eee'))
        return format_html(
            '<span style="color:{};background:{};padding:2px 8px;'
            'border-radius:10px;font-size:11px;font-weight:600;">{}</span>',
            color, bg, status
        )
    badge_foto_4_sisi_status.short_description = "Foto 4 Sisi"

    def badge_inspeksi_status(self, obj):
        status = obj.inspeksi_status
        colors = {
            'DRAFT':    ('#888', '#f0f0f0'),
            'WAITING':  ('#856404', '#fff3cd'),
            'APPROVED': ('#155724', '#d4edda'),
            'REJECTED': ('#721c24', '#f8d7da'),
        }
        color, bg = colors.get(status, ('#333', '#eee'))
        return format_html(
            '<span style="color:{};background:{};padding:2px 8px;'
            'border-radius:10px;font-size:11px;font-weight:600;">{}</span>',
            color, bg, status
        )
    badge_inspeksi_status.short_description = "Inspeksi"

    def action_approve_foto(self, obj):
        cn_sap = obj.asset.CN_SAP if obj.asset else ''
        if obj.foto_4_sisi_status == 'WAITING':
            return format_html(
                '<a href="/asset/approve-foto-4-sisi/{}/" '
                'style="background:#28a745;color:white;padding:4px 10px;'
                'border-radius:4px;font-size:11px;text-decoration:none;font-weight:600;">'
                '✅ Approve Foto</a>',
                cn_sap
            )
        return format_html(
            '<span style="color:#aaa;font-size:11px;">{}</span>',
            obj.foto_4_sisi_status
        )
    action_approve_foto.short_description = "Aksi Foto"

    def action_approve_inspeksi(self, obj):
        cn_sap = obj.asset.CN_SAP if obj.asset else ''
        if obj.inspeksi_status == 'WAITING':
            return format_html(
                '<a href="/asset/approve-inspeksi/{}/" '
                'style="background:#17a2b8;color:white;padding:4px 10px;'
                'border-radius:4px;font-size:11px;text-decoration:none;font-weight:600;">'
                '✅ Approve Inspeksi</a>',
                cn_sap
            )
        return format_html(
            '<span style="color:#aaa;font-size:11px;">{}</span>',
            obj.inspeksi_status
        )
    action_approve_inspeksi.short_description = "Aksi Inspeksi"

    
#=========================================================
#------------- Register-----------------------------------
#=========================================================

admin_site.register(User)
admin_site.register(Group)
