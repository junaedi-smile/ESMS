# accounts/models.py
from django.db import models
from django.contrib.auth.models import User

class UserProfile(models.Model):
    """
    Model ini menyimpan data tambahan pengguna, struktur hierarki organisasi, 
    dan keperluan approval bertingkat.
    """
    LOKASI_CHOICES = [
        ('ADMO', 'ADMO'),
        ('SERA', 'SERA'),
        ('MACO', 'MACO'),
    ]

    DEPARTMENT_CHOICES = [
        ('PJO', 'PJO'),
        ('PLANT', 'PLANT'),
        ('PRODUCTION', 'PRODUCTION'),
        ('ENGINEERING', 'ENGINEERING'),
        ('LOGISTIC', 'LOGISTIC'),
        ('SHE', 'SHE'),
        ('SCM', 'SCM'),
    ]

    SECTION_CHOICES = [
        # ADMO
        ('MINING - PDW', 'MINING - PDW'), ('MINING - PHW', 'MINING - PHW'),
        ('MINING - PLD', 'MINING - PLD'), ('MINING - PSU', 'MINING - PSU'),
        ('HAULING - KLANIS', 'HAULING - KLANIS'), ('HAULING - PFT', 'HAULING - PFT'),
        ('HAULING - PPM', 'HAULING - PPM'), ('HAULING - PTS', 'HAULING - PTS'),
        ('HAULING - PVE', 'HAULING - PVE'),
        # SERA
        ('PLANT-SERA', 'PLANT-SERA'),
        # MACO
        ('MACO - HAULING', 'MACO - HAULING'), ('MACO - MINING', 'MACO - MINING'),
    ]

    # Level Jabatan terstruktur dari yang tertinggi ke terendah
    LEVEL_JABATAN_CHOICES = [
        ('CHIEF_OPERATION', 'Chief Operation'),
        ('DEPT_HEAD', 'Department Head'),
        ('SECTION_HEAD', 'Section Head'),
        ('SENIOR_OFFICER', 'Senior Officer'),
        ('OFFICER', 'Officer'),
    ]

    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name='userprofile')
    lokasi = models.CharField(max_length=10, choices=LOKASI_CHOICES, blank=True, null=True)
    department = models.CharField(max_length=50, choices=DEPARTMENT_CHOICES, blank=True, null=True, verbose_name="Department")
    section = models.CharField(max_length=50, choices=SECTION_CHOICES, blank=True, null=True)
    
    # Jabatan terstruktur
    jabatan_level = models.CharField(max_length=30, choices=LEVEL_JABATAN_CHOICES, blank=True, null=True, verbose_name="Level Jabatan")
    jabatan_nama_resmi = models.CharField(max_length=100, blank=True, null=True, verbose_name="Nama Jabatan Spesifik (Cth: Plant Department Head)")
    
    # Atasan Langsung untuk keperluan routing approval bertingkat (Self-referencing foreign key)
    atasan_langsung = models.ForeignKey(
        'self', 
        on_delete=models.SET_NULL, 
        blank=True, 
        null=True, 
        related_name='bawahan_set',
        verbose_name="Atasan Langsung"
    )

    tanda_tangan = models.ImageField(upload_to='signatures/', blank=True, null=True, verbose_name="File Tanda Tangan")
    
    def __str__(self):
        level_display = self.get_jabatan_level_display() or 'Tanpa Jabatan'
        return f"[{self.lokasi or 'No Loc'}] {self.user.username} - {level_display} ({self.section or self.department or ''})"