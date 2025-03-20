import os
from celery import Celery

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "nfse_abrasf.settings")

app = Celery("nfse_abrasf")

# Pega a configuração do Django
app.config_from_object("django.conf:settings", namespace="CELERY")

# Descobre tasks automaticamente em apps instalados
app.autodiscover_tasks()