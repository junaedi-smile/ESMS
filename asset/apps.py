# asset/apps.py

from django.apps import AppConfig


class AssetConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'asset'
    verbose_name = 'ACTIVITY'

    def ready(self):
        # PASTIKAN BARIS INI ADA DAN TIDAK DIKOMENTARI
        import asset.signals
        print("Asset signals loaded!") # Tambahkan ini untuk verifikasi awal

