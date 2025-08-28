from django.shortcuts import render
from django.http import HttpResponse
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_POST
from django.utils.decorators import method_decorator
from django.views import View
from django.conf import settings
from django.contrib.auth.models import User
from monitoring.utils import send_whatsapp_alert
import subprocess
from twilio.twiml.messaging_response import MessagingResponse


@method_decorator(csrf_exempt, name="dispatch")
class WhatsAppWebhookView(View):

    def post(self, request, *args, **kwargs):

        pending_users = {}  # key = from_number, value = username

        from_number = request.POST.get("From")
        body = request.POST.get("Body", "").strip().lower()

        reply = "🤖 Comando não reconhecido. Use: STATUS ou RESTART\nOu responda com:\n1️⃣ Status\n2️⃣ Reiniciar\n3️⃣ Parar\n4️⃣ Reboot servidor"

        if body in ["status", "1"]:
            result = subprocess.getoutput("systemctl status celery-worker --no-pager -l")
            reply = f"📊 Status do worker:\n{result[:500]}..."  # evita estourar limite de msg

        elif body in ["logs worker", "2"]:
            try:
                result = subprocess.getoutput("journalctl -u celery-worker --no-pager -n 50")
                reply = f"📜 Logs do worker:\n{result[:500]}..."
            except Exception as e:
                reply = f"❌ Erro ao obter logs do worker: {str(e)}"

        elif body in ["logs beat", "3"]:
            try:
                result = subprocess.getoutput("journalctl -u celery-beat --no-pager -n 50")
                reply = f"📜 Logs do beat:\n{result[:500]}..."
            except Exception as e:
                reply = f"❌ Erro ao obter logs do beat: {str(e)}"
            reply = f"📜 Logs do beat:\n{result[:500]}..."

        elif body in ["logs gunicorn", "4"]:
            try:
                result = subprocess.getoutput("journalctl -u gunicorn --no-pager -n 50")
                reply = f"📜 Logs do gunicorn:\n{result[:500]}..."
            except Exception as e:
                reply = f"❌ Erro ao obter logs do gunicorn: {str(e)}"

        elif body in ["logs nginx", "5"]:
            try:
                result = subprocess.getoutput("journalctl -u nginx --no-pager -n 50")
                reply = f"📜 Logs do nginx:\n{result[:500]}..."
            except Exception as e:
                reply = f"❌ Erro ao obter logs do nginx: {str(e)}"

        
        # Dicionário para armazenar username pendente por número do WhatsApp

        elif body.lower() in ["user", "6"]:
            reply = "📩 Para criar um usuário, envie assim:\nuser <username> <email_ou_blank> <senha>\nEx: user Marcos123 meuemail@exemplo.com MinhaSenha123"

        elif body.lower().startswith("user "):
            try:
                parts = body.split(" ", 4)  # ["user", "username", "email", "senha"]
                if len(parts) < 5:
                    reply = "❌ Formato inválido. Use: user <username> <email_ou_blank> <senha>"
                else:
                    username = parts[2].strip()
                    email_user = parts[3].strip() or ""
                    password = parts[4].strip()

                    if not User.objects.filter(username=username).exists():
                        User.objects.create_superuser(username=username, email=email_user, password=password)
                        reply = f"✅ Usuário criado com sucesso!\nUsername: {username}\nSenha: {password}"
                    else:
                        reply = f"⚠️ Usuário já existe: {username}"
            except Exception as e:
                reply = f"❌ Erro ao criar usuário: {str(e)}"
                




        elif body in ["restart", "9"]:
            subprocess.run(["sudo", "systemctl", "restart", "celery-worker"])
            reply = "♻️ Worker reiniciado com sucesso!"

        elif body in ["stop", "3"]:
            subprocess.run(["sudo", "systemctl", "stop", "celery-worker"])
            reply = "🛑 Worker parado!"

        elif body in ["reboot", "4"]:
            subprocess.run(["sudo", "reboot"])
            reply = "🔄 Servidor reiniciando..."

        

        



        # Twilio response
        twilio_resp = MessagingResponse()
        twilio_resp.message(reply)
        return HttpResponse(str(twilio_resp), content_type="application/xml")