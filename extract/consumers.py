from channels.generic.websocket import AsyncWebsocketConsumer
import json

class NotificationConsumer(AsyncWebsocketConsumer):
    async def connect(self):
        # Permitir todos conectarem para teste
        await self.accept()
        print("✅ WebSocket conectado com sucesso (sem autenticação).")

    async def disconnect(self, close_code):
        print("⚠️ WebSocket desconectado.")

    async def notify(self, event):
        await self.send(text_data=json.dumps(event["message"]))