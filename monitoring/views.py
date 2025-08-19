from django.shortcuts import render
from django.http import HttpResponse
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_POST
from django.utils.decorators import method_decorator
from django.views import View
from django.conf import settings
from monitoring.utils import send_whatsapp_alert
import subprocess
from twilio.twiml.messaging_response import MessagingResponse


@method_decorator(csrf_exempt, name="dispatch")
class WhatsAppWebhookView(View):

    def post(self, request, *args, **kwargs):
        from_number = request.POST.get("From")
        body = request.POST.get("Body", "").strip().lower()

        reply = "🤖 Comando não reconhecido. Use: STATUS ou RESTART\nOu responda com:\n1️⃣ Status\n2️⃣ Reiniciar\n3️⃣ Parar\n4️⃣ Reboot servidor"

        if body in ["status", "1"]:
            result = subprocess.getoutput("systemctl status celery-worker --no-pager -l")
            reply = f"📊 Status do worker:\n{result[:500]}..."  # evita estourar limite de msg

        elif body in ["restart", "2"]:
            subprocess.run(["sudo", "systemctl", "restart", "celery-worker"])
            reply = "♻️ Worker reiniciado com sucesso!"

        elif body in ["stop", "3"]:
            subprocess.run(["sudo", "systemctl", "stop", "celery-worker"])
            reply = "🛑 Worker parado!"

        elif body in ["reboot", "4"]:
            subprocess.run(["sudo", "reboot"])
            reply = "🔄 Servidor reiniciando..."

        elif body in ["logs worker", "5"]:
            result = subprocess.getoutput("journalctl -u celery-worker -f --no-pager -l")
            reply = f"📜 Logs do worker:\n{result[:500]}..."

        elif body in ["logs beat", "6"]:
            result = subprocess.getoutput("journalctl -u celery-beat -f --no-pager -l")
            reply = f"📜 Logs do beat:\n{result[:500]}..."

        elif body in ["logs gunicorn", "7"]:
            result = subprocess.getoutput("journalctl -u gunicorn -f --no-pager -l")
            reply = f"📜 Logs do gunicorn:\n{result[:500]}..."

        elif body in ["logs nginx", "8"]:
            result = subprocess.getoutput("journalctl -u nginx -f --no-pager -l")
            reply = f"📜 Logs do nginx:\n{result[:500]}..."

        # Twilio response
        twilio_resp = MessagingResponse()
        twilio_resp.message(reply)
        return HttpResponse(str(twilio_resp), content_type="application/xml")