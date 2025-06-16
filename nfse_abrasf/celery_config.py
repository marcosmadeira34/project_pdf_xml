import os
from celery import Celery
import ssl

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "nfse_abrasf.settings")

app = Celery("nfse_abrasf")

# Pega a configuração do Django
app.config_from_object("django.conf:settings", namespace="CELERY")

# Configurar o broker
app.conf.broker_url = os.getenv('REDIS_TLS_URL', os.getenv('REDIS_URL', 'redis://localhost:6379/0'))

# Configurar SSL se necessário
app.conf.broker_use_ssl = {
    'ssl_cert_reqs': ssl.CERT_NONE
}


# Descobre tasks automaticamente em apps instalados
app.autodiscover_tasks()