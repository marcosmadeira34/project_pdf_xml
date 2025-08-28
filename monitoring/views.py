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

        #############################################################################################
        
        elif body in ["logs worker", "2"]:
            try:
                result = subprocess.getoutput("journalctl -u celery-worker --no-pager -n 50")
                reply = f"📜 Logs do worker:\n{result[:500]}..."
            except Exception as e:
                reply = f"❌ Erro ao obter logs do worker: {str(e)}"

        #############################################################################################

        elif body in ["logs beat", "3"]:
            try:
                result = subprocess.getoutput("journalctl -u celery-beat --no-pager -n 50")
                reply = f"📜 Logs do beat:\n{result[:500]}..."
            except Exception as e:
                reply = f"❌ Erro ao obter logs do beat: {str(e)}"
            reply = f"📜 Logs do beat:\n{result[:500]}..."

        #############################################################################################

        elif body in ["logs gunicorn", "4"]:
            try:
                result = subprocess.getoutput("journalctl -u gunicorn --no-pager -n 50")
                reply = f"📜 Logs do gunicorn:\n{result[:500]}..."
            except Exception as e:
                reply = f"❌ Erro ao obter logs do gunicorn: {str(e)}"

        #############################################################################################

        elif body in ["logs nginx", "5"]:
            try:
                result = subprocess.getoutput("journalctl -u nginx --no-pager -n 50")
                reply = f"📜 Logs do nginx:\n{result[:500]}..."
            except Exception as e:
                reply = f"❌ Erro ao obter logs do nginx: {str(e)}"

        #############################################################################################

        elif body.lower() in ["user", "6"]:
            reply = "📩 Para criar um usuário, envie assim:\nuser <username> <email_ou_blank> <senha>\nEx: user Marcos123 meuemail@exemplo.com MinhaSenha123"

        elif body.lower().startswith("user "):
            try:
                parts = body.split(" ", 3)  # divide em ["user", "username", "email", "senha"]
                if len(parts) < 4:
                    reply = "❌ Formato inválido. Use: user <username> <email_ou_blank> <senha>"
                else:
                    username = parts[1].strip()
                    email_user = parts[2].strip() or ""
                    password = parts[3].strip()

                    if not User.objects.filter(username=username).exists():
                        # Cria o superuser
                        user = User.objects.create_superuser(username=username, email=email_user, password=password)
                        reply = (f"✅ Usuário criado com sucesso!\n"
                                f"ID: {user.id}\n"
                                f"Username: {username}\nSenha: {password}")

                        # --- Adiciona créditos ---
                        reply += f"\n💳 Adicionando 10 créditos de teste para o usuário {username}..."

                        # Cria a ordem de pagamento (substitua "1" pelo ID do produto/quantidade se necessário)
                        order_output = subprocess.getoutput(f"python manage.py create_payment_order {user.id} 1")
                        
                        # Extrai o ID da ordem do output, assumindo que o padrão é: "Ordem de pagamento criada com ID <id> para o usuário ..."
                        import re
                        match = re.search(r"ID ([\w-]+) para o usuário", order_output)
                        print(f"O match da ordem de pagamento é {match}")
                        if match:
                            order_id = match.group(1)
                            print(f"O ID da ordem de pagamento é {order_id}")
                            # Confirma o pagamento
                            confirm_output = subprocess.getoutput(f"python manage.py confirm_payment {order_id}")
                            print(f"O output da confirmação de pagamento é {confirm_output}")
                            # Extrai o saldo do output
                            match_saldo = re.search(r"Novo saldo: (\d+)", confirm_output)
                            print(f"O match do saldo é {match_saldo}")
                            saldo = match_saldo.group(1) if match_saldo else "desconhecido"
                            print(f"O saldo é {saldo}")
                            reply += f"\n✅ Pagamento confirmado! Novo saldo: {saldo} créditos."
                        else:
                            reply += "\n❌ Erro ao criar ordem de pagamento."

                    else:
                        existing_user = User.objects.get(username=username)
                        reply = f"⚠️ Usuário já existe: {username}\nID: {existing_user.id}"
            except Exception as e:
                reply = f"❌ Erro ao criar usuário: {str(e)}"
                
        #############################################################################################
        


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