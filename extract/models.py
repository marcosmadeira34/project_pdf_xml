from django.db import models

# Create your models here.


# extract/models.py
from django.db import models
import uuid

class ArquivoZip(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    arquivo = models.FileField(upload_to='zips/')
    criado_em = models.DateTimeField(auto_now_add=True)
