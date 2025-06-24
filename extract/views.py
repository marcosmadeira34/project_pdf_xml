from django.shortcuts import render

# Create your views here.
from django.shortcuts import render, redirect
from django.http import JsonResponse, HttpResponse
from django.views import View
from extract.services import DocumentAIProcessor
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
import base64
from datetime import datetime
import logging
import requests
import json
from django.views.decorators.csrf import csrf_exempt
from django.http import HttpResponseRedirect

# Configuração do logger
logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)
handler = logging.StreamHandler()
formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
handler.setFormatter(formatter)
logger.addHandler(handler)


load_dotenv()
print("Variáveis de ambiente carregadas.")

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
            return redirect("streamlit-dashboard")  # Redireciona para a página de upload de PDF
        else:
            # Se falhar, retorna um erro
            messages.error(request, "Usuário ou senha inválidos.")
            return render(request, "login_page.html")


class LogoutView(View):
    """View para realizar o logout do usuário."""
    
    #@method_decorator(login_required)
    def get(self, request):
        """Realiza o logout e redireciona para a página de login."""
        from django.contrib.auth import logout
        logout(request)
        return redirect("login")
    

@method_decorator(csrf_exempt, name='dispatch')
class UploadEProcessarPDFView(View):
    """View para upload e processamento assíncrono de PDFs."""

    #@method_decorator(login_required)
    def get(self, request):
        """Renderiza o formulário de upload."""
        return render(request, "test_processar.html")

    #@method_decorator(login_required)
    def post(self, request):
        """Inicia o processamento dos PDFs via Celery e retorna o task_id."""
        files = request.FILES.getlist("files")

        if not files:
            return JsonResponse({"error": "Nenhum arquivo enviado"}, status=400)
        
        # 🚫 Validação de extensão dos arquivos
        for f in files:
            if not f.name.lower().endswith(".pdf"):
                return JsonResponse({"error": f"Arquivo '{f.name}' não é um PDF."}, status=400)

        # Converter os arquivos para um dicionário {nome: bytes}
        files_data = {pdf.name: pdf.read() for pdf in files}

        # Instanciar o processador
        processor = DocumentAIProcessor()

        # Definir limite de segurança para evitar sobrecarga
        max_lotes = 10  # Ajuste conforme necessário

        lotes = processor.dividir_em_lotes(files_data, tamanho_lote=20)

        if len(lotes) > max_lotes:
            return JsonResponse({"error": "Excesso de arquivos enviados. Tente novamente com menos arquivos."}, status=400)

        task_ids = []

        for lote in lotes:
            task = processar_pdfs.delay(lote)
            task_ids.append(task.id)

        return JsonResponse({"task_ids": task_ids, "message": "Processamento iniciado!"})
        

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


class TaskStatusView(View):
    """Retorna o status do processamento da task Celery e permite o download do ZIP."""

    def get(self, request, task_id):
        result = AsyncResult(task_id)

        if result.state == "PROGRESS":
            return JsonResponse({
                "status": "processing",
                "processed": result.info.get("processed", 0),
                "total": result.info.get("total", 1),
            })

        if result.state == "SUCCESS" and result.result:
            zip_bytes_base64 = result.result.get("zip_bytes", "")
            if not zip_bytes_base64:
                return JsonResponse({"status": "error", "message": "ZIP não encontrado."})

            return JsonResponse({
                "status": "completed",
                "zip_data": zip_bytes_base64,  # Envia os bytes do ZIP em Base64
                "xml_files": result.result.get("xml_files", [])
            })

        return JsonResponse({"status": result.state, "message": "Processamento em andamento ou erro."})
    

class DownloadZipView(View):
    """Recebe o ZIP Base64 da task e retorna como um arquivo para o usuário."""
    
    def get(self, request, task_id):
        result = AsyncResult(task_id)

        if result.state == "SUCCESS" and result.result:
            zip_bytes_base64 = result.result.get("zip_bytes", "")
            if not zip_bytes_base64:
                return HttpResponse("Erro: Arquivo ZIP não encontrado.", status=404)

            zip_bytes = base64.b64decode(zip_bytes_base64)  # Decodifica os bytes
            response = HttpResponse(zip_bytes, content_type="application/zip")
            now = datetime.now().strftime("%d_%m_%Y_%H_%M_%S")
            response["Content-Disposition"] = f'attachment; filename="nfse_convertido_{now}.zip"'
            return response

        return HttpResponse("A tarefa ainda está em processamento ou falhou.", status=400)


class StreamlitAppRedirectView(View):
    """
    Redireciona o usuário para o URL da aplicação Streamlit.
    """
    #@method_decorator(login_required) # Opcional: Se quiser que apenas usuários logados acessem essa rota
    def get(self, request):
        # Para desenvolvimento local, o Streamlit roda na porta 8501 por padrão.
        # Para produção no Heroku, usaremos uma variável de ambiente.
        # Configure esta variável no Heroku CLI:
        # heroku config:set STREAMLIT_APP_URL="https://your-streamlit-app-on-streamlit-cloud.streamlit.app" -a seu-app-django-heroku
        streamlit_url = os.getenv("STREAMLIT_APP_URL", "http://localhost:8501")

        if not streamlit_url:
            # Caso a variável de ambiente não esteja configurada em produção
            return JsonResponse({"error": "URL do Streamlit não configurada."}, status=500)

        return HttpResponseRedirect(streamlit_url)
    

# --- NOVA VIEW NO DJANGO PARA ENVIAR XML PARA A API EXTERNA ---
@method_decorator(csrf_exempt, name='dispatch') # Use isso com CAUTELA e apenas se entender os riscos de segurança!
class SendXMLToExternalAPIView(View):
    """
    Recebe um XML do frontend (Streamlit) e o envia para uma API externa.
    """
    #@method_decorator(login_required) # Mantenha a proteção de login se for para usuários autenticados
    def post(self, request):
        try:
            data = json.loads(request.body)
            xml_content = data.get("xml_content")
            file_name = data.get("file_name", "unknown_file")

            if not xml_content:
                return JsonResponse({"status": "error", "error": "Conteúdo XML ausente."}, status=400)

            # --- AQUI VOCÊ FARIA A CHAMADA PARA A SUA API EXTERNA ---
            # Exemplo de URL de API externa (substitua pela sua real)
            external_api_url = os.getenv("EXTERNAL_API_SEND_URL", "https://api.example.com/send_nfse")

            headers = {
                "Content-Type": "application/xml", # Ou 'application/json' se a API externa espera JSON
                # "Authorization": f"Bearer {os.getenv('EXTERNAL_API_TOKEN')}" # Se sua API externa exigir autenticação
            }

            logger.info(f"Enviando XML de {file_name} para API externa.")
            api_response = requests.post(external_api_url, data=xml_content.encode('utf-8'), headers=headers, timeout=30)
            api_response.raise_for_status() # Lança exceção para erros HTTP

            # Assumindo que a API externa retorna um JSON com um UUID ou status
            external_api_data = api_response.json()
            uuid_retornado = external_api_data.get("uuid", "N/A")

            logger.info(f"XML de {file_name} enviado com sucesso. UUID: {uuid_retornado}")
            return JsonResponse({"status": "success", "uuid": uuid_retornado, "message": "XML enviado com sucesso!"})

        except json.JSONDecodeError:
            return JsonResponse({"status": "error", "error": "Requisição JSON inválida."}, status=400)
        except requests.exceptions.RequestException as e:
            error_message = f"Erro ao comunicar com API externa: {str(e)}"
            if e.response is not None:
                error_message += f" - Detalhes: {e.response.text}"
            logger.error(error_message, exc_info=True)
            return JsonResponse({"status": "error", "error": error_message}, status=500)
        except Exception as e:
            logger.error(f"Erro inesperado no envio de XML: {e}", exc_info=True)
            return JsonResponse({"status": "error", "error": f"Erro interno do servidor: {str(e)}"}, status=500)

