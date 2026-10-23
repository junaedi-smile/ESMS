# inside/form/admin.py

from django.contrib import admin
from asset.admin import admin_site 
from django.shortcuts import redirect 
from django.urls import reverse, path 
from django.utils.safestring import mark_safe 

from form.models import (
    FormPengajuanEquipmentDisposed,
    FormLampiranCapex,
    FormPengajuanDisposedSite,
    FormRepairCostAnalisis,    
    FormFotoKonditionUnit,
    ApprovalStep,
    ApprovalLog
)
from .models import  ChecksheetPI, ChecksheetItem
from .views import SelectAssetView, CreateChecksheetView, ChecksheetDetailView


# --- DEFINISI INLINE UNTUK ITEM CHECKSHEET ---
class ChecksheetItemInline(admin.TabularInline):     
    model = ChecksheetItem
    extra = 0     
    fields = ('item_name', 'qty', 'condition', 'remarks')     
    readonly_fields = ('item_name', 'qty') 
# ---------------------------------------------


@admin.register(FormPengajuanEquipmentDisposed)
class PengajuanEquipmentDisposedAdmin(admin.ModelAdmin):
    list_display = ('CN_SAP', 'TYPE', 'HM_SMR', 'LOCATION', 'status')

admin_site.register(FormPengajuanEquipmentDisposed,PengajuanEquipmentDisposedAdmin)

@admin.register(FormLampiranCapex)
class LampiranCapexAdmin(admin.ModelAdmin):
    list_display = ('CN_SAP', 'TYPE', 'HM_SMR', 'NBV_STATUS', 'status')



@admin.register(FormPengajuanDisposedSite)
class PengajuanDisposedSiteAdmin(admin.ModelAdmin):
    list_display = ('CN_SAP', 'TYPE', 'HM_SMR', 'CAUSE', 'status')

admin_site.register(FormPengajuanDisposedSite, PengajuanDisposedSiteAdmin)

@admin.register(FormRepairCostAnalisis)
class RepairCostAnalisisAdmin(admin.ModelAdmin):
    list_display = ('CN_SAP', 'TYPE', 'HM_SMR', 'TOTAL_PRICE', 'status')

admin_site.register(FormRepairCostAnalisis, RepairCostAnalisisAdmin)

@admin.register(FormFotoKonditionUnit)
class FotoKonditionUnitAdmin(admin.ModelAdmin):
    list_display = ('CN_SAP', 'TYPE', 'HM_SMR', 'LOCATION', 'status')

@admin.register(ApprovalStep)
class ApprovalStepAdmin(admin.ModelAdmin):
    list_display = ('urutan', 'nama_langkah', 'penanggung_jawab_group',)

@admin.register(ApprovalLog)
class ApprovalLogAdmin(admin.ModelAdmin):
    list_display = ('form_pengajuan', 'langkah', 'approved_by', 'tanggal_persetujuan')
    def status_dokumen(self, obj):
         return obj.form_pengajuan.status
    status_dokumen.short_description = "Status Saat Ini"
    list_display = ('form_pengajuan', 'langkah', 'approved_by', 'tanggal_persetujuan', 'status_dokumen')


# ------------------------------------------------------------------
# --- CLAS ADMIN UTAMA CHECKSHEETPI (TANPA DECORATOR) ---
# ------------------------------------------------------------------
class ChecksheetPIAdmin(admin.ModelAdmin):
    inlines = [ChecksheetItemInline]

    def create_form_link(self, obj):
        url = reverse('form:select_asset') + f'?cn_sap={obj.cn_sap}'
        return mark_safe(
            f'<a href="{url}" style="background-color:#059669; color:white; padding: 4px 8px; '
            'border-radius:4px; text-decoration:none; font-weight:bold;">Create</a>'
        )
    create_form_link.short_description = 'Create'

    list_display = ('cn_sap', 'egi', 'hm_smr', 'pic_inspector', 'diajukan_oleh','created_at', 'finalized_at','create_form_link',)
    search_fields = ('cn_sap', 'egi', 'pic_inspector')
    list_filter = ('egi', 'pic_inspector')
    list_per_page = 10

    def add_view(self, request, form_url='', extra_context=None):
        return redirect(reverse('form:select_asset'))

admin_site.register(ChecksheetPI, ChecksheetPIAdmin)
# ------------------------------------------------------------------
# ==========================================
# Bagian ATAS form/admin.py (Pastikan import ini ada)
# ==========================================
from django.db.models.signals import post_save
from django.dispatch import receiver
from django.contrib.contenttypes.models import ContentType
# ... import lainnya yang sudah ada tetap biarkan ...


# ... (Seluruh kode admin class yang sudah Anda tulis sebelumnya) ...


# ==========================================
# Bagian PALING BAWAH form/admin.py 
# ==========================================

# List semua model form yang ingin dimonitor otomatis
LIST_FORM_MODELS = [
    FormPengajuanEquipmentDisposed,
    FormLampiranCapex,
    FormPengajuanDisposedSite,
    FormRepairCostAnalisis,
    FormFotoKonditionUnit
]

@receiver(post_save, sender=FormLampiranCapex)
@receiver(post_save, sender=FormPengajuanEquipmentDisposed)
@receiver(post_save, sender=FormPengajuanDisposedSite)
@receiver(post_save, sender=FormRepairCostAnalisis)
@receiver(post_save, sender=FormFotoKonditionUnit)
def auto_record_all_forms_monitoring(sender, instance, created, **kwargs):
    if created:
        # Set status awal ke DRAFT jika kosong
        if not getattr(instance, 'status', None):
            instance.status = 'DRAFT'
            instance.save(update_fields=['status'])

        # Ambil approval step urutan pertama
        first_step = ApprovalStep.objects.filter(urutan=1).first()

        # Record log monitoring
        ApprovalLog.objects.create(
            content_type=ContentType.objects.get_for_model(instance),
            object_id=instance.id,
            langkah=first_step,           
            komentar=f"Dokumen {instance._meta.verbose_name.title()} otomatis terdaftar di monitoring."
        )

# Registrasi model lain yang menggunakan Admin Site kustom


