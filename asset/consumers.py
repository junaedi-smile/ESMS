import json
from channels.generic.websocket import AsyncWebsocketConsumer

class StatusAssetConsumer(AsyncWebsocketConsumer):
    async def connect(self):
        # Mengambil parameter cn_sap dari URL WebSocket
        self.cn_sap = self.scope['url_route']['kwargs']['cn_sap']
        self.room_group_name = f'status_{self.cn_sap}'

        # Masuk ke room group khusus berdasarkan cn_sap unit tersebut
        await self.channel_layer.group_add(
            self.room_group_name,
            self.channel_name
        )
        await self.accept()

    async def disconnect(self, close_code):
        # Keluar dari room group saat koneksi terputus
        await self.channel_layer.group_discard(
            self.room_group_name,
            self.channel_name
        )

    # Menerima event broadcast dari fungsi view Django saat terjadi perubahan status
    async def send_status_update(self, event):
        status = event['status']
        status_text = event['status_text']
        badge_bg = event['badge_bg']
        badge_color = event['badge_color']

        # Mengirim data JSON ke sisi browser (JavaScript)
        await self.send(text_data=json.dumps({
            'status': status,
            'status_text': status_text,
            'badge_bg': badge_bg,
            'badge_color': badge_color
        }))