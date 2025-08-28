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
            # pede para o usuário enviar o nome desejado
            reply = "📩 Envie o nome que deseja usar para o usuário. Ex: 'user username'"

        elif body.lower().startswith("user "):
            try:
                username = body[5:].strip()
                if not username:
                    reply = "❌ Nenhum username enviado. Primeiro: 'user <username>'"
                else:
                    # armazena temporariamente o username
                    pending_users[from_number] = {"username": username, "email": "", "password": ""}
                    reply = "📩 Agora envie o email do usuário (ou deixe em branco). Ex: 'email seu_email@example.com'"
            except Exception as e:
                reply = f"❌ Erro ao processar username: {str(e)}"

        elif body.lower().startswith("email "):
            try:
                email_user = body[6:].strip()
                if from_number not in pending_users:
                    reply = "❌ Nenhum username registrado. Primeiro envie: 'user <username>'"
                else:
                    pending_users[from_number]["email"] = email_user
                    reply = "📩 Agora envie a senha do usuário. Ex: 'psw sua_senha'"
            except Exception as e:
                reply = f"❌ Erro ao processar email: {str(e)}"

        elif body.lower().startswith("psw "):
            try:
                password = body[4:].strip()
                if from_number not in pending_users:
                    reply = "❌ Nenhum username registrado. Primeiro envie: 'user <username>'"
                elif not password:
                    reply = "❌ Senha inválida. Por favor, envie novamente."
                else:
                    pending_users[from_number]["password"] = password
                    user_data = pending_users[from_number]
                    username = user_data["username"]
                    email_user = user_data["email"]

                    if not User.objects.filter(username=username).exists():
                        # cria o usuário ignorando validação de senha curta ou parecida com username
                        User.objects.create_superuser(username=username, email=email_user, password=password)
                        reply = f"✅ Usuário criado com sucesso!\nUsername: {username}\nSenha: {password}"
                    else:
                        reply = f"⚠️ Usuário já existe: {username}"

                    # remove do pending_users após criação
                    pending_users.pop(from_number, None)
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