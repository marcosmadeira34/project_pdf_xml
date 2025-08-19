from django.urls import path
from monitoring.views import WhatsAppWebhookView

urlpatterns = [
    path("webhook/whatsapp/", WhatsAppWebhookView.as_view(), name="whatsapp-webhook"),
]
