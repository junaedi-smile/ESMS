# asset/models.py
from django.db import models
from django.utils import timezone
from django.contrib.auth.models import User # WAJIB ada untuk relasi ke User
from cloudinary.models import CloudinaryField
from django.db.models.signals import post_save
from django.dispatch import receiver
from django.contrib.auth.models import User

#===========================================================================================
# ================Model untuk unit yang Consolidation Equipment Status =====================
#===========================================================================================

class AssetEquipment(models.Model):     
    # Field-field ini akan menjadi identifier unik untuk unit disposed
    CN_SAP = models.CharField(max_length=100, primary_key=True, verbose_name="Code Number SAP") # CN_SAP akan menjadi unik di sini
    No_Asset = models.CharField(max_length=100, blank=True, null=True, verbose_name="No Asset")
    CN_ELLIPSE = models.CharField(max_length=100, blank=True, null=True, verbose_name="Code Number Ellipse")
    EGI = models.CharField(max_length=100, blank=True, null=True)
    FOTO = models.ImageField(upload_to='asset/monthly_reports/images/', blank=True, null=True)
     # Informasi umum unit
    TYPE = models.CharField(max_length=100, blank=True, null=True, verbose_name="Type")
    GROUP = models.CharField(max_length=100, blank=True, null=True, verbose_name="Class Equipment")
    CLASS_WEIGHT = models.CharField(max_length=100, blank=True, null=True, verbose_name="Class Weight")
    OWNERSHIP = models.CharField(max_length=100, blank=True, null=True, verbose_name="Ownership")
    BRAND = models.CharField(max_length=100, blank=True, null=True, verbose_name="Brand")
    SN = models.CharField(max_length=100, blank=True, null=True, verbose_name="Serial Number")

    # Lokasi dan Bagian
    SECTION = models.CharField(max_length=100, blank=True, null=True, verbose_name="Section")
    LOCATION = models.CharField(max_length=100, blank=True, null=True, verbose_name="Location")
    SUB_SITE = models.CharField(max_length=100, blank=True, null=True, verbose_name="Sub Site")
    SUB_LOCATION = models.CharField(max_length=100, blank=True, null=True, verbose_name="Sub Location")

    # Informasi HM / SPO
    HM_SMR = models.CharField(max_length=100, blank=True, null=True, verbose_name="Hour Meter") # CharField jika mungkin ada non-numeric
    HM_DATE = models.DateField(blank=True, null=True, verbose_name="Hour Meter Date")
    SPO_EQUIPMENT = models.IntegerField(blank=True, null=True, verbose_name="SPO Equipment")
    PERSENTASE_SPO = models.FloatField(blank=True, null=True, verbose_name="% SPO Equipment")

    # Status Disposal
    EQUIPMENT_CONDITION = models.CharField(max_length=100, default='DISPOSED', verbose_name="Equipment Condition")
    STATUS_EQUIPMENT = models.CharField(max_length=100, blank=True, null=True, verbose_name="Status Equipment")
    STATUS_EQUIPMENT_DISPOSED = models.CharField(max_length=100, blank=True, null=True, verbose_name="Status Equipment Disposed")
    REFERENSI_NO_PDE = models.CharField(max_length=100, blank=True, null=True, verbose_name="Referensi No PDE")

    # Metadata kapan terakhir diperbarui (dari data bulanan mana)
    LAST_UPDATED_MONTH = models.IntegerField(blank=True, null=True, verbose_name="Bulan Data Terakhir Diperbarui")
    LAST_UPDATED_YEAR = models.IntegerField(blank=True, null=True, verbose_name="Tahun Data Terakhir Diperbarui")
    UPDATED_AT = models.DateTimeField(auto_now=True, verbose_name="Waktu Pembaruan") # Waktu sebenarnya di-update
    BP = models.CharField(max_length=255, blank=True,null=True, verbose_name="BP")
    # Anda juga bisa menambahkan field FOTO jika ingin menyimpan foto terakhir dari disposed unit
    # FOTO = models.ImageField(upload_to='disposed_equipment_photos/', blank=True, null=True)

    class Meta:
        verbose_name = "Consolidation Report"
        verbose_name_plural = "Consolidation Report"
        ordering = ['-LAST_UPDATED_YEAR', '-LAST_UPDATED_MONTH', 'CN_SAP'] # Urutkan berdasarkan bulan/tahun terbaru

    def __str__(self):
        return f"Disposed: {self.CN_SAP} ({self.No_Asset}) - PDE: {self.REFERENSI_NO_PDE}"     
       
  
class AssetMonthlyStatus(models.Model):         
    No_Asset = models.CharField(max_length=255, blank=True, default='Unknown' )
    CN_SAP = models.CharField(max_length=255)   
    CN_ELLIPSE = models.CharField(max_length=255, blank=True, default='Unknown')
    EGI = models.CharField(max_length=255, blank=True, default='Unknown')
    TYPE = models.CharField(max_length=255, blank=True, default='Unknown')
    FOTO = CloudinaryField('image', folder='asset/monthly_reports/images/', blank=True, null=True)
    GROUP = models.CharField(max_length=255, blank=True, default='Unknown')
    CLASS_WEIGHT = models.CharField(max_length=255, blank=True, default='Unknown')
    OWNERSHIP = models.CharField(max_length=255, blank=True, default='Unknown')
    SECTION = models.CharField(max_length=255, blank=True, default='Unknown')
    LOCATION = models.CharField(max_length=255, blank=True, default='Unknown')
    SUB_SITE = models.CharField(max_length=255, blank=True, default='Unknown')
    SUB_LOCATION = models.CharField(max_length=255, blank=True, default='Unknown')   
    BRAND = models.CharField(max_length=255, blank=True, default='Unknown')
    SN = models.CharField(max_length=255, blank=True, default='Unknown')
    HM_SMR = models.CharField(max_length=255, blank=True, null=True)
    HM_DATE = models.DateField(null=True, blank=True)
    SPO_EQUIPMENT = models.IntegerField(blank=True, null=True)
    PERSENTASE_SPO = models.FloatField(null=True, blank=True)
    EQUIPMENT_CONDITION = models.CharField(max_length=255, blank=True)
    STATUS_EQUIPMENT = models.CharField(max_length=255, blank=True)
    STATUS_EQUIPMENT_DISPOSED = models.CharField(max_length=100, blank=True, null=True, verbose_name="Status Equipment Disposed")  
    NBV = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True, verbose_name='NBV')
    WEIGHT = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True, verbose_name='WEIGHT')     
    REFERENSI_NO_PDE = models.CharField(max_length=255, blank=True)
    YEAR = models.IntegerField(blank=True, null=True)
    MONTH = models.DateField(blank=True, null=True)
    BP = models.CharField(max_length=255, blank=True, default='Unknown')
   
    #----untuk save user login-----
    updated_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True, verbose_name="Diubah Oleh")


    def save(self, *args, **kwargs):
        from .models import AssetEquipmentPrepareDisposed, AssetEquipment, AssetEquipmentDisposed
        
        # 1. Cek apakah dokumen sudah lengkap di tabel Prepare ATAU sudah ada di tabel Disposed
        prepare_obj = AssetEquipmentPrepareDisposed.objects.filter(asset__CN_SAP=self.CN_SAP).first()
        disposed_obj = AssetEquipmentDisposed.objects.filter(asset__CN_SAP=self.CN_SAP).first()
        
        is_complete = False
        if disposed_obj:
            # Jika unit sudah pernah naik ke tabel Disposed, tandai pasti lengkap
            is_complete = True
        elif prepare_obj:
            # Cek apakah 4 dokumen wajib sudah lengkap di prepare
            is_complete = bool(
                prepare_obj.foto_4_sisi and 
                prepare_obj.rca and 
                prepare_obj.inspeksi_unit and 
                prepare_obj.pengajuan_disposed
            )
        
        raw_cond = (self.EQUIPMENT_CONDITION or '').upper().strip()
        
        # 🌟 ATURAN UTAMA: Jika dokumen SUDAH lengkap (atau unit sudah di Disposed), 
        # PAKSA status bulanan menjadi DISPOSED apapun input/data baru yang masuk!
        if is_complete:
            self.EQUIPMENT_CONDITION = 'DISPOSED'
            self.STATUS_EQUIPMENT_DISPOSED = 'DISPOSED'
        # Aturan 2: Jika berniat mendispose, tapi dokumen BELUM lengkap -> Paksa PREPARE
        elif raw_cond == 'DISPOSED' and not is_complete:
            self.EQUIPMENT_CONDITION = 'PREPARE FOR DISPOSED'
            self.STATUS_EQUIPMENT_DISPOSED = 'PREPARE FOR DISPOSED'

        super().save(*args, **kwargs)

        # 🌟 3. SINKRONISASI KE TABEL PREPARE (Hanya jika belum lengkap dan berstatus Prepare)
        if self.EQUIPMENT_CONDITION.upper().strip() == 'PREPARE FOR DISPOSED' and not is_complete:
            asset_parent = AssetEquipment.objects.filter(CN_SAP=self.CN_SAP).first()
            if asset_parent:
                defaults_data = {
                    "No_Asset": self.No_Asset,
                    "CN_ELLIPSE": self.CN_ELLIPSE,
                    "EGI": self.EGI,
                    "TYPE": self.TYPE,
                    "GROUP": self.GROUP,
                    "CLASS_WEIGHT": self.CLASS_WEIGHT,
                    "OWNERSHIP": self.OWNERSHIP,
                    "BRAND": self.BRAND,
                    "SN": self.SN,
                    "SECTION": self.SECTION,
                    "LOCATION": self.LOCATION,
                    "SUB_SITE": self.SUB_SITE,
                    "SUB_LOCATION": self.SUB_LOCATION,
                    "HM_SMR": self.HM_SMR,
                    "HM_DATE": self.HM_DATE,
                    "SPO_EQUIPMENT": self.SPO_EQUIPMENT,
                    "PERSENTASE_SPO": self.PERSENTASE_SPO,
                    "nbv_prepare": self.NBV,
                    "EQUIPMENT_CONDITION": 'PREPARE FOR DISPOSED',
                    "STATUS_EQUIPMENT": self.STATUS_EQUIPMENT,
                    "REFERENSI_NO_PDE": self.REFERENSI_NO_PDE,
                    "BP": self.BP,
                }
                
                if not prepare_obj:
                    AssetEquipmentPrepareDisposed.objects.update_or_create(
                        asset=asset_parent,
                        defaults=defaults_data
                    )
                else:
                    AssetEquipmentPrepareDisposed.objects.filter(asset=asset_parent).update(
                        No_Asset=self.No_Asset,
                        CN_ELLIPSE=self.CN_ELLIPSE,
                        EGI=self.EGI,
                        TYPE=self.TYPE,
                        GROUP=self.GROUP,
                        CLASS_WEIGHT=self.CLASS_WEIGHT,
                        OWNERSHIP=self.OWNERSHIP,
                        BRAND=self.BRAND,
                        SN=self.SN,
                        SECTION=self.SECTION,
                        LOCATION=self.LOCATION,
                        SUB_SITE=self.SUB_SITE,
                        SUB_LOCATION=self.SUB_LOCATION,
                        HM_SMR=self.HM_SMR,
                        HM_DATE=self.HM_DATE,
                        SPO_EQUIPMENT=self.SPO_EQUIPMENT,
                        PERSENTASE_SPO=self.PERSENTASE_SPO,
                        nbv_prepare=self.NBV,
                        REFERENSI_NO_PDE=self.REFERENSI_NO_PDE,
                        BP=self.BP,
                    )

    def __str__(self):
        month_str = self.MONTH.strftime('%Y-%m') if self.MONTH else 'N/A'
        return f"{self.No_Asset} - {self.CN_SAP} ({month_str})" 
    
    class Meta:
        verbose_name = "Monthly Eqp Report"  
        verbose_name_plural = "Monthly Eqp Report"
        unique_together = ('CN_SAP', 'MONTH', 'YEAR',)


#===========================================================================================
# ================Model untuk unit yang Disposed ===========================================
#===========================================================================================

class AssetEquipmentDisposed(models.Model):
    # Field-field ini akan menjadi identifier unik untuk unit disposed
    asset = models.OneToOneField(
        AssetEquipment, 
        on_delete=models.CASCADE, 
        related_name='disposed_details',
        to_field='CN_SAP',
        db_column='CN_SAP_id',
        primary_key=True,
    ) # CN_SAP akan menjadi unik di sini
    No_Asset = models.CharField(max_length=100, blank=True, null=True, verbose_name="No Asset")
    CN_ELLIPSE = models.CharField(max_length=100, blank=True, null=True, verbose_name="Code Number Ellipse")
    EGI = models.CharField(max_length=100, blank=True, null=True)

    # Informasi umum unit
    TYPE = models.CharField(max_length=100, blank=True, null=True, verbose_name="Type")
    GROUP = models.CharField(max_length=100, blank=True, null=True, verbose_name="Class Equipment")
    CLASS_WEIGHT = models.CharField(max_length=100, blank=True, null=True, verbose_name="Class Weight")
    OWNERSHIP = models.CharField(max_length=100, blank=True, null=True, verbose_name="Ownership")
    BRAND = models.CharField(max_length=100, blank=True, null=True, verbose_name="Brand")
    SN = models.CharField(max_length=100, blank=True, null=True, verbose_name="Serial Number")

    # Lokasi dan Bagian
    SECTION = models.CharField(max_length=100, blank=True, null=True, verbose_name="Section")
    LOCATION = models.CharField(max_length=100, blank=True, null=True, verbose_name="Location")
    SUB_SITE = models.CharField(max_length=100, blank=True, null=True, verbose_name="Sub Site")
    SUB_LOCATION = models.CharField(max_length=100, blank=True, null=True, verbose_name="Sub Location")

    # Informasi HM / SPO
    HM_SMR = models.CharField(max_length=100, blank=True, null=True, verbose_name="Hour Meter") # CharField jika mungkin ada non-numeric
    HM_DATE = models.DateField(blank=True, null=True, verbose_name="Hour Meter Date")
    SPO_EQUIPMENT = models.IntegerField(blank=True, null=True, verbose_name="SPO Equipment")
    PERSENTASE_SPO = models.FloatField(blank=True, null=True, verbose_name="% SPO Equipment")
    nbv_disposed = models.DecimalField( max_digits=10, decimal_places=2, null=True, blank=True, verbose_name='NBV')
    # Status Disposal
    EQUIPMENT_CONDITION = models.CharField(max_length=100, default='DISPOSED', verbose_name="Equipment Condition")
    STATUS_EQUIPMENT = models.CharField(max_length=100, blank=True, null=True, verbose_name="Status Equipment")
    STATUS_EQUIPMENT_DISPOSED = models.CharField(max_length=100, blank=True, null=True, verbose_name="Status Equipment Disposed")
    REFERENSI_NO_PDE = models.CharField(max_length=100, blank=True, null=True, verbose_name="Referensi No PDE")

    # Metadata kapan terakhir diperbarui (dari data bulanan mana)
    LAST_UPDATED_MONTH = models.IntegerField(blank=True, null=True, verbose_name="Bulan Data Terakhir Diperbarui")
    LAST_UPDATED_YEAR = models.IntegerField(blank=True, null=True, verbose_name="Tahun Data Terakhir Diperbarui")
    UPDATED_AT = models.DateTimeField(auto_now=True, verbose_name="Waktu Pembaruan") # Waktu sebenarnya di-update
    BP = models.CharField(max_length=255, blank=True,null=True, verbose_name="BP")
    # Anda juga bisa menambahkan field FOTO jika ingin menyimpan foto terakhir dari disposed unit
    # FOTO = models.ImageField(upload_to='disposed_equipment_photos/', blank=True, null=True)

    # ── 📂 MERGER FIELD DIGITAL DOKUMEN DISPOSAL ────────────────────────
    foto_4_sisi = models.FileField(upload_to='disposed/foto_4_sisi/', blank=True, null=True, verbose_name="Foto 4 Sisi")
    foto_4_sisi_uploaded_at = models.DateTimeField(null=True, blank=True, verbose_name="Foto 4 Sisi Diupload Pada")
    foto_4_sisi_uploaded_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True, related_name='uploaded_foto_4_sisi', verbose_name="Foto 4 Sisi Diupload Oleh")

    inspeksi_unit = models.FileField(upload_to='disposed/inspeksi_unit/', blank=True, null=True, verbose_name="Inspeksi Unit")
    inspeksi_unit_uploaded_at = models.DateTimeField(null=True, blank=True, verbose_name="Inspeksi Unit Diupload Pada")
    inspeksi_unit_uploaded_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True, related_name='uploaded_inspeksi_unit', verbose_name="Inspeksi Unit Diupload Oleh")

    rca = models.FileField(upload_to='disposed/rca/', blank=True, null=True, verbose_name="RCA")
    rca_uploaded_at = models.DateTimeField(null=True, blank=True, verbose_name="RCA Diupload Pada")
    rca_uploaded_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True, related_name='uploaded_rca', verbose_name="RCA Diupload Oleh")

    pengajuan_disposed = models.FileField(upload_to='disposed/pengajuan/', blank=True, null=True, verbose_name="Pengajuan Disposed Equipment")
    pengajuan_disposed_uploaded_at = models.DateTimeField(null=True, blank=True, verbose_name="Pengajuan Disposed Diupload Pada")
    pengajuan_disposed_uploaded_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True, related_name='uploaded_pengajuan_disposed', verbose_name="Pengajuan Disposed Diupload Oleh")

    lampiran_capex = models.FileField(upload_to='disposed/capex/', blank=True, null=True, verbose_name="Lampiran Capex")
    lampiran_capex_uploaded_at = models.DateTimeField(null=True, blank=True, verbose_name="Lampiran Capex Diupload Pada")
    lampiran_capex_uploaded_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True, related_name='uploaded_lampiran_capex', verbose_name="Lampiran Capex Diupload Oleh")

    pde = models.FileField(upload_to='disposed/pde/', blank=True, null=True, verbose_name="PDE")
    pde_uploaded_at = models.DateTimeField(null=True, blank=True, verbose_name="PDE Diupload Pada")
    pde_uploaded_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True, related_name='uploaded_pde', verbose_name="PDE Diupload Oleh")

    summary_pde = models.FileField(upload_to='disposed/summary_pde/', blank=True, null=True, verbose_name="Summary PDE")
    summary_pde_uploaded_at = models.DateTimeField(null=True, blank=True, verbose_name="Summary PDE Diupload Pada")
    summary_pde_uploaded_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True, related_name='uploaded_summary_pde', verbose_name="Summary PDE Diupload Oleh")

    #----untuk save user login-----
    updated_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True, verbose_name="Diubah Oleh")

    # ── KONSTANTA HELPER UNTUK TRACKING DI VIEW & ADMIN ─────────────────
    DOC_FIELDS = [
        'foto_4_sisi', 'inspeksi_unit', 'rca', 
        'pengajuan_disposed', 'lampiran_capex', 'pde', 'summary_pde'
    ]

    DOC_LABELS = {
        'foto_4_sisi': 'Foto 4 Sisi',
        'inspeksi_unit': 'Inspeksi Unit',
        'rca': 'RCA',
        'pengajuan_disposed': 'Pengajuan Disposed',
        'lampiran_capex': 'Lampiran Capex',
        'pde': 'PDE',
        'summary_pde': 'Summary PDE',
    }

    # ── LOGIKA PROGRESS UTK TRACKING KELENGKAPAN ────────────────────────
    @property
    def total_dokumen(self):
        return len(self.DOC_FIELDS)

    @property
    def jumlah_complete(self):
        return sum(1 for field in self.DOC_FIELDS if getattr(self, field))

    @property
    def jumlah_progress(self):
        return self.total_dokumen - self.jumlah_complete

    @property
    def persentase_complete(self):
        if self.total_dokumen == 0:
            return 0
        return round((self.jumlah_complete / self.total_dokumen) * 100)

    @property
    def is_all_complete(self):
        return self.jumlah_complete == self.total_dokumen

    def get_status_per_dokumen(self):
        """Mengembalikan dict status string untuk keperluan API & Badge"""
        status_dict = {}
        for field in self.DOC_FIELDS:
            status_dict[field] = 'COMPLETE' if getattr(self, field) else 'PROGRESS'
        return status_dict
    
    # ── 🔄 AUTOMATISASI STATUS EQUIPTMENT UTAMA ────────────────────────
    def save(self, *args, **kwargs):
        import os
        from .models import AssetEquipmentPrepareDisposed
        from django.db import transaction

        # 1. Deteksi penghapusan file fisik lama jika diganti/dihapus
        if self.pk:
            try:
                old_instance = AssetEquipmentDisposed.objects.get(pk=self.pk)
                for field in self.DOC_FIELDS:
                    old_file = getattr(old_instance, field, None)
                    new_file = getattr(self, field, None)
                    
                    if old_file and old_file != new_file:
                        if hasattr(old_file, 'path') and os.path.exists(old_file.path):
                            try:
                                os.remove(old_file.path)
                            except Exception:
                                pass
            except AssetEquipmentDisposed.DoesNotExist:
                pass

        # 2. Cek apakah 4 dokumen utama lengkap
        prepare_docs_complete = bool(
            self.foto_4_sisi and 
            self.inspeksi_unit and 
            self.rca and 
            self.pengajuan_disposed
        )

        cn_sap_value = self.asset.CN_SAP if self.asset else getattr(self, 'CN_SAP', None)
        target_condition = 'DISPOSED' if prepare_docs_complete else 'PREPARE FOR DISPOSED'
        self.EQUIPMENT_CONDITION = target_condition

        # Simpan perubahan ke database Disposed terlebih dahulu
        super().save(*args, **kwargs)

        # 3. Update status di master AssetEquipment
        if cn_sap_value:
            AssetEquipment.objects.filter(CN_SAP=cn_sap_value).update(
                EQUIPMENT_CONDITION=target_condition
            )
            if self.asset and self.asset.EQUIPMENT_CONDITION != target_condition:
                self.asset.EQUIPMENT_CONDITION = target_condition
                self.asset.save(update_fields=['EQUIPMENT_CONDITION'])

        # 4. Jika dokumen utama ternyata belum lengkap, kembalikan otomatis ke tabel Prepare
        if not prepare_docs_complete and cn_sap_value:
            try:
                with transaction.atomic():
                    existing_prep = AssetEquipmentPrepareDisposed.objects.filter(asset_id=cn_sap_value).first()

                    # Tarik File & Metadata Tanggal/User dari Disposed atau Prepare lama
                    f_foto = self.foto_4_sisi or (existing_prep.foto_4_sisi if existing_prep else None)
                    f_foto_at = self.foto_4_sisi_uploaded_at or (existing_prep.foto_4_sisi_uploaded_at if existing_prep else None)
                    f_foto_by = self.foto_4_sisi_uploaded_by or (existing_prep.foto_4_sisi_uploaded_by if existing_prep else None)

                    f_inspeksi = self.inspeksi_unit or (existing_prep.inspeksi_unit if existing_prep else None)
                    f_inspeksi_at = self.inspeksi_unit_uploaded_at or (existing_prep.inspeksi_unit_uploaded_at if existing_prep else None)
                    f_inspeksi_by = self.inspeksi_unit_uploaded_by or (existing_prep.inspeksi_unit_uploaded_by if existing_prep else None)

                    f_rca = self.rca or (existing_prep.rca if existing_prep else None)
                    f_rca_at = self.rca_uploaded_at or (existing_prep.rca_uploaded_at if existing_prep else None)
                    f_rca_by = self.rca_uploaded_by or (existing_prep.rca_uploaded_by if existing_prep else None)

                    f_pengajuan = self.pengajuan_disposed or (existing_prep.pengajuan_disposed if existing_prep else None)
                    f_pengajuan_at = self.pengajuan_disposed_uploaded_at or (existing_prep.pengajuan_disposed_uploaded_at if existing_prep else None)
                    f_pengajuan_by = self.pengajuan_disposed_uploaded_by or (existing_prep.pengajuan_disposed_uploaded_by if existing_prep else None)

                    AssetEquipmentPrepareDisposed.objects.update_or_create(
                        asset_id=cn_sap_value,
                        defaults={
                            "No_Asset": self.No_Asset,
                            "CN_ELLIPSE": self.CN_ELLIPSE,
                            "EGI": self.EGI,
                            "TYPE": self.TYPE,
                            "GROUP": self.GROUP,
                            "CLASS_WEIGHT": self.CLASS_WEIGHT,
                            "OWNERSHIP": self.OWNERSHIP,
                            "BRAND": self.BRAND,
                            "SN": self.SN,
                            "SECTION": self.SECTION,
                            "LOCATION": self.LOCATION,
                            "SUB_SITE": self.SUB_SITE,
                            "SUB_LOCATION": self.SUB_LOCATION,
                            "HM_SMR": self.HM_SMR,
                            "HM_DATE": self.HM_DATE,
                            "SPO_EQUIPMENT": self.SPO_EQUIPMENT,
                            "PERSENTASE_SPO": self.PERSENTASE_SPO,
                            "nbv_prepare": self.nbv_disposed,
                            "EQUIPMENT_CONDITION": 'PREPARE FOR DISPOSED',
                            "STATUS_EQUIPMENT": self.STATUS_EQUIPMENT,
                            "REFERENSI_NO_PDE": self.REFERENSI_NO_PDE,
                            "BP": self.BP,
                            
                            # 🌟 SERTAKAN FILE DAN METADATA LENGKAP KEMBALI KE PREPARE
                            "foto_4_sisi": f_foto,
                            "foto_4_sisi_uploaded_at": f_foto_at,
                            "foto_4_sisi_uploaded_by": f_foto_by,
                            
                            "inspeksi_unit": f_inspeksi,
                            "inspeksi_unit_uploaded_at": f_inspeksi_at,
                            "inspeksi_unit_uploaded_by": f_inspeksi_by,
                            
                            "rca": f_rca,
                            "rca_uploaded_at": f_rca_at,
                            "rca_uploaded_by": f_rca_by,
                            
                            "pengajuan_disposed": f_pengajuan,
                            "pengajuan_disposed_uploaded_at": f_pengajuan_at,
                            "pengajuan_disposed_uploaded_by": f_pengajuan_by,
                        }
                    )
                    # Hapus dari tabel Disposed karena statusnya turun kembali ke Prepare
                    super().delete()
            except Exception as e:
                print(f"[Migration Error] Gagal memindahkan unit kembali ke Prepare: {e}")

    class Meta:
        verbose_name = "Report Eqp Disposed"
        verbose_name_plural = "Report Eqp Disposed"
        ordering = ['-LAST_UPDATED_YEAR', '-LAST_UPDATED_MONTH', 'asset__CN_SAP']

    def __str__(self):
        return f"{self.asset.CN_SAP if self.asset else self.pk}"
 
# ===========================================================================
# ── MODELS KHUSUS ASSETEQUIPMENTPREAPREDISPOSED ────────────────────
# ===========================================================================

class AssetEquipmentPrepareDisposed(models.Model):
    """
    Model Mandiri untuk Fase 1 (Prepare for Disposed).
    Berdiri sendiri dengan tabel fisik di database, menggunakan relasi OneToOne 
    terhadap AssetEquipment berdasarkan CN_SAP.
    """
    asset = models.OneToOneField(
        AssetEquipment, 
        on_delete=models.CASCADE, 
        related_name='prepare_disposed_details',
        to_field='CN_SAP',
        db_column='CN_SAP_id',
        primary_key=True,
    )
    No_Asset = models.CharField(max_length=100, blank=True, null=True, verbose_name="No Asset")
    CN_ELLIPSE = models.CharField(max_length=100, blank=True, null=True, verbose_name="Code Number Ellipse")
    EGI = models.CharField(max_length=100, blank=True, null=True)

    # Informasi umum unit
    TYPE = models.CharField(max_length=100, blank=True, null=True, verbose_name="Type")
    GROUP = models.CharField(max_length=100, blank=True, null=True, verbose_name="Class Equipment")
    CLASS_WEIGHT = models.CharField(max_length=100, blank=True, null=True, verbose_name="Class Weight")
    OWNERSHIP = models.CharField(max_length=100, blank=True, null=True, verbose_name="Ownership")
    BRAND = models.CharField(max_length=100, blank=True, null=True, verbose_name="Brand")
    SN = models.CharField(max_length=100, blank=True, null=True, verbose_name="Serial Number")

    # Lokasi dan Bagian
    SECTION = models.CharField(max_length=100, blank=True, null=True, verbose_name="Section")
    LOCATION = models.CharField(max_length=100, blank=True, null=True, verbose_name="Location")
    SUB_SITE = models.CharField(max_length=100, blank=True, null=True, verbose_name="Sub Site")
    SUB_LOCATION = models.CharField(max_length=100, blank=True, null=True, verbose_name="Sub Location")

    # Informasi HM / SPO
    HM_SMR = models.CharField(max_length=100, blank=True, null=True, verbose_name="Hour Meter")
    HM_DATE = models.DateField(blank=True, null=True, verbose_name="Hour Meter Date")
    SPO_EQUIPMENT = models.IntegerField(blank=True, null=True, verbose_name="SPO Equipment")
    PERSENTASE_SPO = models.FloatField(blank=True, null=True, verbose_name="% SPO Equipment")
    nbv_prepare = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True, verbose_name='NBV')
    
    # Status
    EQUIPMENT_CONDITION = models.CharField(max_length=100, default='PREPARE FOR DISPOSED', verbose_name="Equipment Condition")
    STATUS_EQUIPMENT = models.CharField(max_length=100, blank=True, null=True, verbose_name="Status Equipment")
    STATUS_EQUIPMENT_DISPOSED = models.CharField(max_length=100, blank=True, null=True, verbose_name="Status Equipment Disposed")
    REFERENSI_NO_PDE = models.CharField(max_length=100, blank=True, null=True, verbose_name="Referensi No PDE")
    BP = models.CharField(max_length=255, blank=True, null=True, verbose_name="BP")

    
    # ── STATUS APPROVAL PER FORM (INDEPENDEN) ────────────────────
    # ── STATUS APPROVAL PER FOTO 4 SISI ────────────────────

    foto_4_sisi_status = models.CharField(
        max_length=20,
        choices=[
            ('DRAFT', 'Draft'),
            ('WAITING', 'Menunggu Approval'),
            ('APPROVED', 'Disetujui'),
            ('REJECTED', 'Ditolak')
        ],
        default='DRAFT',
        verbose_name="Status Foto 4 Sisi"
    )
    foto_4_sisi_submitted_at = models.DateTimeField(null=True, blank=True)
    foto_4_sisi_submitted_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True, related_name='foto4sisi_submitted_by')
    foto_4_sisi_approved_at   = models.DateTimeField(null=True, blank=True)
    foto_4_sisi_approved_by   = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True, related_name='foto4sisi_approved_by')
    foto_4_sisi_rejected_at   = models.DateTimeField(null=True, blank=True)
    foto_4_sisi_rejected_by   = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True,related_name='foto4sisi_rejected_by')
    foto_4_sisi_approver      = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True,related_name='foto4sisi_current_approver')
    foto_4_sisi_catatan_reject = models.TextField(blank=True, null=True)

     # ── 📂 1. FOTO 4 SISI UTAMA (PDF) ──────────────────────────────────
    foto_4_sisi = models.FileField(upload_to='disposed/foto_4_sisi/', blank=True, null=True, verbose_name="Foto 4 Sisi (PDF)")
    foto_4_sisi_uploaded_at = models.DateTimeField(null=True, blank=True, verbose_name="Foto 4 Sisi Diupload Pada")
    foto_4_sisi_uploaded_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True, related_name='prep_foto_4_sisi', verbose_name="Foto 4 Sisi Diupload Oleh")

    # ── 📂 2. FOTO 4 SISI — 4 File Terpisah ────────────────────────────
    tampak_depan = models.FileField(upload_to='prepare_disposed/foto_4_sisi/', blank=True, null=True, verbose_name="Tampak Depan")
    tampak_depan_uploaded_at = models.DateTimeField(null=True, blank=True, verbose_name="Tampak Depan Diupload Pada")
    tampak_depan_uploaded_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True, related_name='prep_tampak_depan', verbose_name="Tampak Depan Diupload Oleh")

    tampak_belakang = models.FileField(upload_to='prepare_disposed/foto_4_sisi/', blank=True, null=True, verbose_name="Tampak Belakang")
    tampak_belakang_uploaded_at = models.DateTimeField(null=True, blank=True, verbose_name="Tampak Belakang Diupload Pada")
    tampak_belakang_uploaded_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True, related_name='prep_tampak_belakang', verbose_name="Tampak Belakang Diupload Oleh")

    tampak_samping_kanan = models.FileField(upload_to='prepare_disposed/foto_4_sisi/', blank=True, null=True, verbose_name="Tampak Samping Kanan")
    tampak_samping_kanan_uploaded_at = models.DateTimeField(null=True, blank=True, verbose_name="Tampak Samping Kanan Diupload Pada")
    tampak_samping_kanan_uploaded_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True, related_name='prep_tampak_samping_kanan', verbose_name="Tampak Samping Kanan Diupload Oleh")

    tampak_samping_kiri = models.FileField(upload_to='prepare_disposed/foto_4_sisi/', blank=True, null=True, verbose_name="Tampak Samping Kiri")
    tampak_samping_kiri_uploaded_at = models.DateTimeField(null=True, blank=True, verbose_name="Tampak Samping Kiri Diupload Pada")
    tampak_samping_kiri_uploaded_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True, related_name='prep_tampak_samping_kiri', verbose_name="Tampak Samping Kiri Diupload Oleh")


    # ── STATUS APPROVAL FORM ISNPEKSI ────────────────────
    inspeksi_status = models.CharField(
        max_length=20,
        choices=[
            ('DRAFT',    'Draft'),
            ('WAITING',  'Menunggu Approval'),
            ('APPROVED', 'Disetujui'),
            ('REJECTED', 'Ditolak'),
        ],
        default='DRAFT',
        verbose_name="Status Inspeksi Unit"
    )
    inspeksi_submitted_at  = models.DateTimeField(null=True, blank=True)
    inspeksi_submitted_by  = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True, related_name='inspeksi_submitted_by')
    inspeksi_approved_at   = models.DateTimeField(null=True, blank=True)
    inspeksi_approved_by   = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True,related_name='inspeksi_approved_by')
    inspeksi_rejected_at   = models.DateTimeField(null=True, blank=True)
    inspeksi_rejected_by   = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True,related_name='inspeksi_rejected_by')
    inspeksi_approver      = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True,related_name='inspeksi_current_approver')
    inspeksi_catatan_reject = models.TextField(blank=True, null=True)


    

    # ── DOKUMEN PENDUKUNG LAINNYA ───────────────────────────────────────
    inspeksi_unit = models.FileField(upload_to='disposed/inspeksi_unit/', blank=True, null=True, verbose_name="Inspeksi Unit")
    inspeksi_unit_uploaded_at = models.DateTimeField(null=True, blank=True, verbose_name="Inspeksi Unit Diupload Pada")
    inspeksi_unit_uploaded_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True, related_name='prep_inspeksi_unit', verbose_name="Inspeksi Unit Diupload Oleh")

    rca = models.FileField(upload_to='disposed/rca/', blank=True, null=True, verbose_name="RCA")
    rca_uploaded_at = models.DateTimeField(null=True, blank=True, verbose_name="RCA Diupload Pada")
    rca_uploaded_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True, related_name='prep_rca', verbose_name="RCA Diupload Oleh")

    pengajuan_disposed = models.FileField(upload_to='disposed/pengajuan/', blank=True, null=True, verbose_name="Pengajuan Disposed Equipment")
    pengajuan_disposed_uploaded_at = models.DateTimeField(null=True, blank=True, verbose_name="Pengajuan Disposed Diupload Pada")
    pengajuan_disposed_uploaded_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True, related_name='prep_pengajuan_disposed', verbose_name="Pengajuan Disposed Diupload Oleh")

    updated_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True, verbose_name="Diubah Oleh")

    # Tambahkan field pendukung inspeksi unit di dalam model AssetEquipmentPrepareDisposed jika diperlukan
    inspeksi_item_status = models.CharField(max_length=50, default='DRAFT', verbose_name="Status Inspeksi Item")
    inspeksi_item_uploaded_at = models.DateTimeField(null=True, blank=True, verbose_name="Inspeksi Item Diisi Pada")
    inspeksi_item_uploaded_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True, related_name='prep_inspeksi_item', verbose_name="Inspeksi Item Diisi Oleh")
   
    STATUS_CHOICES = (
        ('DRAFT', 'Draft / Belum Disubmit'),
        ('WAITING', 'Menunggu Approval Atasan'),
        ('APPROVED', 'Disetujui'),
        ('REJECTED', 'Ditolak / Perlu Revisi'),
    )
    status_approval = models.CharField(choices=STATUS_CHOICES, default='DRAFT', max_length=20)
    current_approver = models.ForeignKey(User, null=True, blank=True, on_delete=models.SET_NULL, related_name='pending_approvals')  
    catatan_reject = models.TextField(blank=True, null=True,verbose_name='Catatan Penolakan / Revisi')
    

    # 🆕 TAMBAHAN BARU: Field tracking waktu dan user untuk lifecycle approval
    submitted_at = models.DateTimeField(null=True, blank=True, verbose_name="Disubmit Pada")
    submitted_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True, related_name='prep_submitted_by', verbose_name="Disubmit Oleh")
    
    approved_at = models.DateTimeField(null=True, blank=True, verbose_name="Disetujui Pada")
    approved_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True, related_name='prep_approved_by', verbose_name="Disetujui Oleh")
    
    rejected_at = models.DateTimeField(null=True, blank=True, verbose_name="Ditolak/Revisi Pada")
    rejected_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True, related_name='prep_rejected_by', verbose_name="Ditolak/Revisi Oleh")

       
    # Waktu perubahan umum (auto_now=True)
    updated_at = models.DateTimeField(auto_now=True, verbose_name="Diperbarui Pada")

    # ── KONSTANTA HELPER ───────────────────────────────────────────────
    DOC_FIELDS = ['foto_4_sisi', 'inspeksi_unit', 'rca', 'pengajuan_disposed']
    REQUIRED_DOCS = ['inspeksi_unit', 'rca', 'pengajuan_disposed']

    DOC_LABELS = {
        'foto_4_sisi': 'Foto 4 Sisi (PDF)',
        'inspeksi_unit': 'Inspeksi Unit',
        'rca': 'RCA',
        'pengajuan_disposed': 'Pengajuan Disposed',
    }

    FOTO_TERPISAH_FIELDS = [
        'tampak_depan', 
        'tampak_belakang', 
        'tampak_samping_kanan', 
        'tampak_samping_kiri'
    ]

    # ── PROPERTIES & METHODS ───────────────────────────────────────────
    
    @property
    def semua_form_selesai(self):
        """True jika tidak ada form yang masih WAITING."""
        return (
            self.foto_4_sisi_status not in ('WAITING',) and
            self.inspeksi_status    not in ('WAITING',)
        )

    @property
    def ada_form_waiting(self):
        """True jika ada minimal satu form yang masih WAITING."""
        return (
            self.foto_4_sisi_status == 'WAITING' or
            self.inspeksi_status    == 'WAITING'
        )
    

    @property
    def foto_4_sisi_terpisah_lengkap(self):
        """True jika ke-4 foto terpisah sudah diupload semua."""
        return all(bool(getattr(self, f)) for f in self.FOTO_TERPISAH_FIELDS)
     
    @property
    def is_ready_for_disposed(self):
        foto_ok = bool(self.foto_4_sisi) or self.foto_4_sisi_terpisah_lengkap
        dokumen_ok = all(bool(getattr(self, f)) for f in self.REQUIRED_DOCS)
        return foto_ok and dokumen_ok

    @property
    def dokumen_lengkap(self):
        return [f for f in self.REQUIRED_DOCS if getattr(self, f)]

    @property
    def dokumen_kurang(self):
        return [f for f in self.REQUIRED_DOCS if not getattr(self, f)]

    @property
    def jumlah_lengkap(self):
        foto_ok = 1 if (bool(self.foto_4_sisi) or self.foto_4_sisi_terpisah_lengkap) else 0
        return foto_ok + len(self.dokumen_lengkap)

    @property
    def total_required(self):
        return 1 + len(self.REQUIRED_DOCS)

    @property
    def persentase_lengkap(self):
        total = self.total_required
        return round(self.jumlah_lengkap / total * 100) if total else 0  
      
    @property
    def total_dokumen(self):
        return len(self.DOC_FIELDS)
      
    @property
    def is_phase_1_complete(self):
        ada_foto = bool(self.foto_4_sisi) or self.foto_4_sisi_terpisah_lengkap
        return bool(
            ada_foto and 
            self.rca and 
            self.inspeksi_unit and 
            self.pengajuan_disposed
        )

    @property
    def jumlah_complete(self):
        ada_foto = 1 if (bool(self.foto_4_sisi) or self.foto_4_sisi_terpisah_lengkap) else 0
        docs = [self.rca, self.inspeksi_unit, self.pengajuan_disposed]
        return ada_foto + sum(1 for d in docs if d)

    @property
    def persentase_complete(self):
        total_dokumen = 4
        completed = self.jumlah_complete
        return round((completed / total_dokumen) * 100)

    @property
    def is_all_complete(self):
        return self.jumlah_complete >= self.total_dokumen

    def get_status_per_dokumen(self):
        status_dict = {}
        ada_foto = bool(self.foto_4_sisi) or self.foto_4_sisi_terpisah_lengkap
        status_dict['foto_4_sisi'] = 'COMPLETE' if ada_foto else 'PROGRESS'
        
        for field in self.REQUIRED_DOCS:
            status_dict[field] = 'COMPLETE' if getattr(self, field) else 'PROGRESS'
        return status_dict
      
    # ── 🔄 AUTOMATISASI STATUS & MIGRASI OTOMATIS KE DISPOSED ────────────

    def save(self, *args, **kwargs):
        import os
        from .models import AssetEquipmentDisposed, AssetEquipment
        from django.db import transaction

        cn_sap_value = None
        if self.asset:
            cn_sap_value = getattr(self.asset, 'CN_SAP', None)
        elif self.pk:
            cn_sap_value = self.pk
        
        print(f"\n[DEBUG SAVE MASTER-BASED] CN_SAP: {cn_sap_value}")

        existing_prep = None
        if cn_sap_value:
            existing_prep = AssetEquipmentPrepareDisposed.objects.filter(asset_id=cn_sap_value).first()

        # Gabungkan field dokumen utama dan foto terpisah untuk pengecekan penghapusan file
        ALL_TRACKED_FILES = self.DOC_FIELDS + self.FOTO_TERPISAH_FIELDS

        # Cek apakah ada flag dari view untuk mengosongkan foto/dokumen secara paksa
        force_clear = getattr(self, '_force_clear_photos', False)

        if existing_prep:
            for field in ALL_TRACKED_FILES:
                old_file = getattr(existing_prep, field, None)
                new_file = getattr(self, field, None)
                
                # Jika di-clear paksa atau file baru kosong dan memang sengaja dihapus
                if old_file and (not new_file or force_clear):
                    if hasattr(old_file, 'path') and os.path.exists(old_file.path):
                        try:
                            os.remove(old_file.path)
                        except Exception:
                            pass

                    # Reset nilai field menjadi None jika force_clear aktif
                    if force_clear:
                        setattr(self, field, None)

                    # Reset metadata khusus untuk foto utama jika dihapus
                    if field == 'foto_4_sisi':
                        self.foto_4_sisi_uploaded_at = None
                        self.foto_4_sisi_uploaded_by = None
                    print(f"[FILE DELETE & RESET] Dokumen/Foto '{field}' dihapus user.")

        # Lindungi file lama jika input baru kosong (HANYA jika tidak sedang force_clear)
        if existing_prep and not force_clear:
            for field in self.DOC_FIELDS:
                new_val = getattr(self, field, None)
                old_val = getattr(existing_prep, field, None)
                if not new_val and old_val and getattr(self, f"{field}_uploaded_at", None) is not None:
                    setattr(self, field, old_val)

            # Lindungi juga 4 foto terpisah dari data lama jika tidak di-update
            for field in self.FOTO_TERPISAH_FIELDS:
                new_val = getattr(self, field, None)
                old_val = getattr(existing_prep, field, None)
                if not new_val and old_val:
                    setattr(self, field, old_val)

        is_complete = self.is_phase_1_complete
        target_condition = 'DISPOSED' if is_complete else 'PREPARE FOR DISPOSED'
        self.EQUIPMENT_CONDITION = target_condition

        super().save(*args, **kwargs)
        print("[DEBUG SAVE SUCCESS] Data prepare disimpan dengan aman.")

        if cn_sap_value:
            AssetEquipment.objects.filter(CN_SAP=cn_sap_value).update(
                EQUIPMENT_CONDITION=target_condition
            )
            if self.asset and self.asset.EQUIPMENT_CONDITION != target_condition:
                self.asset.EQUIPMENT_CONDITION = target_condition
                self.asset.save(update_fields=['EQUIPMENT_CONDITION'])

        if is_complete and cn_sap_value:
            try:
                current_db_instance = AssetEquipmentPrepareDisposed.objects.filter(pk=self.pk).first()
                if current_db_instance:
                    existing_disposed = AssetEquipmentDisposed.objects.filter(asset=self.asset).first()

                    f_foto = current_db_instance.foto_4_sisi or (existing_disposed.foto_4_sisi if existing_disposed else None)
                    f_foto_at = current_db_instance.foto_4_sisi_uploaded_at or (existing_disposed.foto_4_sisi_uploaded_at if existing_disposed else None)
                    f_foto_by = current_db_instance.foto_4_sisi_uploaded_by or (existing_disposed.foto_4_sisi_uploaded_by if existing_disposed else None)

                    f_inspeksi = current_db_instance.inspeksi_unit or (existing_disposed.inspeksi_unit if existing_disposed else None)
                    f_inspeksi_at = current_db_instance.inspeksi_unit_uploaded_at or (existing_disposed.inspeksi_unit_uploaded_at if existing_disposed else None)
                    f_inspeksi_by = current_db_instance.inspeksi_unit_uploaded_by or (existing_disposed.inspeksi_unit_uploaded_by if existing_disposed else None)

                    f_rca = current_db_instance.rca or (existing_disposed.rca if existing_disposed else None)
                    f_rca_at = current_db_instance.rca_uploaded_at or (existing_disposed.rca_uploaded_at if existing_disposed else None)
                    f_rca_by = current_db_instance.rca_uploaded_by or (existing_disposed.rca_uploaded_by if existing_disposed else None)

                    f_pengajuan = current_db_instance.pengajuan_disposed or (existing_disposed.pengajuan_disposed if existing_disposed else None)
                    f_pengajuan_at = current_db_instance.pengajuan_disposed_uploaded_at or (existing_disposed.pengajuan_disposed_uploaded_at if existing_disposed else None)
                    f_pengajuan_by = current_db_instance.pengajuan_disposed_uploaded_by or (existing_disposed.pengajuan_disposed_uploaded_by if existing_disposed else None)

                    with transaction.atomic():
                        AssetEquipmentDisposed.objects.update_or_create(
                            asset=self.asset,
                            defaults={
                                "No_Asset": self.No_Asset,
                                "CN_ELLIPSE": self.CN_ELLIPSE,
                                "EGI": self.EGI,
                                "TYPE": self.TYPE,
                                "GROUP": self.GROUP,
                                "CLASS_WEIGHT": self.CLASS_WEIGHT,
                                "OWNERSHIP": self.OWNERSHIP,
                                "BRAND": self.BRAND,
                                "SN": self.SN,
                                "SECTION": self.SECTION,
                                "LOCATION": self.LOCATION,
                                "SUB_SITE": self.SUB_SITE,
                                "SUB_LOCATION": self.SUB_LOCATION,
                                "HM_SMR": self.HM_SMR,
                                "HM_DATE": self.HM_DATE,
                                "SPO_EQUIPMENT": self.SPO_EQUIPMENT,
                                "PERSENTASE_SPO": self.PERSENTASE_SPO,
                                "nbv_disposed": self.nbv_prepare,
                                "EQUIPMENT_CONDITION": 'DISPOSED',
                                "STATUS_EQUIPMENT": self.STATUS_EQUIPMENT,
                                "STATUS_EQUIPMENT_DISPOSED": self.STATUS_EQUIPMENT_DISPOSED,
                                "REFERENSI_NO_PDE": self.REFERENSI_NO_PDE,
                                "BP": self.BP,
                                "foto_4_sisi": f_foto,
                                "foto_4_sisi_uploaded_at": f_foto_at,
                                "foto_4_sisi_uploaded_by": f_foto_by,
                                "inspeksi_unit": f_inspeksi,
                                "inspeksi_unit_uploaded_at": f_inspeksi_at,
                                "inspeksi_unit_uploaded_by": f_inspeksi_by,
                                "rca": f_rca,
                                "rca_uploaded_at": f_rca_at,
                                "rca_uploaded_by": f_rca_by,
                                "pengajuan_disposed": f_pengajuan,
                                "pengajuan_disposed_uploaded_at": f_pengajuan_at,
                                "pengajuan_disposed_uploaded_by": f_pengajuan_by,
                                "updated_by": self.updated_by,
                            }
                        )
                        super().delete()
            except Exception as e:
                print(f"[Migration Error] Gagal pindah ke Disposed: {e}")

    class Meta:
        verbose_name = "Standby For Disposed"
        verbose_name_plural = "Checksheet Inspection Unit"
        ordering = ['asset__CN_SAP']

    def __str__(self):
        return f"{self.asset.CN_SAP if self.asset else self.pk} - Standby For Disposed" 
    
#===========================================================================================
# ================Model untuk unit yang Master Data Equipment Status ===============================
#===========================================================================================
    
class AssetMasterMonthlyStatus(models.Model):         
    No_Asset = models.CharField(max_length=255, blank=True, default='Unknown' )
    CN_SAP = models.CharField(max_length=255, blank=True, default='Unknown')   
    CN_ELLIPSE = models.CharField(max_length=255, blank=True, default='Unknown')
    EGI = models.CharField(max_length=255, blank=True, default='Unknown')
    TYPE =models.CharField(max_length=255, blank=True, default='Unknown')
    FOTO = CloudinaryField('image', folder='asset/monthly_reports/images/', blank=True, null=True)
    GROUP =models.CharField(max_length=255, blank=True, default='Unknown')
    CLASS_WEIGHT = models.CharField(max_length=255, blank=True, default='Unknown')
    LOCATION_CODE_SAP = models.CharField(max_length=255, blank=True, default='Unknown')
    OWNERSHIP = models.CharField(max_length=255, blank=True, default='Unknown')
    SECTION = models.CharField(max_length=255, blank=True, default='Unknown')
    LOCATION = models.CharField(max_length=255, blank=True, default='Unknown')
    SUB_SITE =models.CharField(max_length=255, blank=True, default='Unknown')
    SUB_LOCATION = models.CharField(max_length=255, blank=True, default='Unknown')   
    BRAND = models.CharField(max_length=255, blank=True, default='Unknown')
    SN = models.CharField(max_length=255, blank=True, default='Unknown')
    HM_SMR = models.CharField(max_length=255, blank=True, null=True)
    HM_DATE = models.DateField(null=True, blank=True)
    SPO_EQUIPMENT = models.IntegerField(blank=True, null=True)
    PERSENTASE_SPO = models.FloatField(null=True, blank=True)
    EQUIPMENT_CONDITION = models.CharField(max_length=255,blank=True, default='Unknown')
    STATUS_EQUIPMENT = models.CharField(max_length=255, blank=True, default='Unknown')
    STATUS_EQUIPMENT_DISPOSED = models.CharField(max_length=100, blank=True, null=True, verbose_name="Status Equipment Disposed")  
    STATUS_SAP = models.CharField(max_length=255, blank=True)
    NBV = models.DecimalField( max_digits=10, decimal_places=2, null=True, blank=True, verbose_name='NBV')
    WEIGHT = models.DecimalField( max_digits=10, decimal_places=2, null=True, blank=True, verbose_name='WEIGHT')     
    REFERENSI_NO_PDE = models.CharField(max_length=255, blank=True)
    YEAR = models.IntegerField(blank=True, null=True)
    MONTH = models.DateField(blank=True, null=True)
    BP = models.CharField(max_length=255, blank=True, default='Unknown')


    def __str__(self):
        month_str = self.MONTH.strftime('%Y-%m') if self.MONTH else 'N/A' # Format lebih baik
        return f"{self.No_Asset} - {self.CN_SAP} ({month_str})" 
    
    class Meta:
        verbose_name = "Master Monthly Report"  
        verbose_name_plural = "Master Monthly Report" # Koreksi typo: Mothly -> Monthly
        # --- PERUBAHAN UTAMA: Tambahkan unique_together ---
        unique_together = ('CN_SAP', 'MONTH', 'YEAR',)


#===========================================================================================
# ================Model untuk unit yang Master Data Equipment Status ===============================
#===========================================================================================
    
class AssetFinalMonthlyStatus(models.Model):         
    No_Asset = models.CharField(max_length=255, blank=True, default='Unknown' )
    CN_SAP = models.CharField(max_length=255, blank=True, default='Unknown')   
    CN_ELLIPSE = models.CharField(max_length=255, blank=True, default='Unknown')
    EGI = models.CharField(max_length=255, blank=True, default='Unknown')
    TYPE =models.CharField(max_length=255, blank=True, default='Unknown')
    FOTO = CloudinaryField('image', folder='asset/monthly_reports/images/', blank=True, null=True)
    GROUP =models.CharField(max_length=255, blank=True, default='Unknown')
    CLASS_WEIGHT = models.CharField(max_length=255, blank=True, default='Unknown')
    LOCATION_CODE_SAP = models.CharField(max_length=255, blank=True, default='Unknown')
    OWNERSHIP = models.CharField(max_length=255, blank=True, default='Unknown')
    SECTION = models.CharField(max_length=255, blank=True, default='Unknown')
    LOCATION = models.CharField(max_length=255, blank=True, default='Unknown')
    SUB_SITE =models.CharField(max_length=255, blank=True, default='Unknown')
    SUB_LOCATION = models.CharField(max_length=255, blank=True, default='Unknown')   
    BRAND = models.CharField(max_length=255, blank=True, default='Unknown')
    SN = models.CharField(max_length=255, blank=True, default='Unknown')
    HM_SMR = models.CharField(max_length=255, blank=True, null=True)
    HM_DATE = models.DateField(null=True, blank=True)
    SPO_EQUIPMENT = models.IntegerField(blank=True, null=True)
    PERSENTASE_SPO = models.FloatField(null=True, blank=True)
    EQUIPMENT_CONDITION = models.CharField(max_length=255,blank=True, default='Unknown')
    STATUS_EQUIPMENT = models.CharField(max_length=255, blank=True, default='Unknown')
    STATUS_EQUIPMENT_DISPOSED = models.CharField(max_length=100, blank=True, null=True, verbose_name="Status Equipment Disposed")  
    STATUS_SAP = models.CharField(max_length=255, blank=True)
    NBV = models.DecimalField( max_digits=10, decimal_places=2, null=True, blank=True, verbose_name='NBV')
    WEIGHT = models.DecimalField( max_digits=10, decimal_places=2, null=True, blank=True, verbose_name='WEIGHT')     
    REFERENSI_NO_PDE = models.CharField(max_length=255, blank=True)
    YEAR = models.IntegerField(blank=True, null=True)
    MONTH = models.DateField(blank=True, null=True)
    BP = models.CharField(max_length=255, blank=True, default='Unknown')


    def __str__(self):
        month_str = self.MONTH.strftime('%Y-%m') if self.MONTH else 'N/A' # Format lebih baik
        return f"{self.No_Asset} - {self.CN_SAP} ({month_str})" 
    
    class Meta:
        verbose_name = "Final Monthly Report"  
        verbose_name_plural = "Summary Final Report" # Koreksi typo: Mothly -> Monthly
        # --- PERUBAHAN UTAMA: Tambahkan unique_together ---
        unique_together = ('CN_SAP', 'MONTH', 'YEAR',)



#===========================================================================================
# =============== Model untuk unit yang Standby   ==========================================
#===========================================================================================

class AssetEquipmentStandby(models.Model):
    # Field-field ini akan menjadi identifier unik untuk unit disposed
    asset = models.OneToOneField(
        AssetEquipment, 
        on_delete=models.CASCADE, 
        related_name='standby_details',  # 🌟 Unik
        to_field='CN_SAP',
        db_column='CN_SAP_id',
        primary_key=True,
    ) # CN_SAP akan menjadi unik di sini
    No_Asset = models.CharField(max_length=100, blank=True, null=True, verbose_name="No Asset")
    CN_ELLIPSE = models.CharField(max_length=100, blank=True, null=True, verbose_name="Code Number Ellipse")
    EGI = models.CharField(max_length=100, blank=True, null=True)

    # Informasi umum unit
    TYPE = models.CharField(max_length=100, blank=True, null=True, verbose_name="Type")
    GROUP = models.CharField(max_length=100, blank=True, null=True, verbose_name="Class Equipment")
    CLASS_WEIGHT = models.CharField(max_length=100, blank=True, null=True, verbose_name="Class Weight")
    OWNERSHIP = models.CharField(max_length=100, blank=True, null=True, verbose_name="Ownership")
    BRAND = models.CharField(max_length=100, blank=True, null=True, verbose_name="Brand")
    SN = models.CharField(max_length=100, blank=True, null=True, verbose_name="Serial Number")

    # Lokasi dan Bagian
    SECTION = models.CharField(max_length=100, blank=True, null=True, verbose_name="Section")
    LOCATION = models.CharField(max_length=100, blank=True, null=True, verbose_name="Location")
    SUB_SITE = models.CharField(max_length=100, blank=True, null=True, verbose_name="Sub Site")
    SUB_LOCATION = models.CharField(max_length=100, blank=True, null=True, verbose_name="Sub Location")

    # Informasi HM / SPO
    HM_SMR = models.CharField(max_length=100, blank=True, null=True, verbose_name="Hour Meter") # CharField jika mungkin ada non-numeric
    HM_DATE = models.DateField(blank=True, null=True, verbose_name="Hour Meter Date")
    SPO_EQUIPMENT = models.IntegerField(blank=True, null=True, verbose_name="SPO Equipment")
    PERSENTASE_SPO = models.FloatField(blank=True, null=True, verbose_name="% SPO Equipment")
    nbv_disposed = models.DecimalField( max_digits=10, decimal_places=2, null=True, blank=True, verbose_name='NBV')
    # Status Disposal
    EQUIPMENT_CONDITION = models.CharField(max_length=100, default='STANDBY', verbose_name="Equipment Condition")
    STATUS_EQUIPMENT = models.CharField(max_length=100, blank=True, null=True, verbose_name="Status Equipment")
    STATUS_EQUIPMENT_DISPOSED = models.CharField(max_length=100, blank=True, null=True, verbose_name="Status Equipment Disposed")
    REFERENSI_NO_PDE = models.CharField(max_length=100, blank=True, null=True, verbose_name="Referensi No PDE")

    # Metadata kapan terakhir diperbarui (dari data bulanan mana)
    LAST_UPDATED_MONTH = models.IntegerField(blank=True, null=True, verbose_name="Bulan Data Terakhir Diperbarui")
    LAST_UPDATED_YEAR = models.IntegerField(blank=True, null=True, verbose_name="Tahun Data Terakhir Diperbarui")
    UPDATED_AT = models.DateTimeField(auto_now=True, verbose_name="Waktu Pembaruan") # Waktu sebenarnya di-update
    BP = models.CharField(max_length=255, blank=True,null=True, verbose_name="BP")
    # Anda juga bisa menambahkan field FOTO jika ingin menyimpan foto terakhir dari disposed unit
    # FOTO = models.ImageField(upload_to='disposed_equipment_photos/', blank=True, null=True)

    # ── 📂 MERGER FIELD DIGITAL DOKUMEN STANDBY ────────────────────────
    ba_standby = models.FileField(upload_to='documents/standby/', blank=True, null=True, verbose_name="BA Standby")
    ba_standby_uploaded_at = models.DateTimeField(null=True, blank=True, verbose_name="BA Standby Diupload Pada")
    ba_standby_uploaded_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True, related_name='uploaded_ba_standby')

    # --untuk simpan user login----
    updated_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True, verbose_name="Diubah Oleh")

    # ── KONSTANTA HELPER UNTUK TRACKING DI VIEW & ADMIN ─────────────────
    DOC_FIELDS = ['ba_standby']

    DOC_LABELS = {
        'ba_standby': 'BA Standby',
    }

    # ── LOGIKA PROGRESS UTK TRACKING KELENGKAPAN (Disesuaikan) ──────────
    @property
    def total_dokumen(self):
        return len(self.DOC_FIELDS)

    @property
    def jumlah_complete(self):
        return sum(1 for field in self.DOC_FIELDS if getattr(self, field))

    @property
    def jumlah_progress(self):
        return self.total_dokumen - self.jumlah_complete

    @property
    def persentase_complete(self):
        if self.total_dokumen == 0: return 0
        return round((self.jumlah_complete / self.total_dokumen) * 100)

    @property
    def is_all_complete(self):
        return self.jumlah_complete == self.total_dokumen

    class Meta:
        verbose_name = "Report Eqp Standby"
        verbose_name_plural = "Report Eqp Standby"
        ordering = ['-LAST_UPDATED_YEAR', '-LAST_UPDATED_MONTH', 'asset__CN_SAP'] 

    def __str__(self):
        return f"{self.asset.CN_SAP if self.asset else self.pk}"

       
#===========================================================================================
# =============== Model untuk unit yang Breakdown   ========================================
#===========================================================================================

class AssetEquipmentBreakdown(models.Model):
    # Field-field ini akan menjadi identifier unik untuk unit disposed
    asset = models.OneToOneField(
        AssetEquipment, 
        on_delete=models.CASCADE, 
        related_name='breakdown_details', # 🌟 Unik
        to_field='CN_SAP',
        db_column='CN_SAP_id',
        primary_key=True,
    ) # CN_SAP akan menjadi unik di sini
    No_Asset = models.CharField(max_length=100, blank=True, null=True, verbose_name="No Asset")
    CN_ELLIPSE = models.CharField(max_length=100, blank=True, null=True, verbose_name="Code Number Ellipse")
    EGI = models.CharField(max_length=100, blank=True, null=True)

    # Informasi umum unit
    TYPE = models.CharField(max_length=100, blank=True, null=True, verbose_name="Type")
    GROUP = models.CharField(max_length=100, blank=True, null=True, verbose_name="Class Equipment")
    CLASS_WEIGHT = models.CharField(max_length=100, blank=True, null=True, verbose_name="Class Weight")
    OWNERSHIP = models.CharField(max_length=100, blank=True, null=True, verbose_name="Ownership")
    BRAND = models.CharField(max_length=100, blank=True, null=True, verbose_name="Brand")
    SN = models.CharField(max_length=100, blank=True, null=True, verbose_name="Serial Number")

    # Lokasi dan Bagian
    SECTION = models.CharField(max_length=100, blank=True, null=True, verbose_name="Section")
    LOCATION = models.CharField(max_length=100, blank=True, null=True, verbose_name="Location")
    SUB_SITE = models.CharField(max_length=100, blank=True, null=True, verbose_name="Sub Site")
    SUB_LOCATION = models.CharField(max_length=100, blank=True, null=True, verbose_name="Sub Location")

    # Informasi HM / SPO
    HM_SMR = models.CharField(max_length=100, blank=True, null=True, verbose_name="Hour Meter") # CharField jika mungkin ada non-numeric
    HM_DATE = models.DateField(blank=True, null=True, verbose_name="Hour Meter Date")
    SPO_EQUIPMENT = models.IntegerField(blank=True, null=True, verbose_name="SPO Equipment")
    PERSENTASE_SPO = models.FloatField(blank=True, null=True, verbose_name="% SPO Equipment")
    nbv_disposed = models.DecimalField( max_digits=10, decimal_places=2, null=True, blank=True, verbose_name='NBV')

    # Status Disposal
    EQUIPMENT_CONDITION = models.CharField(max_length=100, default='BREAKDOWN', verbose_name="Equipment Condition")
    STATUS_EQUIPMENT = models.CharField(max_length=100, blank=True, null=True, verbose_name="Status Equipment")
    STATUS_EQUIPMENT_DISPOSED = models.CharField(max_length=100, blank=True, null=True, verbose_name="Status Equipment Disposed")
    REFERENSI_NO_PDE = models.CharField(max_length=100, blank=True, null=True, verbose_name="Referensi No PDE")

    # Metadata kapan terakhir diperbarui (dari data bulanan mana)
    LAST_UPDATED_MONTH = models.IntegerField(blank=True, null=True, verbose_name="Bulan Data Terakhir Diperbarui")
    LAST_UPDATED_YEAR = models.IntegerField(blank=True, null=True, verbose_name="Tahun Data Terakhir Diperbarui")
    UPDATED_AT = models.DateTimeField(auto_now=True, verbose_name="Waktu Pembaruan") # Waktu sebenarnya di-update
    BP = models.CharField(max_length=255, blank=True,null=True, verbose_name="BP")
    # Anda juga bisa menambahkan field FOTO jika ingin menyimpan foto terakhir dari disposed unit
    # FOTO = models.ImageField(upload_to='disposed_equipment_photos/', blank=True, null=True)

    # ── 📂 MERGER FIELD DIGITAL DOKUMEN BREAKDOWN ──────────────────────
    ba_breakdown = models.FileField(upload_to='documents/breakdown/', blank=True, null=True, verbose_name="BA Breakdown")
    ba_breakdown_uploaded_at = models.DateTimeField(null=True, blank=True, verbose_name="BA Breakdown Diupload Pada")
    ba_breakdown_uploaded_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True, related_name='uploaded_ba_breakdown')

    updated_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True, verbose_name="Diubah Oleh")
    # ── KONSTANTA HELPER UNTUK TRACKING DI VIEW & ADMIN ─────────────────
    DOC_FIELDS = ['ba_breakdown']

    DOC_LABELS = {
        'ba_breakdown': 'BA Breakdown',
    }

    # ── LOGIKA PROGRESS UTK TRACKING KELENGKAPAN (Disesuaikan) ──────────
    @property
    def total_dokumen(self):
        return len(self.DOC_FIELDS)

    @property
    def jumlah_complete(self):
        return sum(1 for field in self.DOC_FIELDS if getattr(self, field))

    @property
    def jumlah_progress(self):
        return self.total_dokumen - self.jumlah_complete

    @property
    def persentase_complete(self):
        if self.total_dokumen == 0: return 0
        return round((self.jumlah_complete / self.total_dokumen) * 100)

    @property
    def is_all_complete(self):
        return self.jumlah_complete == self.total_dokumen

    class Meta:
        verbose_name = "Report Eqp Breakdown"
        verbose_name_plural = "Report Eqp Breakdown"
        ordering = ['-LAST_UPDATED_YEAR', '-LAST_UPDATED_MONTH', 'asset__CN_SAP'] # Urutkan berdasarkan bulan/tahun terbaru


    def __str__(self):
        return f"{self.asset.CN_SAP if self.asset else self.pk}"


#===========================================================================================
# ================Model untuk unit yang Operate ============================================
#===========================================================================================
    
class AssetEquipmentOperate(models.Model):         
    asset = models.OneToOneField(
        AssetEquipment, 
        on_delete=models.CASCADE, 
        related_name='operate_details', # 🌟 Unik
        to_field='CN_SAP',
        db_column='CN_SAP_id',
        primary_key=True,
    ) # CN_SAP akan menjadi unik di sini 
    No_Asset = models.CharField(max_length=255, blank=True, default='Unknown' )
    CN_ELLIPSE = models.CharField(max_length=255, blank=True, default='Unknown')
    EGI = models.CharField(max_length=255, blank=True, default='Unknown')

    # Informasi umum unit
    TYPE =models.CharField(max_length=255, blank=True, default='Unknown')
    FOTO = CloudinaryField('image', folder='asset/monthly_reports/images/', blank=True, null=True)
    GROUP =models.CharField(max_length=255, blank=True, default='Unknown')
    CLASS_WEIGHT = models.CharField(max_length=255, blank=True, default='Unknown')
    OWNERSHIP = models.CharField(max_length=255, blank=True, default='Unknown')
    BRAND = models.CharField(max_length=255, blank=True, default='Unknown')
    SN = models.CharField(max_length=255, blank=True, default='Unknown')

    # Lokasi dan Bagian
    SECTION = models.CharField(max_length=255, blank=True, default='Unknown')
    LOCATION = models.CharField(max_length=255, blank=True, default='Unknown')
    SUB_SITE =models.CharField(max_length=255, blank=True, default='Unknown')
    SUB_LOCATION = models.CharField(max_length=255, blank=True, default='Unknown')   
    
    # Informasi HM / SPO
    HM_SMR = models.CharField(max_length=255, blank=True, null=True)
    HM_DATE = models.DateField(null=True, blank=True)
    SPO_EQUIPMENT = models.IntegerField(blank=True, null=True)
    PERSENTASE_SPO = models.FloatField(null=True, blank=True)
    NBV = models.DecimalField( max_digits=10, decimal_places=2, null=True, blank=True, verbose_name='NBV')

    # Status Disposal
    EQUIPMENT_CONDITION = models.CharField(max_length=255,blank=True)
    STATUS_EQUIPMENT = models.CharField(max_length=255, blank=True)
    STATUS_EQUIPMENT_DISPOSED = models.CharField(max_length=100, blank=True, null=True, verbose_name="Status Equipment Disposed")  
    REFERENSI_NO_PDE = models.CharField(max_length=255, blank=True)

    # Metadata kapan terakhir diperbarui (dari data bulanan mana)
    WEIGHT = models.DecimalField( max_digits=10, decimal_places=2, null=True, blank=True, verbose_name='WEIGHT')    
    YEAR = models.IntegerField(blank=True, null=True)
    MONTH = models.DateField(blank=True, null=True)
    BP = models.CharField(max_length=255, blank=True, default='Unknown')
   
    class Meta:
        verbose_name = "Report Eqp Operate"  
        verbose_name_plural = "Report Eqp Operate" # Koreksi typo: Mothly -> Monthly
        ordering = ['asset__CN_SAP']
        # --- PERUBAHAN UTAMA: Tambahkan unique_together ---
    
    def __str__(self):
        month_str = self.MONTH.strftime('%Y-%m') if self.MONTH else 'N/A' # Format lebih baik
        return f"{self.No_Asset} - {self.asset_id} ({month_str})" 
        