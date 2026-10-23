# data/signals.py

from django.db.models.signals import post_save, post_delete
from django.dispatch import receiver
from django.db.models import Sum
from .models import AR01
from asset.models import AssetEquipmentDisposed

# =========================================================================
# Sinyal untuk POST_SAVE (Dibuat & Diperbarui)
# =========================================================================
@receiver(post_save, sender=AR01)
def update_disposed_asset_nbv(sender, instance, **kwargs):
    """
    Fungsi ini dipanggil setelah objek AR01 disimpan.
    Ia akan menghitung total book_value untuk semua AR01 dengan type_name yang sama
    dan memperbarui kolom 'nbv_disposed' pada model AssetEquipmentDisposed yang sesuai.
    """
    try:
        # 1. Cari semua objek AR01 yang memiliki 'type_name' yang sama dengan instance ini.
        #    Kita menggunakan .filter() karena mungkin ada lebih dari satu.
        related_ar01_items = AR01.objects.filter(type_name=instance.type_name)

        # 2. Hitung total 'book_value' dari semua objek yang ditemukan.
        #    'aggregate' dengan 'Sum' akan menjumlahkan nilai.
        total_nbv = related_ar01_items.aggregate(total_sum=Sum('book_value'))['total_sum']

        # 3. Cari objek AssetEquipmentDisposed yang akan diperbarui.
        #    Pastikan hanya satu objek yang ditemukan.
        target_asset = AssetEquipmentDisposed.objects.get(CN_SAP=instance.type_name)

        # 4. Perbarui nilai 'nbv_disposed' dengan hasil penjumlahan.
        #    Jika total_nbv adalah None (misalnya jika tidak ada item), kita atur ke None.
        target_asset.nbv_disposed = total_nbv or None

        # 5. Simpan perubahan pada AssetEquipmentDisposed.
        target_asset.save()
        print(f"Signal (post_save): Berhasil memperbarui '{target_asset.CN_SAP}' dengan total NBV: {target_asset.nbv_disposed}.")
        
    except AssetEquipmentDisposed.DoesNotExist:
        print(f"Signal (post_save): Tidak ada AssetEquipmentDisposed yang cocok untuk '{instance.type_name}'.")
    except AssetEquipmentDisposed.MultipleObjectsReturned:
        print(f"Signal (post_save): Peringatan - Ditemukan duplikat untuk '{instance.type_name}'. Tidak ada yang diperbarui.")

# =========================================================================
# Sinyal untuk POST_DELETE (Dihapus)
# =========================================================================
@receiver(post_delete, sender=AR01)
def clear_or_update_disposed_asset_nbv(sender, instance, **kwargs):
    """
    Fungsi ini dipanggil setelah objek AR01 dihapus.
    Ia akan menghitung ulang total book_value dari item yang tersisa
    dan memperbarui atau mengosongkan kolom 'nbv_disposed' pada model AssetEquipmentDisposed.
    """
    try:
        # 1. Cari semua objek AR01 yang tersisa dengan 'type_name' yang sama.
        #    Instance yang baru dihapus tidak akan ada dalam hasil filter ini.
        related_ar01_items = AR01.objects.filter(type_name=instance.type_name)

        # 2. Hitung total 'book_value' dari semua objek yang tersisa.
        #    Jika tidak ada yang tersisa, total_nbv akan menjadi None.
        total_nbv = related_ar01_items.aggregate(total_sum=Sum('book_value'))['total_sum']

        # 3. Cari objek AssetEquipmentDisposed yang akan diperbarui.
        target_asset = AssetEquipmentDisposed.objects.get(CN_SAP=instance.type_name)

        # 4. Perbarui nilai 'nbv_disposed' dengan total yang baru atau kosongkan jika tidak ada lagi.
        target_asset.nbv_disposed = total_nbv or None

        # 5. Simpan perubahan.
        target_asset.save()
        print(f"Signal (post_delete): Berhasil mengosongkan/memperbarui NBV untuk '{target_asset.CN_SAP}' menjadi: {target_asset.nbv_disposed}.")

    except AssetEquipmentDisposed.DoesNotExist:
        print(f"Signal (post_delete): Tidak ada AssetEquipmentDisposed yang cocok untuk '{instance.type_name}'.")
    except AssetEquipmentDisposed.MultipleObjectsReturned:
        print(f"Signal (post_delete): Peringatan - Ditemukan duplikat untuk '{instance.type_name}'. Tidak ada yang diperbarui.")


