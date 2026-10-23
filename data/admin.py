from django.contrib import admin
from import_export import resources,fields
from import_export.admin import ImportExportModelAdmin
from .models import (
    MPS,
    AR01,
    IH08,
    HistoryReplacementComponent,
    EquipmentWeight,
    pop,
    egiobsolete,
    checksheetmasterlist,
    conmon,
    directcost,
    KaryawanPenerimaNotifikasi,
    )
from import_export.widgets import CharWidget,DateWidget,IntegerWidget,Widget,DecimalWidget
from datetime import datetime
from asset.admin import admin_site


#==================================================================================
#-------resources & Register ImporExport MPS---------------------------------------
#==================================================================================

class MPSResource(resources.ModelResource):
    class Meta:
        model = MPS
        # Fields yang akan diimpor/diekspor
        fields = (
            'JobsiteCode', 'ModelName', 'TypeName', 'ComponentName', 'ActivityName',
            'FirstLife', 'SecondLife', 'PartNumber', 'Description', 'Brand',
            'COA', 'COADesc', 'GLGroup', 'Price', 'IsMajorPart', 'Qty',
            'isCapitalized', 'Amount'
        )
        # Menentukan apakah objek baru akan dibuat atau diperbarui berdasarkan PartNumber
        # Untuk kasus ini, saya asumsikan PartNumber bisa menjadi identifikasi unik
        # Jika tidak, Anda bisa menghapus `id` dan `PartNumber` dari `fields` dan
        # menggunakan `PartNumber` sebagai `import_id_fields` jika memang unik
        import_id_fields = ('JobsiteCode','ActivityName','PartNumber',)
        export_order = fields
        skip_unchanged = True
        report_skipped = True

# Mendaftarkan model MPS ke admin site
@admin.register(MPS)
class MPSAdmin(ImportExportModelAdmin):
    """
    Mengintegrasikan fitur import/export untuk model MPS.
    """
    resource_class = MPSResource
    list_display = (
        'JobsiteCode', 'ModelName', 'TypeName', 'ComponentName', 'ActivityName',
        'PartNumber', 'Price', 'Qty', 'Amount'
    )
    search_fields = ('JobsiteCode', 'PartNumber', 'Description')
    list_filter = ('JobsiteCode', 'ModelName', 'TypeName', 'Brand')
    list_per_page = 10
#==================================================================================
#-------resources & Register ImporExport AR01--------------------------------------
#==================================================================================

class AR01Resource(resources.ModelResource):
           
        asset = fields.Field(column_name='Asset', attribute='asset', widget=CharWidget())
        sub_number = fields.Field(column_name='Sub-number', attribute='sub_number', widget=CharWidget())
        capitalized_on = fields.Field(column_name='Capitalized On', attribute='capitalized_on ', widget=CharWidget())
        asset_description = fields.Field(column_name='Asset Description', attribute='asset_description', widget=CharWidget())
        acquisition_value = fields.Field(column_name='Acquis.val.', attribute='acquisition_value', widget=CharWidget())
        accumulated_depreciation = fields.Field(column_name='Accum.dep.', attribute='accumulated_depreciation', widget=CharWidget())
        book_value = fields.Field(column_name='Book val.', attribute='book_value', widget=CharWidget())
        currency = fields.Field(column_name='currency', attribute='currency', widget=CharWidget())
        type_name = fields.Field(column_name='Type Name', attribute='type_name', widget=CharWidget())
        company_code = fields.Field(column_name='Company Code', attribute='company_code', widget=CharWidget())
        business_area = fields.Field(column_name='business_area', attribute='business_area', widget=CharWidget())
        balance_sheet_item = fields.Field(column_name='balance_sheet_item', attribute='balance_sheet_item', widget=CharWidget())
        balance_sheet_account_apc = fields.Field(column_name='balance_sheet_account_apc', attribute=' balance_sheet_account_apc', widget=CharWidget())
        asset_class = fields.Field(column_name='Asset Class', attribute='asset_class', widget=CharWidget())
        deactivation_on = fields.Field(column_name='deactivation_on', attribute='deactivation_on', widget=CharWidget())
        additional_description = fields.Field(column_name='additional_description', attribute='additional_description', widget=CharWidget())
        serial_number = fields.Field(column_name='Serial number', attribute='serial_number', widget=CharWidget())
        cost_center = fields.Field(column_name='Cost Center', attribute='cost_center', widget=CharWidget())
        plant = fields.Field(column_name='Plant', attribute='plant', widget=CharWidget())
        asset_sub_group_1 = fields.Field(column_name='asset_sub_group_1', attribute='asset_sub_group_1', widget=CharWidget())
        asset_sub_group_2 = fields.Field(column_name='asset_sub_group_2', attribute='asset_sub_group_2', widget=CharWidget())
        asset_sub_group_3 = fields.Field(column_name='asset_sub_group_3', attribute='asset_sub_group_3', widget=CharWidget())
        asset_status_1 = fields.Field(column_name='asset_status_1', attribute='asset_status_1', widget=CharWidget())
        asset_status_2 = fields.Field(column_name='asset_status_2', attribute='asset_status_2', widget=CharWidget())
        asset_status = fields.Field(column_name='asset_status', attribute='asset_status', widget=CharWidget())
        asset_super_number = fields.Field(column_name='asset_super_number', attribute='asset_super_number', widget=CharWidget())
        useful_life = fields.Field(column_name='Useful Life', attribute='useful_life', widget=CharWidget())
        scrap_value = fields.Field(column_name='Scrap value', attribute='scrap_value', widget=CharWidget())
        
        class Meta:
            model = AR01
            import_id_fields = ('asset','sub_number','type_name',)
            export_order = fields
            skip_unchanged = True
            report_skipped = True

@admin.register(AR01)
class AR01Admin(ImportExportModelAdmin):
    resource_class = AR01Resource
    list_display = (
            'asset','sub_number','capitalized_on','asset_description',
            'acquisition_value','accumulated_depreciation','book_value',
            'currency','type_name','company_code','business_area','balance_sheet_item',
            'balance_sheet_account_apc','asset_class','deactivation_on','additional_description',
            'serial_number','cost_center',
    )
    search_fields = ('type_name',)
    list_filter = ('type_name',)
    list_per_page = 5
#==================================================================================
#-------resources & Register ImporExport HistoryReplacementComponentResource--------------------------------------
#==================================================================================
class CustomDateWidget(Widget):
    def __init__(self, formats=None):
        # Tambahkan format baru dan ubah urutan untuk memprioritaskan format yang Anda butuhkan
        self.formats = formats or [
            '%m/%d/%Y',  # Format untuk 7/30/2025 dan 9/1/2010
            '%Y-%m-%d %H:%M:%S',  # Format untuk 2025-07-31 00:00:00
            '%Y-%m-%d',
            '%d-%m-%Y',
            '%Y/%m/%d'
        ]

    # Tambahkan **kwargs untuk menerima argumen tambahan seperti 'file_name'
    def clean(self, value, row=None, **kwargs):
        # Tambahkan penanganan untuk nilai kosong atau None di awal
        if value is None or not str(value).strip():
            return None
        
        # Mengkonversi nilai ke string agar bisa diproses oleh strptime
        value = str(value).strip()

        # Tambahkan penanganan khusus untuk nilai waktu kosong seperti '00:00:00'
        # Jika nilai hanya berisi waktu, kembalikan None
        try:
            # Coba parsing sebagai waktu saja
            datetime.strptime(value, '%H:%M:%S')
            return None  # Jika berhasil, ini adalah waktu kosong, jadi kita kembalikan None
        except (ValueError, TypeError):
            # Jika parsing gagal, lanjutkan ke format tanggal
            pass

        # Coba setiap format tanggal yang tersedia
        for f in self.formats:
            try:
                # Mengubah string menjadi objek datetime
                return datetime.strptime(value, f).date()
            except (ValueError, TypeError):
                # Jika parsing gagal, lanjutkan ke format berikutnya
                continue
        
        raise ValueError("Value could not be parsed as a date with any of the defined formats: {}".format(value))


class HistoryReplacementComponentResource(resources.ModelResource):

    jobsite_code = fields.Field(column_name='JobsiteCode', attribute='jobsite_code', widget=CharWidget())
    equipment_code = fields.Field(column_name='EquipmentCode', attribute='equipment_code', widget=CharWidget())
    equipment_model = fields.Field(column_name='EquipmentModel', attribute='equipment_model', widget=CharWidget())
    activity_name = fields.Field(column_name='ActivityName', attribute='activity_name', widget=CharWidget())
    activity_type = fields.Field(column_name='ActivityType', attribute='activity_type', widget=CharWidget())
    component = fields.Field(column_name='Component', attribute='component', widget=CharWidget())
    history_date = fields.Field(column_name='HistoryDate', attribute='history_date', widget=CustomDateWidget())
    hm_replacement = fields.Field(column_name='HM Replacement', attribute='hm_replacement', widget=DecimalWidget())
    hm_reading_date = fields.Field(column_name='HM Reading Date', attribute='hm_reading_date', widget=CustomDateWidget())
    hm_reading = fields.Field(column_name='HM Reading', attribute='hm_reading', widget=DecimalWidget())
    life_time = fields.Field(column_name='Life Time', attribute='life_time', widget=DecimalWidget())

 # # PERBAIKAN UTAMA: Tambahkan **kwargs ke dalam argumen metode
    def before_save_instance(self, instance,row,**kwargs):
        # Pastikan kedua nilai (hm_reading dan hm_replacement) ada
        if instance.hm_reading is not None and instance.hm_replacement is not None:
            # Lakukan perhitungan dan simpan hasilnya di kolom life_time
            instance.life_time = instance.hm_reading - instance.hm_replacement
        else:
            # Jika salah satu nilai tidak ada, atur life_time menjadi None
            instance.life_time = None

    class Meta:
        model = HistoryReplacementComponent
        fields = (
            'jobsite_code','equipment_code','equipment_model','activity_name',
            'activity_type','component','history_date','hm_replacement','hm_reading_date',
            'hm_reading','life_time',
        )
        import_id_fields = ('jobsite_code','equipment_code','activity_name','history_date',)
        export_order = fields
        skip_unchanged = True
        report_skipped = True
@admin.register(HistoryReplacementComponent)
class HistoryReplacementComponentAdmin(ImportExportModelAdmin):
    resource_class = HistoryReplacementComponentResource
    list_display = (
            'jobsite_code','equipment_code','equipment_model','activity_name',
            'activity_type','component','history_date','hm_replacement','hm_reading_date',
            'hm_reading','life_time',           
    )
    search_fields = ('equipment_code',)
    list_filter = ('equipment_code',)
    list_per_page = 10

    # ========================================================================
    # MENGINTEGRASIKAN CSS dan JavaScript KUSTOM
    # ========================================================================
    class Media:
        # Menentukan berkas statis yang akan disertakan di halaman admin
        # Berkas ini akan dilampirkan ke bagian <head> dari halaman.
        
        # Contoh: Tambahkan CSS untuk garis tabel
        css = {
            # 'all' berarti berlaku untuk semua media
            'all': ('admin/css/custom_admin.css',)
        }
        
        # Contoh: Tambahkan JavaScript untuk mengubah ukuran kolom
        js = (
            # Pastikan path ini benar dan pustaka berada di direktori static Anda
            # Anda harus mengunduh pustaka colResizable dan menyimpannya di sini.
            'admin/js/colResizable-1.6.min.js',
            'admin/js/custom_table.js',
        )

#==================================================================================
#-------resources & Register ImporExport Equipment Weight--------------------------
#==================================================================================
class EquipmentWeightResource(resources.ModelResource):
    class Meta:
        model = EquipmentWeight
        fields = (
            'equipment_type','egi','brand','weight','lenght','wide','height',
        )
        import_id_fields = ('equipment_type','egi',)
        export_order = fields
        skip_unchanged = True
        report_skipped = True

@admin.register(EquipmentWeight)
class EquipmentWeightAdmin(ImportExportModelAdmin):
    resource_class = EquipmentWeightResource
    list_display = (
        'equipment_type','egi','brand','weight','lenght','wide','height',
    )

    search_fields = ('equipment_type','egi',)
    list_filter = ('equipment_type','egi',)
    list_per_page = 5

#==================================================================================
#-------resources & Register ImporExport pop -------------------------
#==================================================================================
# Buat DateWidget kustom untuk menangani berbagai format dan nilai kosong
# Buat Widget Tanggal kustom yang akan mencoba memparsing berbagai format
# Perbarui CustomDateWidget untuk menerima argumen keyword tambahan
class CustomDateWidget(Widget):
    def __init__(self, formats=None):
        # Tambahkan format baru dan ubah urutan untuk memprioritaskan format yang Anda butuhkan
        self.formats = formats or [
            '%m/%d/%Y',  # Format untuk 7/30/2025 dan 9/1/2010
            '%Y-%m-%d %H:%M:%S',  # Format untuk 2025-07-31 00:00:00
            '%Y-%m-%d',
            '%d-%m-%Y',
            '%Y/%m/%d'
        ]

    # Tambahkan **kwargs untuk menerima argumen tambahan seperti 'file_name'
    def clean(self, value, row=None, **kwargs):
        if not value:
            return None
        
        # Mengkonversi nilai ke string agar bisa diproses oleh strptime
        value = str(value).strip()

        # Tambahkan penanganan khusus untuk nilai waktu kosong seperti '00:00:00'
        # Jika nilai hanya berisi waktu, kembalikan None
        try:
            # Coba parsing sebagai waktu saja
            datetime.strptime(value, '%H:%M:%S')
            return None  # Jika berhasil, ini adalah waktu kosong, jadi kita kembalikan None
        except (ValueError, TypeError):
            # Jika parsing gagal, lanjutkan ke format tanggal
            pass

        # Coba setiap format tanggal yang tersedia
        for f in self.formats:
            try:
                # Mengubah string menjadi objek datetime
                return datetime.strptime(value, f).date()
            except (ValueError, TypeError):
                # Jika parsing gagal, lanjutkan ke format berikutnya
                continue
        
        raise ValueError("Value could not be parsed as a date with any of the defined formats: {}".format(value))


class popResource(resources.ModelResource):          
    equipment_cn_sap = fields.Field(column_name='SAP EQP NUM',attribute='equipment_cn_sap',widget=CharWidget())    
    equipment_activity = fields.Field(column_name='EQP ACTIVITY',attribute='equipment_activity',widget=CharWidget())
    equipment_type = fields.Field(column_name='EQP TYPE',attribute='equipment_type',widget=CharWidget())
    equipment_model = fields.Field(column_name='EQP MODEL',attribute='equipment_model',widget=CharWidget())
    equipment_class = fields.Field(column_name='EQP CLASS (EGI) SAP',attribute='equipment_class',widget=CharWidget())
    equipment_cn_ellipse = fields.Field(column_name='OLD EQP NUM (MP2 & ELLIPSE)',attribute='equipment_cn_ellipse',widget=CharWidget())   
    equipment_status = fields.Field(column_name='EQP STATUS',attribute='equipment_status',widget=CharWidget())
    serial_number = fields.Field(column_name='SERIAL NUMBER',attribute='serial_number',widget=CharWidget())
    brand =fields.Field(column_name='PRODUCT',attribute='brand',widget=CharWidget())
    sales_agen = fields.Field(column_name='SALES AGEN',attribute='sales_agen',widget=CharWidget())
    location = fields.Field(column_name='DISTRICT+LOCATION',attribute='location ',widget=CharWidget())
    hm_smr_reading = fields.Field(column_name='HM/SMR (READING)',attribute='hm_smr_reading',widget=CharWidget())
    hm_smr_reading_date = fields.Field(column_name='LAST UP DATE HM/SMR (READING)',attribute='hm_smr_reading_date',widget=CustomDateWidget())
    hm_cuml_reading = fields.Field(column_name='HM/SMR (CUMULATIVE)',attribute='hm_cuml_reading',widget=CharWidget())
    hm_cuml_reding_date = fields.Field(column_name='LAST UP DATE HM/SMR (CUMULATIVE)',attribute='hm_cuml_reding_date',widget=CustomDateWidget())
    site_received_date = fields.Field(column_name='1st DATE of RECEIVED ON SITE',attribute='site_received_date',widget=CustomDateWidget())
    month_do_date = fields.Field(column_name='MONTH DO',attribute='month_do_date',widget=DateWidget())
    year_do = fields.Field(column_name='YEAR DO',attribute='year_do',widget=IntegerWidget())
    owner = fields.Field(column_name='OWNER',attribute='owner',widget=CharWidget())
    fmc = fields.Field(column_name='FMC ?',attribute='fmc',widget=CharWidget())
    plant_code = fields.Field(column_name='MAINT PLANT (DISTRICT)',attribute='plant_code',widget=CharWidget())
    functional_location = fields.Field(column_name='FUNCTIONAL LOCATION',attribute='functional_location',widget=CharWidget())
    asset_number = fields.Field(column_name='ASSET NUMBER',attribute='asset_number',widget=CharWidget())

    class Meta :
        model = pop
        fields = (
           'equipment_activity','equipment_type','equipment_model',
            'equipment_class','equipment_cn_ellipse','equipment_cn_sap','equipment_status','serial_number','brand',
            'sales_agen','location','hm_smr_reading','hm_smr_reading_date','hm_cuml_reading','hm_cuml_reding_date',
            'site_received_date','month_do_date','year_do','owner','fmc','plant_code','functional_location','asset_number',
        )
        import_id_fields = ('equipment_cn_sap',)
        export_order = fields
        skip_unchanged = True
        report_skipped = True

@admin.register(pop)
class popAdmin(ImportExportModelAdmin):
    resource_class = popResource
    list_display = (
            'equipment_activity','equipment_type','equipment_model',
            'equipment_class','equipment_cn_ellipse','equipment_cn_sap','equipment_status','serial_number','brand',
            'sales_agen','location','hm_smr_reading','hm_smr_reading_date','hm_cuml_reading','hm_cuml_reding_date',
            'site_received_date','month_do_date','year_do','owner','fmc','plant_code','functional_location','asset_number',
    )
    search_fields = ('equipment_type','equipment_cn_sap',)
    list_filter = ('equipment_type','equipment_cn_sap',)
    list_per_page=5

#=================================================================================
#--------Register EGI Obsolete----------------------------------------------------
#=================================================================================
class egiobsoleteresource(resources.ModelResource):
    EGI = fields.Field(column_name="EGI", attribute="EGI", widget=CharWidget())
    TYPE = fields.Field(column_name="TYPE", attribute="TYPE", widget=CharWidget())
    DISCONTINUE = fields.Field(column_name="DISCONTINUE", attribute="DISCONTINUE", widget=CharWidget())
    NEW_GENERATION = fields.Field(column_name="NEW_GENERATION", attribute="NEW_GENERATION", widget=CharWidget())
    BRAND = fields.Field(column_name="BRAND", attribute="BRAND", widget=CharWidget())
    REMARKS = fields.Field(column_name="REMARKS", attribute="REMARKS", widget=CharWidget())
    
    class Meta:
        model = egiobsolete
        fields= ('EGI', 'TYPE', 'DISCONTINUE', 'NEW_GENERATION', 'BRAND','REMARKS',)
        import_id_fields = ('EGI',)
        export_order = fields
        skip_unchanged = True
        report_skipped = True

@admin.register(egiobsolete)
class egiobsoleteAdmin(ImportExportModelAdmin):
    resource_class = egiobsoleteresource
    list_display = ('EGI', 'TYPE', 'DISCONTINUE', 'NEW_GENERATION', 'BRAND','REMARKS',) 
    search_fields = ('EGI',)
    list_filter = ('EGI','TYPE',)
    list_per_page=5

#================================================================================
#---register InspectionMasterItem------------------------------------------------
#===============================================================================
class checksheetmasterlistresource(resources.ModelResource):
    EGI = fields.Field(column_name="EGI", attribute="EGI", widget=CharWidget())
    CATEGORY = fields.Field(column_name="CATEGORY", attribute="CATEGORY", widget=CharWidget())
    ITEM = fields.Field(column_name="ITEM", attribute="ITEM", widget=CharWidget())
    QTY = fields.Field(column_name="QTY", attribute="QTY", widget=CharWidget())
    REMARKS = fields.Field(column_name="EGI", attribute="EGI", widget=CharWidget())

    class Meta:
        model = checksheetmasterlist
        fields = ('EGI', 'CATEGORY', 'ITEM', 'QTY', 'REMARKS',)
        import_id_fields = ()
        export_order = fields
        skip_unchanged = True
        report_skipped = True

@admin.register(checksheetmasterlist)
class checksheetmasterlistAdmin(ImportExportModelAdmin):
    resource_class = checksheetmasterlistresource
    list_display = ('EGI', 'CATEGORY', 'ITEM', 'QTY', 'REMARKS',)
    search_fields = ('EGI',)
    list_filter = ('EGI','CATEGORY',)
    list_per_page = 5


class CleanedDecimalWidget(DecimalWidget):
    def clean(self, value, row=None, **kwargs):
        if value is None:
            return None
        
        # Ubah ke string dan bersihkan spasi di ujung-ujungnya
        val_str = str(value).strip()
        
        # Jika berisi tanda strip, N/A, atau kosong, kembalikan None (NULL di database)
        if val_str in ['-', 'N/A', 'None', '']:
            return None
            
        # Hilangkan simbol '%' jika ada (misal "0%" menjadi "0", "85%" menjadi "85")
        if '%' in val_str:
            val_str = val_str.replace('%', '').strip()
            
        # Panggil fungsi clean bawaan menggunakan nilai yang sudah bersih
        return super().clean(val_str, row, **kwargs)

# ================================================================================
# ========= Pendaftaran fungsi dan class CONMON ===================================
# ================================================================================
class conmonresource(resources.ModelResource):
    LOCATION = fields.Field(column_name="Jobsite", attribute="LOCATION", widget=CharWidget())
    EGI = fields.Field(column_name="Model Type", attribute="EGI", widget=CharWidget())
    EQP_TYPE = fields.Field(column_name="Equipment Type", attribute="EQP_TYPE", widget=CharWidget())
    CN_SAP = fields.Field(column_name="Equipment Number", attribute="CN_SAP", widget=CharWidget()) 
    SN = fields.Field(column_name="Equipment Serial number", attribute="SN", widget=CharWidget())
    COMPONENT = fields.Field(column_name="Component", attribute="COMPONENT", widget=CharWidget())
    LIFETIME = fields.Field(column_name="Lifetime Comp", attribute="LIFETIME", widget=CharWidget())
    SPO = fields.Field(column_name="SPO", attribute="SPO", widget=CharWidget())
    EQP_HEALTH = fields.Field(column_name="Equipment Health", attribute="EQP_HEALTH", widget=CleanedDecimalWidget())
    EQP_STATUS_HEALTH = fields.Field(column_name="EQP_STATUS_HEALTH", attribute="EQP_STATUS_HEALTH", widget=CharWidget())
    COMP_HEALTH = fields.Field(column_name="Component Health", attribute="COMP_HEALTH", widget=CleanedDecimalWidget())
    COMP_STATUS_HEALTH = fields.Field(column_name="COMP_STATUS_HEALTH", attribute="COMP_STATUS_HEALTH", widget=CharWidget())

    class Meta:
        model = conmon
        # Sesuai diskusi sebelumnya, pastikan composite key aktif jika satu unit punya banyak komponen
        fields = ('LOCATION','EGI','EQP_TYPE','CN_SAP','SN','COMPONENT','LIFETIME','SPO','EQP_HEALTH','EQP_STATUS_HEALTH','COMP_HEALTH','COMP_STATUS_HEALTH',)
        import_id_fields = ['CN_SAP', 'COMPONENT'] 
        export_order = fields
        skip_unchanged = True
        report_skipped = True


@admin.register(conmon)
class conmonAdmin(ImportExportModelAdmin):
    resource_class = conmonresource
    
    # 1. 🔥 GANTI 'COMP_HEALTH' dengan 'show_health_percentage' di baris list_display
    list_display = ('LOCATION','EGI','EQP_TYPE','CN_SAP','SN','COMPONENT','LIFETIME','SPO','show_eqp_health_percentage','EQP_STATUS_HEALTH','show_comp_health_percentage','COMP_STATUS_HEALTH',)
    search_fields = ('LOCATION', 'EGI', 'CN_SAP',)
    list_filter = ('LOCATION', 'EGI', 'CN_SAP',)
    list_per_page = 25

    # 2. 🔥 TAMBAHKAN LOGIKA CUSTOM METHOD PERSENTASE DI BAWAH INI
    def show_comp_health_percentage(self, obj):
        if obj.COMP_HEALTH is not None:
            try:
                # Mengubah nilai float database (misal 0.85 atau 1.0) menjadi nilai persentase (85 atau 100)
                val = float(obj.COMP_HEALTH)
                # Jika hasilnya bilangan bulat (misal 100.0), hilangkan .0 nya menjadi 100%
                if val.is_integer():
                    return f"{int(val)}%"
                # Jika desimal (misal 85.5), tampilkan satu digit di belakang koma (85.5%)
                return f"{val:.2f}%"
            except (ValueError, TypeError):
                return f"{obj.COMP_HEALTH}%"
        return "-"
    
    # Menyetel label nama kolom di header tabel Django Admin
    show_comp_health_percentage.short_description = "COMP HEALTH"
    # Mengizinkan kolom ini bisa di-sorting berdasarkan nilai asli numeriknya di database
    show_comp_health_percentage.admin_order_field = "COMP_HEALTH"
    
    # 2. 🔥 TAMBAHKAN LOGIKA CUSTOM METHOD PERSENTASE DI BAWAH INI
    def show_eqp_health_percentage(self, obj):
        if obj.EQP_HEALTH is not None:
            try:
                # Mengubah nilai float database (misal 0.85 atau 1.0) menjadi nilai persentase (85 atau 100)
                val = float(obj.EQP_HEALTH)
                # Jika hasilnya bilangan bulat (misal 100.0), hilangkan .0 nya menjadi 100%
                if val.is_integer():
                    return f"{int(val)}%"
                # Jika desimal (misal 85.5), tampilkan satu digit di belakang koma (85.5%)
                return f"{val:.2f}%"
            except (ValueError, TypeError):
                return f"{obj.EQP_HEALTH}%"
        return "-"
    
    # Menyetel label nama kolom di header tabel Django Admin
    show_eqp_health_percentage.short_description = "EQP HEALTH"
    # Mengizinkan kolom ini bisa di-sorting berdasarkan nilai asli numeriknya di database
    show_eqp_health_percentage.admin_order_field = "EQP_HEALTH"
    

class directcostresource(resources.ModelResource):
    LOCATION = fields.Field(column_name="Chart of Accounts", attribute="LOCATION", widget=CharWidget())
    YEAR = fields.Field(column_name="Fiscal Year", attribute="YEAR", widget=CharWidget())
    DATE = fields.Field(column_name="Posting Date", attribute="DATE", widget=CharWidget())
    DOCUMENT = fields.Field(column_name="Document Number", attribute="DOCUMENT", widget=CharWidget())
    COMP_CODE_CURR = fields.Field(column_name="Company Code Currency Value", attribute="COMP_CODE_CURR", widget=CharWidget())
    FUNC_AREA = fields.Field(column_name="Functional Area: Text", attribute="FUNC_AREA", widget=CharWidget())
    GL_ACCOUNT = fields.Field(column_name="G/L Account", attribute="GL_ACCOUNT", widget=CharWidget())
    GL_ACCOUNT_TEXT = fields.Field(column_name="G/L Account: Short Text", attribute="GL_ACCOUNT_TEXT", widget=CharWidget())
    MATERIAL = fields.Field(column_name="Material", attribute="MATERIAL", widget=CharWidget())
    MATERIAL_DESC = fields.Field(column_name="Material: Description", attribute="MATERIAL_DESC", widget=CharWidget())
    CN_SAP = fields.Field(column_name="Equipment", attribute="CN_SAP", widget=CharWidget())

    class Meta:
        model = directcost
        fields = ('LOCATION','YEAR','DATE','DOCUMENT','COMP_CODE_CURR','FUNC_AREA','GL_ACCOUNT','GL_ACCOUNT_TEXT','MATERIAL','MATERIAL_DESC','CN_SAP',)
        import_id_fields = ['DATE','DOCUMENT','CN_SAP']
        export_order = fields
        skip_unchanged = True
        report_skipped = True

@admin.register(directcost)
class directcostAdmin(ImportExportModelAdmin):
    resource_class = directcostresource
    list_display = ('LOCATION','YEAR','DATE','DOCUMENT','COMP_CODE_CURR','FUNC_AREA','GL_ACCOUNT','GL_ACCOUNT_TEXT','MATERIAL','MATERIAL_DESC','CN_SAP',)
    search_fields = ('LOCATION','CN_SAP',)
    list_filter = ('LOCATION','CN_SAP',)
    list_per_page = 10


#=================================================================================
#======= Pendaftaran class IH08 ==================================================
#=================================================================================

class IH08resource(resources.ModelResource):
    CN_SAP = fields.Field(column_name="Equipment", attribute="CN_SAP", widget=CharWidget())
    LOCATION = fields.Field(column_name="MaintPlant", attribute="LOCATION", widget=CharWidget())
    EGI = fields.Field(column_name="Model number", attribute="EGI", widget=CharWidget())
    SN = fields.Field(column_name="Manuf. SerialNr", attribute="SN", widget=CharWidget())
    MANUFACTURE = fields.Field(column_name="Manufacturer", attribute="MANUFACTURE", widget=CharWidget())
    STATUS = fields.Field(column_name="User status", attribute="STATUS", widget=CharWidget())
    
    class Meta:
        model = IH08
        fields = ('CN_SAP','LOCATION','EGI','SN','MANUFACTURE','STATUS',)
        import_id_fields = ['CN_SAP','LOCATION',]
        export_order = fields
        skip_unchanged = True
        report_skipped = True

@admin.register(IH08)
class IH08Admin(ImportExportModelAdmin):
    resource_class = IH08resource
    list_display = ('CN_SAP','LOCATION','EGI','SN','MANUFACTURE','STATUS',)
    search_fields = ('CN_SAP','LOCATION','EGI','STATUS',)
    list_filter = ('CN_SAP','LOCATION','EGI','MANUFACTURE','STATUS',)
    list_per_page = 10


@admin.register(KaryawanPenerimaNotifikasi)
class KaryawanPenerimaNotifikasiAdmin(admin.ModelAdmin):
    list_display = ("nama", "email", "is_active")
    list_filter = ("is_active",)
    search_fields = ("nama", "email")

    # Mengelompokkan field di halaman detail admin agar rapi
    fieldsets = (
        ('Informasi Karyawan', {
            'fields': ('nama', 'email', 'is_active')
        }),
        ('Langganan Dokumen Notifikasi (Matrix)', {
            'fields': (
                'notif_ba_breakdown', 'notif_ba_standby', 'notif_foto_4_sisi',
                'notif_inspeksi', 'notif_rca', 'notif_pengajuan_disposed',
                'notif_lampiran_capex', 'notif_pde','notif_summary_pde','notif_waiting_prepare','notif_approved_prepare',
            )
        }),
    )
    

from django.contrib import admin
from import_export.admin import ImportExportModelAdmin
from .models import InspectionTemplateItem

class InspectionTemplateItemresource(resources.ModelResource):

    TYPE = fields.Field(column_name="EQUIPMENT TYPE", attribute="TYPE", widget=CharWidget())
    EGI  = fields.Field(column_name="EGI", attribute="EGI", widget=CharWidget())
    ITEM_GROUP = fields.Field(column_name="ITEM GROUP", attribute="ITEM_GROUP", widget=CharWidget())
    ITEM_NAME = fields.Field(column_name="ITEM NAME", attribute="ITEM_NAME", widget=CharWidget())
    QTY = fields.Field(column_name="QTY", attribute="QTY", widget=CharWidget())
    
    
    class Meta:
        model = InspectionTemplateItem
        fields = ('TYPE','EGI','ITEM_GROUP','ITEM_NAME','QTY',)
        import_id_fields = ['TYPE','EGI','ITEM_GROUP','ITEM_NAME',]
        export_order = fields
        skip_unchanged = True
        report_skipped = True

@admin.register(InspectionTemplateItem, site=admin_site)
class InspectionTemplateItemAdmin(ImportExportModelAdmin):
    
    resource_class = InspectionTemplateItemresource
    list_display = ('TYPE','EGI','ITEM_GROUP','ITEM_NAME','QTY',)
    list_filter = ('TYPE','EGI','ITEM_GROUP','ITEM_NAME','QTY',)
    search_fields = ('TYPE','EGI','ITEM_GROUP','ITEM_NAME','QTY',)
    list_per_page = 20



#==================================================================================
#-------Register Views ke Amdin_site --------------------------------------
#==================================================================================


admin_site.register(MPS,MPSAdmin)
admin_site.register(AR01,AR01Admin)
admin_site.register(HistoryReplacementComponent,HistoryReplacementComponentAdmin)
admin_site.register(EquipmentWeight,EquipmentWeightAdmin)
admin_site.register(pop,popAdmin)
admin_site.register(egiobsolete,egiobsoleteAdmin)
admin_site.register(checksheetmasterlist,checksheetmasterlistAdmin)
admin_site.register(conmon,conmonAdmin)
admin_site.register(directcost,directcostAdmin)
admin_site.register(IH08,IH08Admin)
admin_site.register(KaryawanPenerimaNotifikasi,KaryawanPenerimaNotifikasiAdmin)