# accounts/signals.py
from django.db.models.signals import pre_save, post_save
from django.dispatch import receiver
from django.contrib.auth.models import User, Group
from .models import UserProfile
from django.core.exceptions import ObjectDoesNotExist

# ==================================================================
# 🌟 SINYAL PRE-SAVE: OTOMATIS HASH PASSWORD AMAN TANPA CRASH
# ==================================================================
@receiver(pre_save, sender=User)
def hash_password_before_save(sender, instance, **kwargs):
    """
    Mengamankan password menjadi hash sebelum disimpan ke database.
    Mencegah double-hashing dan aman dari konflik form Jazzmin.
    """
    if instance.password:
        # Cek apakah password sudah dalam bentuk hash Django standar (pbkdf2, bcrypt, argon2)
        is_already_hashed = instance.password.startswith(('pbkdf2_sha256$', 'bcrypt$', 'argon2$', 'crypt$'))
        
        if not is_already_hashed:
            # Enkripsi teks murni (plain text) menjadi hash resmi Django
            instance.set_password(instance.password)


# ==================================================================
# SINYAL POST-SAVE: PEMBUATAN OTOMATIS PROFILE KARYAWAN
# ==================================================================
@receiver(post_save, sender=User)
def create_or_update_user_profile_and_group(sender, instance, created, **kwargs):
    # 1. Pastikan UserProfile selalu terbentuk aman
    try:
        instance.userprofile.save()
    except ObjectDoesNotExist:
        UserProfile.objects.create(user=instance)

    # 2. Tetapkan Grup Default (Hanya jika pengguna baru/IDK baru dibuat)
    if created:
        try:
            default_group = Group.objects.get(name='group_a')
            instance.groups.add(default_group)
            print(f"User '{instance.username}' successfully added to default group '{default_group.name}'.")
        except Group.DoesNotExist:
            print("Warning: 'group_a' does not exist. Please create it in the Django Admin.")