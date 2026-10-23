# accounts/admin.py
from django.contrib import admin
from django.contrib.auth.admin import UserAdmin as BaseUserAdmin
from django.contrib.auth.models import User
from django.utils.html import format_html
from django.contrib.admin.sites import NotRegistered 
from django.contrib.admin.exceptions import AlreadyRegistered 
from django import forms

from .models import UserProfile
from asset.admin import admin_site  # Menggunakan Admin Site Kustom Anda

# 🌟 FORM KUSTOM UNTUK JAVASCRIPT AJAX DROPDOWN BERTINGKAT
class UserProfileForm(forms.ModelForm):
    class Meta:
        model = UserProfile
        fields = '__all__'

    class Media:
        # Menghubungkan file Javascript kustom ke dalam dashboard Jazzmin
        js = ('assets/js/dropdown_lokasi.js',)

# ------------------------------------------------------------------
# 1. INLINE ADMIN untuk UserProfile
# ------------------------------------------------------------------
class UserProfileInline(admin.StackedInline):
    model = UserProfile
    form = UserProfileForm  # Menggunakan form kustom yang membawa JS
    can_delete = False
    verbose_name_plural = 'Informasi Karyawan (Lokasi & Section)'
    
# ------------------------------------------------------------------
# 2. KUSTOMISASI USER ADMIN
# ------------------------------------------------------------------
class CustomUserAdmin(BaseUserAdmin):
    inlines = (UserProfileInline,)
    
    # Menampilkan NIK (username), Lokasi, Section, Status Superuser, dan Grup di list utama
    list_display = BaseUserAdmin.list_display + ('get_lokasi', 'get_section', 'is_superuser', 'groups_list')
    list_filter = BaseUserAdmin.list_filter + ('groups', 'is_superuser', 'is_active')

    def get_lokasi(self, obj):
        return obj.userprofile.lokasi if hasattr(obj, 'userprofile') else '-'
    get_lokasi.short_description = 'Lokasi'

    def get_section(self, obj):
        return obj.userprofile.section if hasattr(obj, 'userprofile') else '-'
    get_section.short_description = 'Section / PIC'

    def groups_list(self, obj):
        # Mengambil semua nama grup dengan rapi tanpa menggunakan backslash (\) yang rawan error
        groups = [group.name for group in obj.groups.all().order_by('name')]
        
        if not groups:
            return format_html('<span style="color: #6c757d;">(Tidak Ada Grup)</span>')
        return ", ".join(groups)

    groups_list.short_description = 'Grup User'
    groups_list.admin_order_field = 'groups__name'

# ------------------------------------------------------------------
# 3. HAPUS PENDAFTARAN DARI ADMIN SITE BAWAAN DAFTARKAN ULANG
# ------------------------------------------------------------------

try:
    # Hapus pendaftaran User bawaan Django yang standar
    admin.site.unregister(User)
except NotRegistered:
    pass 

# ------------------------------------------------------------------
# 4. DAFTARKAN PADA KEDUA ADMIN SITE (KUSTOM & DEFAULT JAZZMIN)
# ------------------------------------------------------------------

# A. Daftarkan ke Default Admin Site (Agar dibaca sempurna oleh tema Jazzmin Anda)
admin.site.register(User, CustomUserAdmin)

# B. Daftarkan ke Custom Admin Site Anda (INSIDE system)
try:
    admin_site.register(User, CustomUserAdmin)
except AlreadyRegistered:
    pass
except Exception as e:
    print(f"Error registering User on custom admin site: {e}")
    
# Daftarkan juga UserProfile ke kedua tempat agar aman
try:
    admin.site.register(UserProfile)
    admin_site.register(UserProfile)
except AlreadyRegistered:
    pass