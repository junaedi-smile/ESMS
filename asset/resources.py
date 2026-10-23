from import_export import resources, fields
from import_export.widgets import DateWidget, IntegerWidget, CharWidget,ForeignKeyWidget
from .models import AssetEquipment, AssetMonthlyStatus,AssetEquipmentDisposed
from import_export import fields, resources
from import_export.widgets import FloatWidget



class AssetEquipmentResource(resources.ModelResource):
    No_Asset = fields.Field(
        column_name= 'NO ASSET',
        attribute= 'No_Asset',
        widget= CharWidget()
    )

    CN_SAP = fields.Field(
        column_name='CN SAP',
        attribute= 'CN_SAP',
        widget= CharWidget()
    )

    CN_ELLIPSE = fields.Field(
        column_name='CN ELLIPSE',
        attribute='CN_ELLIPSE',
        widget=CharWidget()
    )
    
    SUB_SITE = fields.Field(
        column_name='SUB SITE',
        attribute='SUB_SITE',
        widget=CharWidget()
    )

    HM_SMR = fields.Field(
        column_name='HM SMR',
        attribute='HM_SMR',
        widget=CharWidget()
    )
    HM_DATE = fields.Field(
        column_name='HM DATE',
        attribute='HM_DATE',
        widget=DateWidget(format='%Y-%m-%d')  # Format date saat import/export
    )

    SPO_EQUIPMENT = fields.Field(
        column_name='SPO EQUIPMENT',
        attribute='SPO_EQUIPMENT',
        widget=IntegerWidget()
    )

    PERSENTASE_SPO = fields.Field(
        column_name='PERSENTASE SPO',
        attribute='PERSENTASE_SPO',
        widget=CharWidget()
    )
    EQUIPMENT_CONDITION =fields.Field(
        column_name='EQUIPMENT CONDITION',
        attribute='EQUIPMENT_CONDITION',
        widget=CharWidget()
    )
    STATUS_EQUIPMENT=fields.Field(
        column_name='STATUS EQUIPMENT',
        attribute='STATUS_EQUIPMENT',
        widget=CharWidget()
    )
    STATUS_EQUIPMENT_DISPOSED=fields.Field(
        column_name=' STATUS EQUIPMENT DISPOSED',
        attribute=' STATUS_EQUIPMENT_DISPOSED',
        widget=CharWidget()
    )
    REFERENSI_NO_PDE=fields.Field(
        column_name='REFERENSI NO PDE',
        attribute='REFERENSI_NO_PDE',
        widget=CharWidget()
    )

    class Meta:
        model = AssetEquipment
        import_id_fields = ['CN_SAP']  # field unik untuk identifikasi saat update
        fields = (
            'No_Asset',
            'CN_SAP',
            'CN_ELLIPSE',
            'EGI',
            'TYPE',            
            'GROUP',
            'OWNERSHIP',
            'LOCATION',
            'SUB_SITE',
            'BRAND',
            'SN',
            'HM_SMR',
            'HM_DATE',
            'SPO_EQUIPMENT',
            'PERSENTASE_SPO',
            'EQUIPMENT_CONDITION',
            'STATUS_EQUIPMENT',
            'STATUS_EQUIPMENT_DISPOSED',
            'REFERENSI_NO_PDE',
        )
        export_order = fields  # urutan kolom saat export
        skip_unchanged = True
        report_skipped = True


class AssetMonthlyStatusResource(resources.ModelResource):
    def clean_HM_DATE(self, value):
        # Mengonversi "midnight" ke objek time 00:00:00 jika model HM_DATE adalah TimeField
        # Jika HM_DATE di model adalah DateField, ini harus dikonversi ke tanggal yang valid.
        # Asumsi ini tetap DateField, jadi kita harus mengembalikan tanggal yang valid atau None.
        if value is not None and str(value).strip().lower() == "midnight":
            # Jika ini adalah DateField, "midnight" tidak masuk akal.
            # Anda perlu memutuskan tanggal apa yang harus dikembalikan.
            # Untuk saat ini, jika modelnya DateField dan dapat null, kembalikan None.
            return None # Atau tanggal default yang masuk akal, misal datetime.now().date()
        return value

    # ✅ ADDED: clean method for PERSENTASE_SPO
    def clean_PERSENTASE_SPO(self, value):
        if value is None or str(value).strip() == '':
            return None  # Konversi string kosong atau None menjadi None
        try:
            # Coba konversi ke float. Jika ada koma, ganti dengan titik
            return float(str(value).replace(',', '.'))
        except ValueError:
            # Jika tidak bisa dikonversi, berikan pesan error yang jelas
            raise ValueError(f"'{value}' bukan angka yang valid untuk PERSENTASE_SPO.")


    No_Asset = fields.Field(
        column_name= 'No Asset',
        attribute= 'No_Asset',
        widget= CharWidget()
    )

    CN_SAP = fields.Field(
        column_name='Code Number',
        attribute= 'CN_SAP',
        widget= CharWidget()
    )

    CN_ELLIPSE = fields.Field(
        column_name='Code Number Ellipse',
        attribute='CN_ELLIPSE',
        widget=CharWidget()
    )

    TYPE = fields.Field(
        column_name='Type',
        attribute='TYPE',
        widget=CharWidget()
    )

    GROUP = fields.Field(
        column_name='Class Equipment',
        attribute='GROUP',
        widget=CharWidget()
    )
    
    CLASS_WEIGHT = fields.Field(
        column_name='Class Weight',
        attribute='CLASS_WEIGHT',
        widget=CharWidget()
    )

    OWNERSHIP = fields.Field(
        column_name='Ownership',
        attribute='OWNERSHIP',
        widget=CharWidget()
    )

    SECTION = fields.Field(
        column_name='Section',
        attribute='SECTION',
        widget=CharWidget()
    )

    LOCATION = fields.Field(
        column_name='Location',
        attribute='LOCATION',
        widget=CharWidget()
    )

    SUB_SITE = fields.Field(
        column_name='Sub Site',
        attribute='SUB_SITE',
        widget=CharWidget()
    )

    SUB_LOCATION = fields.Field(
        column_name='Sub Location',
        attribute='SUB_LOCATION',
        widget=CharWidget()
    )

    BRAND = fields.Field(
        column_name='Brand',
        attribute='BRAND',
        widget=CharWidget()
    )

    SN = fields.Field(
        column_name='Serial Number',
        attribute='SN',
        widget=CharWidget()
    )

    HM_SMR = fields.Field(
        column_name='Hour Meter',
        attribute='HM_SMR',
        widget=CharWidget()
    )
    HM_DATE = fields.Field(
        column_name='Hour Meter Date',
        attribute='HM_DATE',
        widget=DateWidget(format='%Y-%m-%d')  # Format date saat import/export
    )

    SPO_EQUIPMENT = fields.Field(
        column_name='SPO Equipment',
        attribute='SPO_EQUIPMENT',
        widget=IntegerWidget()
    )

    PERSENTASE_SPO = fields.Field(
        column_name='% SPO Equipment',
        attribute='PERSENTASE_SPO',
        widget=CharWidget() # Tetap gunakan CharWidget untuk membaca sebagai string
    )
    EQUIPMENT_CONDITION =fields.Field(
        column_name='Equipment Condition',
        attribute='EQUIPMENT_CONDITION',
        widget=CharWidget()
    )
    STATUS_EQUIPMENT=fields.Field(
        column_name='Status Equipment',
        attribute='STATUS_EQUIPMENT',
        widget=CharWidget()
    )
    STATUS_EQUIPMENT_DISPOSED=fields.Field(
        column_name=' Status Equipment Disposed', # Perhatikan spasi di awal nama kolom, bisa jadi masalah
        attribute=' STATUS_EQUIPMENT_DISPOSED', # Perhatikan spasi di awal attribute, bisa jadi masalah
        widget=CharWidget()
    )
    REFERENSI_NO_PDE=fields.Field(
        column_name='Referensi No PDE',
        attribute='REFERENSI_NO_PDE',
        widget=CharWidget()
    )

    YEAR= fields.Field(
        column_name='Year',
        attribute='YEAR',
        widget=IntegerWidget()
    )

    MONTH= fields.Field(
        column_name='Month',
        attribute='MONTH',
        widget=DateWidget(format='%Y-%m-%d')
    )

    class Meta:
        model = AssetMonthlyStatus
        import_id_fields = ['CN_SAP']  # field unik untuk identifikasi saat update
        fields = (
            'No_Asset',
            'CN_SAP',
            'CN_ELLIPSE',
            'EGI',
            'TYPE',
            'GROUP',
            'CLASS_WEIGHT',
            'OWNERSHIP',
            'SECTION',
            'LOCATION',
            'SUB_SITE',
            'SUB_LOCATION',
            'BRAND',
            'SN',
            'HM_SMR',
            'HM_DATE',
            'SPO_EQUIPMENT',
            'PERSENTASE_SPO',
            'EQUIPMENT_CONDITION',
            'STATUS_EQUIPMENT',
            'STATUS_EQUIPMENT_DISPOSED',
            'REFERENSI_NO_PDE',
            'YEAR',
            'MONTH'
        )
        export_order = fields  # urutan kolom saat export
        skip_unchanged = True
        report_skipped = True

#=============================================
#-------AssetEquipmentDisposed-----------------

class AssetEquipmentDisposedResource(resources.ModelResource):
    No_Asset = fields.Field(
        column_name= 'NO ASSET',
        attribute= 'No_Asset',
        widget= CharWidget()
    )

    CN_SAP = fields.Field(
        column_name='CN SAP',
        attribute= 'CN_SAP',
        widget= CharWidget()
    )

    CN_ELLIPSE = fields.Field(
        column_name='CN ELLIPSE',
        attribute='CN_ELLIPSE',
        widget=CharWidget()
    )
    
    SUB_SITE = fields.Field(
        column_name='SUB SITE',
        attribute='SUB_SITE',
        widget=CharWidget()
    )

    HM_SMR = fields.Field(
        column_name='HM SMR',
        attribute='HM_SMR',
        widget=CharWidget()
    )
    HM_DATE = fields.Field(
        column_name='HM DATE',
        attribute='HM_DATE',
        widget=DateWidget(format='%Y-%m-%d')  # Format date saat import/export
    )

    SPO_EQUIPMENT = fields.Field(
        column_name='SPO EQUIPMENT',
        attribute='SPO_EQUIPMENT',
        widget=IntegerWidget()
    )

    PERSENTASE_SPO = fields.Field(
        column_name='PERSENTASE SPO',
        attribute='PERSENTASE_SPO',
        widget=CharWidget()
    )
    EQUIPMENT_CONDITION =fields.Field(
        column_name='EQUIPMENT CONDITION',
        attribute='EQUIPMENT_CONDITION',
        widget=CharWidget()
    )
    STATUS_EQUIPMENT=fields.Field(
        column_name='STATUS EQUIPMENT',
        attribute='STATUS_EQUIPMENT',
        widget=CharWidget()
    )
    STATUS_EQUIPMENT_DISPOSED=fields.Field(
        column_name=' STATUS EQUIPMENT DISPOSED',
        attribute=' STATUS_EQUIPMENT_DISPOSED',
        widget=CharWidget()
    )
    REFERENSI_NO_PDE=fields.Field(
        column_name='REFERENSI NO PDE',
        attribute='REFERENSI_NO_PDE',
        widget=CharWidget()
    )

    class Meta:
        model = AssetEquipmentDisposed
        import_id_fields = ['CN_SAP']  # field unik untuk identifikasi saat update
        fields = (
            'No_Asset',
            'CN_SAP',
            'CN_ELLIPSE',
            'EGI',
            'TYPE',            
            'GROUP',
            'OWNERSHIP',
            'LOCATION',
            'SUB_SITE',
            'BRAND',
            'SN',
            'HM_SMR',
            'HM_DATE',
            'SPO_EQUIPMENT',
            'PERSENTASE_SPO',
            'EQUIPMENT_CONDITION',
            'STATUS_EQUIPMENT',
            'STATUS_EQUIPMENT_DISPOSED',
            'REFERENSI_NO_PDE',
        )
        export_order = fields  # urutan kolom saat export
        skip_unchanged = True
        report_skipped = True