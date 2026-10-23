#data/models.py

from django.db import models
from django.db.models.signals import pre_save
from django.dispatch import receiver

# Create your models here.
class MPS(models.Model):
    JobsiteCode     = models.CharField(max_length=20, verbose_name='Kode Lokasi')
    ModelName       = models.CharField(max_length=50, verbose_name='Nama Model')
    TypeName        = models.CharField(max_length=50, verbose_name='Nama Tipe')
    ComponentName   = models.CharField(max_length=100, verbose_name='Nama Komponen')
    ActivityName    = models.CharField(max_length=100, verbose_name='Nama Aktivitas')
    FirstLife       = models.IntegerField(verbose_name='First Life (Jam)', null=True, blank=True)
    SecondLife      = models.IntegerField(verbose_name='Second Life (Jam)', null=True, blank=True)
    PartNumber      = models.CharField(max_length=50, verbose_name='Nomor Suku Cadang')
    Description     = models.TextField(verbose_name='Deskripsi')
    Brand           = models.CharField(max_length=50, verbose_name='Merk')
    COA             = models.CharField(max_length=50, verbose_name='COA', null=True, blank=True)
    COADesc         = models.CharField(max_length=100, verbose_name='Deskripsi COA', null=True, blank=True)
    GLGroup         = models.CharField(max_length=50, verbose_name='GL Group', null=True, blank=True)
    Price           = models.DecimalField(max_digits=15, decimal_places=2, verbose_name='Harga')
    IsMajorPart     = models.BooleanField(default=False, verbose_name='Apakah Suku Cadang Utama?')
    Qty             = models.IntegerField(verbose_name='Kuantitas')
    isCapitalized   = models.BooleanField(default=False, verbose_name='Apakah Dikapitalisasi?')
    Amount          = models.DecimalField(max_digits=15, decimal_places=2, verbose_name='Jumlah')

    class Meta:
        verbose_name = "MPS"
        verbose_name_plural = "MPS"

    def __str__(self):
        return f"{self.ComponentName} - {self.PartNumber}"
    

class AR01(models.Model):
    asset                       = models.CharField(max_length=50)
    sub_number                  = models.CharField(max_length=50, blank=True, null=True)
    capitalized_on              = models.DateField(blank=True, null=True)
    asset_description           = models.TextField(blank=True, null=True)
    acquisition_value           = models.DecimalField(max_digits=20, decimal_places=2, blank=True, null=True)
    accumulated_depreciation    = models.DecimalField(max_digits=20, decimal_places=2, blank=True, null=True)
    book_value                  = models.DecimalField(max_digits=20, decimal_places=2, blank=True, null=True)
    currency                    = models.CharField(max_length=10, blank=True, null=True)
    type_name                   = models.CharField(max_length=100, blank=True, null=True)
    company_code                = models.CharField(max_length=10, blank=True, null=True)
    business_area               = models.CharField(max_length=50, blank=True, null=True)
    balance_sheet_item          = models.CharField(max_length=100, blank=True, null=True)
    balance_sheet_account_apc   = models.CharField(max_length=100, blank=True, null=True)
    asset_class                 = models.CharField(max_length=100, blank=True, null=True)
    deactivation_on             = models.DateField(blank=True, null=True)
    additional_description      = models.TextField(blank=True, null=True)
    serial_number               = models.CharField(max_length=100, blank=True, null=True)
    cost_center                 = models.CharField(max_length=100, blank=True, null=True)
    plant                       = models.CharField(max_length=100, blank=True, null=True)
    asset_sub_group_1           = models.CharField(max_length=100, blank=True, null=True)
    asset_sub_group_2           = models.CharField(max_length=100, blank=True, null=True)
    asset_sub_group_3           = models.CharField(max_length=100, blank=True, null=True)
    asset_status_1              = models.CharField(max_length=50, blank=True, null=True)
    asset_status_2              = models.CharField(max_length=50, blank=True, null=True)
    asset_status                = models.CharField(max_length=50, blank=True, null=True)
    asset_super_number          = models.CharField(max_length=100, blank=True, null=True)
    useful_life                 = models.IntegerField(blank=True, null=True)
    scrap_value                 = models.DecimalField(max_digits=20, decimal_places=2, blank=True, null=True)

    class Meta:
        db_table = "AR01"
        verbose_name = "AR01"
        verbose_name_plural = "AR01"

    def __str__(self):
        return f"{self.asset} - {self.asset_description}"

class HistoryReplacementComponent(models.Model):
    jobsite_code        = models.CharField(max_length=50)
    equipment_code      = models.CharField(max_length=50)
    equipment_model     = models.CharField(max_length=100, blank=True, null=True)
    activity_name       = models.CharField(max_length=100, blank=True, null=True)
    activity_type       = models.CharField(max_length=50, blank=True, null=True)
    component           = models.CharField(max_length=150, blank=True, null=True)
    history_date        = models.DateField(blank=True, null=True)
    hm_replacement      = models.DecimalField(max_digits=20, decimal_places=2, blank=True, null=True)
    hm_reading_date     = models.DateField(blank=True, null=True)
    hm_reading          = models.DecimalField(max_digits=20, decimal_places=2, blank=True, null=True)
    life_time           = models.DecimalField(max_digits=20, decimal_places=2, blank=True, null=True)

    class Meta:
        db_table = "history_replacement_component"
        verbose_name = "Replace Component"
        verbose_name_plural = "Replace Component"

    def __str__(self):
        return f"{self.equipment_code} - {self.component} ({self.history_date})"
    
class EquipmentWeight(models.Model):
    equipment_type = models.CharField(max_length=255, blank=True, null=True)
    egi = models.CharField(max_length=255, blank=True, null=True)
    brand = models.CharField(max_length=255, blank=True, null=True)
    weight = models.DecimalField(max_digits=20,decimal_places=2, blank=True, null=True)
    lenght = models.DecimalField(max_digits=20,decimal_places=2, blank=True, null=True)
    wide = models.DecimalField(max_digits=20,decimal_places=2, blank=True, null=True)
    height = models.DecimalField(max_digits=20,decimal_places=2, blank=True, null=True)

    class Meta:
        db_table = "Equipment_Weight"
        verbose_name =  "Equipment Weight"
        verbose_name_plural =  "Equipment Weight"
    def __str__(self):
        return f"{self.equipment_type} - {self.egi}"


class pop(models.Model):
    equipment_cn_sap = models.CharField(max_length=255, blank=True, null=True)    
    equipment_activity = models.CharField(max_length=255, blank=True, null=True)
    equipment_type = models.CharField(max_length=255, blank=True, null=True)
    equipment_model = models.CharField(max_length=255, blank=True, null=True)
    equipment_class = models.CharField(max_length=255, blank=True, null=True)
    equipment_cn_ellipse = models.CharField(max_length=255, blank=True, null=True)    
    equipment_status = models.CharField(max_length=255, blank=True, null=True)
    serial_number = models.CharField(max_length=100, blank=True, null=True)
    brand = models.CharField(max_length=100, blank=True, null=True)
    sales_agen = models.CharField(max_length=100, blank=True, null=True)
    location = models.CharField(max_length=50, blank=True, null=True)
    hm_smr_reading = models.CharField(max_length=50, blank=True, null=True)
    hm_smr_reading_date = models.DateField(blank=True, null=True)
    hm_cuml_reading = models.CharField(max_length=50, blank=True, null=True)
    hm_cuml_reding_date = models.DateField(blank=True, null=True)
    site_received_date = models.DateField(blank=True, null=True)
    month_do_date = models.DateField(blank=True, null=True)
    year_do = models.IntegerField(blank=True, null=True)
    owner = models.CharField(max_length=100, blank=True, null=True)
    fmc = models.CharField(max_length=100, blank=True, null=True)
    plant_code = models.CharField(max_length=100, blank=True, null=True)
    functional_location = models.CharField(max_length=150, blank=True, null=True)
    asset_number = models.CharField(max_length=50, blank=True, null=True)
    
    class Meta:
        db_table = "pop equipment"
        verbose_name = "POP equipment"
        verbose_name_plural = "POP equipment"

    def __str__(self):
        return f"{self.equipment_type} - {self.equipment_cn_sap}"
class LifeComponent(models.Model):
    jobsite_code = models.CharField(max_length=50)
    equipment_code = models.CharField(max_length=50)
    equipment_model = models.CharField(max_length=100, blank=True, null=True)
    activity_name = models.CharField(max_length=100, blank=True, null=True)
    activity_type = models.CharField(max_length=50, blank=True, null=True)

    class Meta:
        db_table = "Life_Component"
        verbose_name = "Life Component"
        verbose_name_plural = "Life Component"

    def __str__(self):
        return f"{self.equipment_code}-{self.equipment_model}"
    
class egiobsolete(models.Model):
    EGI = models.CharField(max_length=100, blank=True, null=True, verbose_name="egi")
    TYPE = models.CharField(max_length=100, blank=True, null=True, verbose_name="Tipe")
    DISCONTINUE = models.CharField(max_length=100, blank=True, null=True, verbose_name="Discontinue")
    NEW_GENERATION = models.CharField(max_length=100, blank=True, null=True, verbose_name="New Generation")
    BRAND = models.CharField(max_length=100, blank=True, null=True, verbose_name="Brand")
    REMARKS = models.CharField(max_length=100, blank=True, null=True, verbose_name="Remarks")

    class Meta:
        db_table = "egiobsolete"
        verbose_name = "EGI Obsolete"
        verbose_name_plural = "EGI Obsolete"

    def __str__(self):
        return f"{self.EGI}-{self.TYPE}"
    
class checksheetmasterlist(models.Model):
    EGI = models.CharField(max_length=100, blank=True, null=True, verbose_name="EGI")
    CATEGORY = models.CharField(max_length=250, blank=True, null=True, verbose_name="CATEGORY")
    ITEM = models.CharField(max_length=250, blank=True, null=True, verbose_name="ITEM")
    QTY = models.CharField(max_length=100, blank=True, null=True, verbose_name="QTY")
    REMARKS = models.CharField(max_length=250, blank=True, null=True, verbose_name="REMARKS")

    class Meta:
        db_table = "checksheetmasterlist"
        verbose_name = "checksheet master list"
        verbose_name_plural = "checksheet master list"
    def __str__(self):
        return f"{self.EGI}-{self.CATEGORY}"
    
class conmon(models.Model):
    LOCATION            = models.CharField(max_length=100, blank=True, null=True)
    EGI                 = models.CharField(max_length=100, blank=True, null=True)
    EQP_TYPE            = models.CharField(max_length=100, blank=True, null=True)
    CN_SAP              = models.CharField(max_length=100, blank=True, null=True) # CN_SAP akan menjadi unik di sini
    SN                  = models.CharField(max_length=100, blank=True, null=True)
    COMPONENT           = models.CharField(max_length=100, blank=True, null=True)
    LIFETIME            = models.CharField(max_length=100, blank=True, null=True)
    SPO                 = models.CharField(max_length=100, blank=True, null=True)
    EQP_HEALTH          = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True)
    EQP_STATUS_HEALTH   = models.CharField(max_length=100, blank=True, null=True)
    COMP_HEALTH         = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True)
    COMP_STATUS_HEALTH  = models.CharField(max_length=100, blank=True, null=True)
    
    class Meta:
        db_table = "conmon"
        verbose_name ="conmon comp"
        verbose_name_plural = "conmon comp"
    def __str__(self):
        return f"{self.EGI}-{self.CN_SAP}"
    
    # 🔥 TAMBAHKAN METHOD KUSTOM INI DI DALAM MODEL
    def determine_comp_status_health(self):
        if self.COMP_HEALTH is None:
            return "-"
            
        # Konversi ke float untuk mempermudah perbandingan range desimal
        val = float(self.COMP_HEALTH)
        
        # Logika pembagian kondisi sesuai instruksi Bapak
        if 0.00 <= val <= 25.99:
            return "SEVERE"
        elif 26.00 <= val <= 50.99:
            return "CRITICAL"
        elif 51.00 <= val <= 75.00:
            return "CAUTION"
        elif 76.00 <= val <= 100.00:
            return "NORMAL"
        else:
            return "-" # Jika di luar range 0-100%
    
    # 🔥 TAMBAHKAN METHOD KUSTOM INI DI DALAM MODEL
    def determine_eqp_status_health(self):
        if self.EQP_HEALTH is None:
            return "-"
            
        # Konversi ke float untuk mempermudah perbandingan range desimal
        val = float(self.EQP_HEALTH)
        
        # Logika pembagian kondisi sesuai instruksi Bapak
        if 0.00 <= val <= 25.99:
            return "SEVERE"
        elif 26.00 <= val <= 50.99:
            return "CRITICAL"
        elif 51.00 <= val <= 75.00:
            return "CAUTION"
        elif 76.00 <= val <= 100.00:
            return "NORMAL"
        else:
            return "-" # Jika di luar range 0-100%
        
# 🔥 REKOMENDASI: Gabungkan kedua proses ke dalam SATU signal pre_save
@receiver(pre_save, sender=conmon)
def auto_fill_conmon_status(sender, instance, **kwargs):
    # ✅ Sudah diperbaiki panggilan fungsi determine_comp_status_health()-nya
    instance.COMP_STATUS_HEALTH = instance.determine_comp_status_health()
    
    # ✅ Sekaligus memproses status equipment
    instance.EQP_STATUS_HEALTH = instance.determine_eqp_status_health()
    
class directcost(models.Model):
    LOCATION        = models.CharField(max_length=100, blank=True, null=True)
    YEAR            = models.CharField(max_length=20, blank=True, null=True)
    DATE            = models.CharField(max_length=20, blank=True, null=True)
    DOCUMENT        = models.CharField(max_length=100, blank=True,null=True)
    COMP_CODE_CURR  = models.CharField(max_length=100, blank=True,null=True)
    FUNC_AREA       = models.CharField(max_length=100, blank=True,null=True)
    GL_ACCOUNT      = models.CharField(max_length=100, blank=True,null=True)
    GL_ACCOUNT_TEXT = models.CharField(max_length=100, blank=True,null=True)
    MATERIAL        = models.CharField(max_length=100, blank=True,null=True)
    MATERIAL_DESC   = models.CharField(max_length=100, blank=True,null=True)
    CN_SAP          = models.CharField(max_length=100, blank=True,null=True)

    class Meta:
        db_table = "directcost"
        verbose_name = "Direct Cost"
        verbose_name_plural = "Direct Cost"
    def __str__(self):
        return f"{self.LOCATION}-{self.CN_SAP}"
    
class IH08(models.Model):
   CN_SAP = models.CharField(max_length=100, blank=True, null=True)
   LOCATION = models.CharField(max_length=100, blank=True, null=True)
   EGI= models.CharField(max_length=100, blank=True, null=True)
   SN = models.CharField(max_length=100, blank=True, null=True)
   MANUFACTURE = models.CharField(max_length=100, blank=True, null=True)
   STATUS = models.CharField(max_length=100, blank=True, null=True)

   class Meta:
       db_table = "IH08"
       verbose_name = "IH08"
       verbose_name_plural = "IH08"

   def __str__(self):
        return f"{self.CN_SAP}-{self.EGI}"
#==========================================#
#  class Notifikasi penerima email===#
# ======================================= 

class KaryawanPenerimaNotifikasi(models.Model):
    nama = models.CharField(max_length=100)
    email = models.EmailField(unique=True)
    is_active = models.BooleanField(default=True, verbose_name="Aktif Send Email")


    # 🌟 MATRIX NOTIFIKASI (Centang dokumen yang ingin diterima user ini) 🌟
    notif_ba_breakdown = models.BooleanField(default=False, verbose_name="Notif BA Breakdown")
    notif_ba_standby = models.BooleanField(default=False, verbose_name="Notif BA Standby")
    notif_foto_4_sisi = models.BooleanField(default=False, verbose_name="Notif Foto 4 Sisi")
    notif_inspeksi = models.BooleanField(default=False, verbose_name="Notif Inspeksi")
    notif_rca = models.BooleanField(default=False, verbose_name="Notif RCA")
    notif_pengajuan_disposed = models.BooleanField(default=False, verbose_name="Notif Pengajuan Disposed")
    notif_lampiran_capex = models.BooleanField(default=False, verbose_name="Notif Lampiran Capex")
    notif_pde = models.BooleanField(default=False, verbose_name="Notif PDE")
    notif_summary_pde = models.BooleanField(default=False, verbose_name="Notif Summary PDE")
    notif_approved_prepare = models.BooleanField(default=False, verbose_name="Notif Form Approved (Prepare Disposed)")
    notif_waiting_prepare = models.BooleanField(default=False, verbose_name="Notif Form Pengajuan / Waiting (Prepare Disposed)")
    
    def __str__(self):
        return f"{self.nama} ({self.email})"

    class Meta:
        verbose_name = "DaftarPenerimaNotifikasi"
        verbose_name_plural = "List Penerima Notifikasi"


class InspectionTemplateItem(models.Model):
    """
    Master Bank Data Item Pemeriksaan Check Sheet disesuaikan dengan struktur Excel.
    """
    TYPE = models.CharField(max_length=100, help_text="EQUIPMENT TYPE (Cth: WATER TRUCK)")
    EGI = models.CharField(max_length=100, help_text="EGI Unit (Cth: HD785-5)")
    ITEM_GROUP = models.CharField(max_length=100, help_text="ITEM GROUP / Kategori (Cth: ENGINE)")
    ITEM_NAME = models.CharField(max_length=255, help_text="ITEM NAME / Nama Komponen (Cth: RADIATOR)")
    QTY = models.PositiveIntegerField(default=1, help_text="QTY (Cth: 1)")

    def __str__(self):
        return f"[{self.TYPE} - {self.EGI}] {self.ITEM_GROUP} : {self.ITEM_NAME} (Qty: {self.QTY})"

    class Meta:
        verbose_name = "Master Inspection Check Sheet Item"
        verbose_name_plural = "Master Check Sheet"
        ordering = ['TYPE', 'EGI', 'ITEM_GROUP']