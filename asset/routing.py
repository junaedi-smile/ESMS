from django.urls import re_path
from . import consumers

websocket_urlpatterns = [
    # Menggunakan [\w-]+ agar karakter minus (-) seperti pada 'AC020-0001' bisa terbaca
    re_path(r'ws/status-asset/(?P<cn_sap>[\w-]+)/$', consumers.StatusAssetConsumer.as_asgi()),
]