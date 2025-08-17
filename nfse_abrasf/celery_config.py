# nfse_abrasf/celery_config.py
import os
from celery import Celery
import ssl

from celery.schedules import crontab

import logging

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "nfse_abrasf.settings")

app = Celery("nfse_abrasf")
app.config_from_object("django.conf:settings", namespace="CELERY")

app.conf.update(
    timezone="UTC",
    enable_utc=True,
)


redis_url = os.getenv('REDIS_TLS_URL', os.getenv('REDIS_URL', 'redis://localhost:6379/0'))
app.conf.broker_url = redis_url
app.conf.result_backend = redis_url

app.conf.broker_transport_options = {
    "visibility_timeout": 3600,
    "socket_keepalive": True,
    "retry_on_timeout": True,
    "socket_connect_timeout": 30,   # tenta reconectar mais rápido
    "socket_timeout": 30,           # evita ficar preso indefinidamente
}
app.conf.broker_connection_retry_on_startup = True
app.conf.broker_heartbeat = 30  # envia sinal a cada 30s para manter conexão viva

# Descobre tasks automaticamente em apps instalados
app.autodiscover_tasks()

app.conf.beat_schedule = {
    "heartbeat-task-every-minute": {
        "task": "extract.tasks.heartbeat_task",
        "schedule": crontab(minute="*"),  # todo minuto
    },
}

if redis_url.startswith("rediss://"):
    ssl_options = {"ssl_cert_reqs": ssl.CERT_NONE}
    app.conf.broker_use_ssl = ssl_options
    app.conf.redis_backend_use_ssl = ssl_options  # <- isso é necessário!



# # Pega a configuração do Django
# app.config_from_object("django.conf:settings", namespace="CELERY")

# # Configurar o broker
# app.conf.broker_url = os.getenv('REDIS_TLS_URL', os.getenv('REDIS_URL', 'redis://localhost:6379/0'))

# # Configurar SSL se necessário
# app.conf.broker_use_ssl = {
#     'ssl_cert_reqs': ssl.CERT_NONE
# }


