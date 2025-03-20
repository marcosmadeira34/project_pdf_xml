from django.shortcuts import render

# Create your views here.
from django.shortcuts import render, redirect
from django.http import JsonResponse, HttpResponse
from django.views import View
from .services import DocumentAIProcessor, XMLGenerator
from django.contrib.auth import authenticate, login as auth_login
from django.contrib.auth.decorators import login_required
from django.utils.decorators import method_decorator
from django.contrib import messages
from dotenv import load_dotenv
import os
import zipfile
import io
from PyPDF2 import PdfMerger
from django.views.decorators.csrf import csrf_exempt
from django.http import JsonResponse
from django.core.files.storage import default_storage
from celery.result import AsyncResult
from .tasks import processar_pdfs

load_dotenv()
print("Variáveis de ambiente carregadas.")

class UploadEProcessarPDFView(View):
    """View para upload e processamento assíncrono de PDFs."""

    @method_decorator(login_required)
    def get(self, request):
        """Renderiza o formulário de upload."""
        return render(request, "test_processar.html")

    @method_decorator(login_required)
    def post(self, request):
        """Inicia o processamento dos PDFs via Celery e retorna o task_id."""
        files = request.FILES.getlist("files")

        if not files:
            return JsonResponse({"error": "Nenhum arquivo enviado"}, status=400)

        # Converter os arquivos para um dicionário {nome: bytes}
        files_data = {pdf.name: pdf.read() for pdf in files}

        # Instanciar o processador
        processor = DocumentAIProcessor()

        # Dividir os envios de pdf em lotes de 20 para evitar erros de limite de memório
        lotes = processor.dividir_em_lotes(files_data, 20)

        task_ids = []

        for lote in lotes:
            # Enviar para processamento assíncrono
            task = processar_pdfs.delay(lote)
            task_ids.append(task.id)

        return JsonResponse({"task_id": task.id, "message": "Processamento iniciado!"})

class TaskStatusView(View):
    """Verifica o status de uma task do Celery."""

    def get(self, request, task_id):
        result = AsyncResult(task_id)
        if result.state == "SUCCESS":
            zip_url = default_storage.url(result.result)  # URL do ZIP gerado
            return JsonResponse({"status": "completed", "zip_url": zip_url})
        return JsonResponse({"status": result.state})
        
   


class MergePDFsView(View):
    """View para mesclar múltiplos PDFs em um único arquivo."""
    @method_decorator(csrf_exempt)
    def post(self, request):
        if request.method == "POST" and request.FILES.getlist("files"):
            pdf_merge = PdfMerger()

            for file in request.FILES.getlist("files"):
                pdf_merge.append(file)
            
            merge_pdf = io.BytesIO()
            pdf_merge.write(merge_pdf)
            pdf_merge.close()
            merge_pdf.seek(0)

            response = HttpResponse(merge_pdf.read(), 
                                    content_type="application/pdf")
            response["Content-Disposition"] = 'inline; filename="merged_pdf.pdf"'
            return response


class LoginView(View):
    """View para exibir o formulário de login."""

    def get(self, request):
        return render(request, "login_page.html")
    

    def post(self, request):
        username = request.POST.get("username")
        password = request.POST.get("password")

        # Autentica o usuário
        user = authenticate(request, username=username, password=password)
        if user is not None:
            # Se o login for bem-sucedido, realiza o login e redireciona para a página de upload
            auth_login(request, user)
            return redirect("upload-e-processar-pdf")  # Redireciona para a página de upload de PDF
        else:
            # Se falhar, retorna um erro
            messages.error(request, "Usuário ou senha inválidos.")
            return render(request, "login_page.html")