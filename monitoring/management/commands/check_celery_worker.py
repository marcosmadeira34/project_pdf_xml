import subprocess
from django.core.management.base import BaseCommand
from monitoring.utils import send_whatsapp_alert

class Command(BaseCommand):
    help = "Verifica se o worker Celery está rodando e envia alerta via WhatsApp"

    def handle(self, *args, **kwargs):
        try:
            status = subprocess.run(
                ["systemctl", "is-active", "--quiet", "celery-worker"],
                check=False
            )

            if status.returncode != 0:
                send_whatsapp_alert("⚠️ O worker Celery caiu no servidor EC2!")
                self.stdout.write(self.style.ERROR("Worker Celery caiu! Alerta enviado."))
            else:
                self.stdout.write(self.style.SUCCESS("Worker Celery rodando normalmente."))

        except Exception as e:
            send_whatsapp_alert(f"❌ Erro ao verificar worker: {str(e)}")
            self.stdout.write(self.style.ERROR(f"Erro: {str(e)}"))
