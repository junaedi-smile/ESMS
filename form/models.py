#inside/form/models.py
from django.db import models
from django.contrib.auth import get_user_model
from django.contrib.auth.models import Group
from django.contrib.contenttypes.fields import GenericForeignKey
from django.contrib.contenttypes.models import ContentType
from asset.models import AssetEquipmentDisposed
from django.utils.translation import gettext_lazy as _
from django.utils import timezone

# dapatkan models user yang sedang digunakan django
User = get_user_model()

#Pilihan status dokumen (sesuai approval bertingkat)
DOCUMENT_STATUS_CHOICES = (
    ('DRAFT', 'Draft'),             
    ('SUB', 'Submitted'),           # Menunggu Approval Level 1
    ('APR1', 'Approved Level 1'),   # Menunggu Approval Level 2
    ('APR2', 'Approved Level 2'),   # Menunggu Final Approval
    ('FIN', 'Final Approved'),      
    ('REJ', 'Rejected'),
)

# Model Abstrak untuk bidang yang umum di semua formulir
class FormBaseModel(models.Model):
    diajukan_oleh = models.ForeignKey(User, on_delete=models.CASCADE, related_name='%(class)s_pengajuan', null=True, blank=True)
    last_action_by = models.ForeignKey(User, null=True, blank=True, on_delete=models.SET_NULL, related_name='%(class)s_last_action')
    status = models.CharField(max_length=10, choices=DOCUMENT_STATUS_CHOICES, default='DRAFT')
    submitted_at = models.DateTimeField(null=True, blank=True, verbose_name="Tanggal Pengajuan")
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        abstract = True
        
# 1. Model Pengajuan Equipment Disposed
class FormPengajuanEquipmentDisposed(FormBaseModel):
    CN_SAP = models.CharField(max_length=50)
    GROUP = models.CharField(max_length=50)
    TYPE = models.CharField(max_length=50)
    EGI = models.CharField(max_length=50)
    HM_SMR = models.DecimalField(max_digits=10, decimal_places=2)
    LOCATION = models.CharField(max_length=100)
    PERSENTASE_SPO = models.DecimalField(max_digits=5, decimal_places=2)
    NBV = models.DecimalField(max_digits=15, decimal_places=2)
    RCA = models.DecimalField(max_digits=15, decimal_places=2)
    LIFE_COMPT = models.DecimalField(max_digits=5, decimal_places=2)


    class Meta:
        verbose_name = "PDE"
        verbose_name_plural = "PDE"

    def __str__(self):
        return f"Pengajuan Disposed: {self.CN_SAP}"

# 2. Model Lampiran Capex
class FormLampiranCapex(FormBaseModel):
    NBV_STATUS_CHOICES = [
        ('COMPLETE', 'Complete'),
        ('NOT_COMPLETE', 'Not Complete'),
    ]
    
    CN_SAP = models.CharField(max_length=50)
    GROUP = models.CharField(max_length=50)
    TYPE = models.CharField(max_length=50)
    EGI = models.CharField(max_length=50)
    HM_SMR = models.DecimalField(max_digits=10, decimal_places=2)
    SPO_EQUIPMENT = models.CharField(max_length=100)
    PERSENTASE_SPO = models.FloatField(blank=True, null=True, verbose_name="% SPO Equipment")
    NILAI_AKUISISI = models.DecimalField(max_digits=15, decimal_places=2)
    NBV = models.DecimalField(max_digits=15, decimal_places=2)
    RV = models.DecimalField(max_digits=15, decimal_places=2)
    NBV_STATUS = models.CharField(max_length=20, choices=NBV_STATUS_CHOICES)
    DATE_DELIVERY = models.DateField()
    LIFE_EQUIPMENT = models.DecimalField(max_digits=10, decimal_places=2)
    STANDAR_DEPRE_EQUIPMENT = models.DecimalField(max_digits=5, decimal_places=2)
    REPLACEMENT = models.CharField(max_length=100)
    KONDISI_BODY = models.CharField(max_length=100)
    KONDISI_FRAME = models.CharField(max_length=100)
    KONDISI_KOMPONEN = models.CharField(max_length=100)
    PROSENTASE_LIFE_COMP_SPO = models.DecimalField(max_digits=5, decimal_places=2)
    COST_REPAIR = models.DecimalField(max_digits=15, decimal_places=2)
    HARGA_NEW = models.DecimalField(max_digits=15, decimal_places=2)
    NILAI_SISA_COMP = models.DecimalField(max_digits=15, decimal_places=2)
    OBSOLETE = models.TextField()

    class Meta:
        verbose_name = "Lampiran Capex"
        verbose_name_plural = "Lampiran Capex"

    def __str__(self):
        return f"Lampiran Capex: {self.CN_SAP}"

# 3. Model Pengajuan Disposed Site
class FormPengajuanDisposedSite(FormBaseModel):
    CN_SAP = models.CharField(max_length=50)
    TYPE = models.CharField(max_length=50)
    EGI = models.CharField(max_length=50)
    SN = models.CharField(max_length=50)
    DATE_CAUSE = models.DateField()
    HM_SMR = models.DecimalField(max_digits=10, decimal_places=2)
    CAUSE = models.TextField()
    NEW_PRICE = models.DecimalField(max_digits=15, decimal_places=2)
    RCA_PRICE = models.DecimalField(max_digits=15, decimal_places=2)
    ROSENTASE_RCA_VS_NEW_PRICE = models.DecimalField(max_digits=5, decimal_places=2)

    class Meta:
        verbose_name = "PDS"
        verbose_name_plural = "PDS"

    def __str__(self):
        return f"Pengajuan Disposed Site: {self.CN_SAP}"

# 4. Model Repair Cost Analysis
class FormRepairCostAnalisis(FormBaseModel):
    CATEGORY_CHOICES = [
        ('A', 'Category A'),
        ('B', 'Category B'),
        ('C', 'Category C'),
    ]

    CN_SAP = models.CharField(max_length=50)
    TYPE = models.CharField(max_length=50)
    EGI = models.CharField(max_length=50)
    SN = models.CharField(max_length=50)
    DATE_CAUSE = models.DateField()
    HM_SMR = models.DecimalField(max_digits=10, decimal_places=2)
    CAUSE = models.TextField()
    NO = models.IntegerField()
    PART_NUMBER = models.CharField(max_length=100)
    DESCRIPTIONS = models.TextField()
    QTY = models.DecimalField(max_digits=10, decimal_places=2)
    UNIT = models.CharField(max_length=20)
    UNIT_PRICE = models.DecimalField(max_digits=15, decimal_places=2)
    TOTAL_PRICE = models.DecimalField(max_digits=15, decimal_places=2)
    CATEGORY = models.CharField(max_length=2, choices=CATEGORY_CHOICES)

    class Meta:
        verbose_name = "RCA"
        verbose_name_plural = "RCA"

    def __str__(self):
        return f"Repair Cost Analisis: {self.CN_SAP}"   
    

# 5.Model BA Standby Unit

class FormBAStandby(FormBaseModel):
    """
    Berita Acara Stand By Unit
    Satu form untuk satu unit (CN SAP tunggal)
    """
    # ── Data Unit (auto-fill dari AssetEquipment) ──────────
    CN_SAP          = models.CharField(max_length=100, verbose_name="CN Unit")
    EGI             = models.CharField(max_length=100, blank=True, null=True, verbose_name="EGI")
    EQUIP_NAME      = models.CharField(max_length=100, blank=True, null=True, verbose_name="Equipment Name")
    SERIAL_NUMBER   = models.CharField(max_length=100, blank=True, null=True, verbose_name="Serial Number")
    HM              = models.CharField(max_length=100, blank=True, null=True, verbose_name="Hour Meter")
    LOCATION        = models.CharField(max_length=100, blank=True, null=True, verbose_name="Location")

    # ── Data Form (diisi manual) ───────────────────────────
    NO_DOKUMEN_AUTO   = models.CharField(max_length=100, blank=True, null=True, verbose_name="No. Dokumen Sistem")
    NO_DOKUMEN_MANUAL = models.CharField(max_length=100, blank=True, null=True, verbose_name="No. Dokumen Manual")
    TANGGAL_EFEKTIF   = models.DateField(blank=True, null=True, verbose_name="Tanggal Efektif Standby")
    ALASAN_STANDBY    = models.TextField(blank=True, null=True, verbose_name="Alasan Standby")
    STATUS_STANDBY    = models.CharField(
        max_length=50,
        default='STANDBY',
        verbose_name="Status"
    )

    # ── Tanda Tangan ───────────────────────────────────────
    # Diajukan oleh
    DIAJUKAN_NAMA     = models.CharField(max_length=100, blank=True, null=True)
    DIAJUKAN_JABATAN  = models.CharField(max_length=100, blank=True, null=True)

    # Mengetahui 1
    MENGETAHUI1_NAMA    = models.CharField(max_length=100, blank=True, null=True)
    MENGETAHUI1_JABATAN = models.CharField(max_length=100, blank=True, null=True)

    # Mengetahui 2
    MENGETAHUI2_NAMA    = models.CharField(max_length=100, blank=True, null=True)
    MENGETAHUI2_JABATAN = models.CharField(max_length=100, blank=True, null=True)

    # Menyetujui 1
    MENYETUJUI1_NAMA    = models.CharField(max_length=100, blank=True, null=True)
    MENYETUJUI1_JABATAN = models.CharField(max_length=100, blank=True, null=True)

    # Menyetujui 2
    MENYETUJUI2_NAMA    = models.CharField(max_length=100, blank=True, null=True)
    MENYETUJUI2_JABATAN = models.CharField(max_length=100, blank=True, null=True)

    # Menyetujui 3
    MENYETUJUI3_NAMA    = models.CharField(max_length=100, blank=True, null=True)
    MENYETUJUI3_JABATAN = models.CharField(max_length=100, blank=True, null=True)

    class Meta:
        verbose_name        = "BA Standby"
        verbose_name_plural = "BA Standby"
        ordering            = ['-created_at']

    def __str__(self):
        return f"BA Standby: {self.CN_SAP} — {self.STATUS_STANDBY}"



# 6. Model Foto Kondition Unit
class FormFotoKonditionUnit(FormBaseModel):
    CN_SAP = models.CharField(max_length=50)
    TYPE = models.CharField(max_length=50)
    EGI = models.CharField(max_length=50)
    SN = models.CharField(max_length=50)
    LOCATION = models.CharField(max_length=100)
    DATE_CAUSE = models.DateField()
    HM_SMR = models.DecimalField(max_digits=10, decimal_places=2)
    TAMPAK_DEPAN = models.ImageField(upload_to='foto_kondisi/')
    TAMPAK_BELAKANG = models.ImageField(upload_to='foto_kondisi/')
    TAMPAK_SAMPING_KANAN = models.ImageField(upload_to='foto_kondisi/')
    TAMPAK_SAMPING_KIRI = models.ImageField(upload_to='foto_kondisi/')

    class Meta:
        verbose_name = "Equipment Condition"
        verbose_name_plural = "Equipment Condition"

    def __str__(self):
        return f"Foto Kondition Unit: {self.CN_SAP}"
    
# Sistem Approval (Revisi dari sebelumnya)
class ApprovalStep(models.Model):
    urutan = models.IntegerField(unique=True)
    nama_langkah = models.CharField(max_length=100)
    penanggung_jawab_group = models.ForeignKey(Group, on_delete=models.CASCADE, related_name='langkah_persetujuan', null=True)

    class Meta:
        verbose_name = "urutan approval"
        verbose_name_plural = "urutan approval"       

    def __str__(self):
        return f"Langkah {self.urutan}: {self.nama_langkah} ({self.penanggung_jawab_group.name})"

# 🚨 ApprovalLog (Riwayat Approval)

class ApprovalLog(models.Model):
    content_type = models.ForeignKey(ContentType, on_delete=models.CASCADE)
    object_id = models.PositiveIntegerField()
    form_pengajuan = GenericForeignKey('content_type', 'object_id')
    # Aksi yang dilakukan
    ACTION_CHOICES = (
        ('SUBMIT', 'Diajukan'),
        ('APPROVED', 'Disetujui'), 
        ('REJECTED', 'Ditolak')
    )

    langkah = models.ForeignKey(ApprovalStep, on_delete=models.SET_NULL, null=True)
    approved_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True)
    action = models.CharField(max_length=10, choices=ACTION_CHOICES, default='SUBMIT')    
    komentar = models.TextField(blank=True, null=True)
    tanggal_persetujuan = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = "Riwayat Approval"
        verbose_name_plural = "Riwayat Approval"
        ordering = ['tanggal_persetujuan']
    
    def __str__(self):
        return f"{self.action} oleh {self.approved_by} pada {self.form_pengajuan.__class__.__name__} - Langkah {self.langkah.urutan if self.langkah else 'N/A'}"
   
    
class ChecksheetPI(models.Model):
    cn_sap = models.CharField(max_length=100, blank=True, null=True, verbose_name="UNIT CODE")
    egi = models.CharField(max_length=100, blank=True, null=True, verbose_name="UNIT MODEL")
    hm_smr = models.CharField(max_length=100, blank=True, null=True, verbose_name="SMR")
   # Data Personil
    pic_inspector = models.CharField(max_length=100, verbose_name="PIC Inspector")
    atasan_inspector = models.CharField(max_length=100, verbose_name="Atasan Inspector")
    # Tambahkan di dalam class ChecksheetPI
    diajukan_oleh = models.ForeignKey(User, on_delete=models.CASCADE, related_name='checksheet_dibuat',null=True, blank=True)

    
    created_at = models.DateTimeField(auto_now_add=True)

    status = models.CharField(
        max_length=10,
        choices=DOCUMENT_STATUS_CHOICES,
        default='DRAFT',
        verbose_name="Status Dokumen"
    )
    submitted_at = models.DateTimeField(
        null=True, blank=True, verbose_name="Tanggal Pengajuan"
    )
    finalized_at = models.DateTimeField(null=True, blank=True, verbose_name="Lama Waktu pengajuan")

    class Meta:
        db_table = "ChecksheetPI"
        verbose_name = "Checksheet PI"
        verbose_name_plural = "Checksheet PI"

    def __str__(self):
        return f"{self.cn_sap}-{self.egi}"
    # Pilihan Kondisi untuk setiap Item
CONDITION_CHOICES = (
    ('G', 'Good'),
    ('B', 'Bad'),
    ('N', 'NA/Tidak Ada'),
)

class ChecksheetItem(models.Model):
    """Model Detail untuk setiap baris dalam Checksheet."""
    
    # Foreign Key ke Header
    checksheet_pi = models.ForeignKey(
        ChecksheetPI, 
        on_delete=models.CASCADE, 
        related_name='items'
    )
    
    # Data Item (Disalin dari ChecksheetMasterList)
    category = models.CharField(max_length=255, null=True, blank=True, verbose_name="CATEGORY")
    item_name = models.CharField(max_length=255, verbose_name="ITEM")
    qty = models.IntegerField(default=1, verbose_name="QTY")
    
    # Data Input User
    condition = models.CharField(
        max_length=1, 
        choices=CONDITION_CHOICES, 
        verbose_name="CONDITION"
    )
    remarks = models.TextField(verbose_name="REMARKS", blank=True, null=True)
    
    class Meta:
        db_table = "ChecksheetItem"
        verbose_name = "Checksheet Item"
        ordering = ['item_name']

