import subprocess
from django.core.management.base import BaseCommand
from monitoring.utils import send_whatsapp_alert
import os
import json

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
STATE_FILE = os.path.join(BASE_DIR, "celery_status.json")

class Command(BaseCommand):
    help = "Verifica se o worker Celery está rodando e envia alerta via WhatsApp apenas se houver mudança de status"

    def load_last_status(self):
        if os.path.exists(STATE_FILE):
            with open(STATE_FILE, "r") as f:
                data = json.load(f)
                return data.get("status", True)  # assume ativo se não existir
        return True

    def save_status(self, status: bool):
        with open(STATE_FILE, "w") as f:
            json.dump({"status": status}, f)

    def handle(self, *args, **kwargs):
        last_status = self.load_last_status()
        try:
            status = subprocess.run(
                ["systemctl", "is-active", "--quiet", "celery-worker"],
                check=False
            )
            current_status = status.returncode == 0

            # Só envia alerta se o status mudou
            if current_status != last_status:
                if not current_status:
                    send_whatsapp_alert("⚠️ O worker Celery caiu no servidor EC2!")
                    self.stdout.write(self.style.ERROR("Worker Celery caiu! Alerta enviado."))
                else:
                    send_whatsapp_alert("✅ Worker Celery reiniciado com sucesso!")
                    self.stdout.write(self.style.SUCCESS("Worker Celery reiniciado! Alerta enviado."))

            else:
                # Apenas log no console, sem enviar alerta
                if current_status:
                    self.stdout.write(self.style.SUCCESS("Worker Celery rodando normalmente."))
                else:
                    self.stdout.write(self.style.WARNING("Worker Celery continua parado."))

            # Salva o estado atual
            self.save_status(current_status)

        except Exception as e:
            send_whatsapp_alert(f"❌ Erro ao verificar worker: {str(e)}")
            self.stdout.write(self.style.ERROR(f"Erro: {str(e)}"))
