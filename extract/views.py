# extract/views.py

import json
import logging
import os
import requests
import base64 # Importe base64 para lidar com o ZIP
from celery.result import AsyncResult
from django.contrib import messages
from django.contrib.auth import authenticate, login as auth_login, logout as auth_logout
from django.http import HttpResponseRedirect, JsonResponse
from django.shortcuts import render, redirect
from django.views import View
from django.views.decorators.csrf import csrf_exempt
from django.utils.decorators import method_decorator

# Importa as classes e funções do seu processador e tarefas Celery
# Certifique-se de que esses imports estão corretos para o seu projeto
from extract.services import DocumentAIProcessor
from extract.tasks import processar_pdfs, merge_pdfs_task

logger = logging.getLogger(__name__)

# --- View de Login ---
class LoginView(View):
    """View para exibir o formulário de login."""

    def get(self, request):
        return render(request, "login_page.html")

    def post(self, request):
        username = request.POST.get("username")
        password = request.POST.get("password")

        user = authenticate(request, username=username, password=password)
        if user is not None:
            auth_login(request, user)
            # Redireciona para a URL que leva ao Streamlit
            return redirect("streamlit-dashboard")
        else:
            messages.error(request, "Usuário ou senha inválidos.")
            return render(request, "login_page.html")

# --- View de Logout ---
class LogoutView(View):
    """View para realizar o logout do usuário."""

    def get(self, request):
        auth_logout(request)
        messages.info(request, "Você foi desconectado com sucesso.")
        return redirect("login")

# --- View para Redirecionar para o Streamlit ---
class StreamlitAppRedirectView(View):
    """Redireciona o usuário para o URL da aplicação Streamlit."""

    def get(self, request):
        streamlit_app_url = os.getenv("STREAMLIT_APP_URL", "http://127.0.0.1:8501")
        if not streamlit_app_url:
            # Em um ambiente de produção, logue isso, mas evite expor detalhes sensíveis
            logger.error("STREAMLIT_APP_URL não configurada nas variáveis de ambiente.")
            return JsonResponse({"error": "Configuração de URL do Streamlit ausente."}, status=500)
        return HttpResponseRedirect(streamlit_app_url)

# --- View para Upload e Processamento de PDF (API) ---
@method_decorator(csrf_exempt, name='dispatch')
class UploadEProcessarPDFView(View):
    """Recebe PDFs do frontend, inicia o processamento assíncrono via Celery."""

    def post(self, request):
        files = request.FILES.getlist("files")

        if not files:
            return JsonResponse({"error": "Nenhum arquivo enviado"}, status=400)

        files_data = {pdf.name: pdf.read() for pdf in files}

        try:
            processor = DocumentAIProcessor()
            max_lotes = 10
            lotes = processor.dividir_em_lotes(files_data, tamanho_lote=20)

            if len(lotes) > max_lotes:
                return JsonResponse({"error": "Excesso de arquivos enviados. Tente novamente com menos arquivos."}, status=400)

            task_ids = []
            for lote in lotes:
                task = processar_pdfs.delay(lote) # Inicia a tarefa Celery
                task_ids.append(task.id)
                print(f"O retorno da tarefa é: {task.id}")
            
            return JsonResponse({"task_ids": task_ids, "message": "Processamento iniciado!"})
        except Exception as e:
            logger.error(f"Erro ao iniciar o processamento de PDF: {e}", exc_info=True)
            return JsonResponse({"error": f"Erro interno ao iniciar o processamento: {str(e)}"}, status=500)

# --- View para Verificar o Status da Tarefa Celery (API) ---
@method_decorator(csrf_exempt, name='dispatch')
class TaskStatusView(View):
    """
    Verifica o status de uma tarefa Celery e retorna o resultado se concluída.
    Se a tarefa for bem-sucedida, retorna os XMLs extraídos (em base64) e o ZIP.
    """

    def get(self, request, task_id):
        try:
            result = AsyncResult(task_id)
            response_data = {"state": result.status}


            if result.status == "SUCCESS":
                response_data["meta"] = result.result

            elif result.status == "FAILURE":
                response_data["meta"] = {"error": str(result.result)}
            else:
                response_data["meta"] = {}

            return JsonResponse(response_data)
        except Exception as e:
            logger.error(f"Erro ao verificar status da tarefa {task_id}: {e}", exc_info=True)
            return JsonResponse({"error": f"Erro interno ao verificar status da tarefa: {str(e)}"}, status=500)
        


# --- View para Download de ZIP (API - mantida, mas não usada no fluxo principal agora) ---
@method_decorator(csrf_exempt, name='dispatch')
class DownloadZipView(View):
    def get(self, request, task_id):
        try:
            task = AsyncResult(task_id)
            if task.successful():
                result = task.result
                zip_filename = result.get('zip_file_name')
                if not zip_filename:
                    return JsonResponse({"error": "ZIP não encontrado no resultado."}, status=404)

                zip_path = f"/tmp/{zip_filename}"
                if not os.path.exists(zip_path):
                    raise Http404("Arquivo ZIP não encontrado no servidor.")

                return FileResponse(
                    open(zip_path, 'rb'),
                    as_attachment=True,
                    filename=zip_filename
                )
            else:
                return JsonResponse({"error": "Tarefa ainda não finalizada ou falhou."}, status=400)
        except Exception as e:
            logger.error(f"Erro ao tentar baixar ZIP: {e}", exc_info=True)
            return JsonResponse({"error": "Erro ao processar download."}, status=500)


# --- View para Juntar PDFs (API) ---
@method_decorator(csrf_exempt, name='dispatch')
class MergePDFsView(View):
    """Inicia uma tarefa Celery para juntar múltiplos PDFs."""

    def post(self, request):
        try:
            data = json.loads(request.body)
            pdf_contents_base64 = data.get("pdf_contents_base64")
            output_filename = data.get("output_filename", "merged_document.pdf")

            if not pdf_contents_base64:
                return JsonResponse({"error": "Nenhum conteúdo PDF fornecido para merge."}, status=400)

            # Inicia a tarefa assíncrona para merge
            task = merge_pdfs_task.delay(pdf_contents_base64, output_filename)
            return JsonResponse({"task_id": task.id, "message": "Merge iniciado!"})

        except json.JSONDecodeError:
            return JsonResponse({"error": "Requisição JSON inválida."}, status=400)
        except Exception as e:
            logger.error(f"Erro ao iniciar merge de PDFs: {e}", exc_info=True)
            return JsonResponse({"error": f"Erro interno do servidor: {str(e)}"}, status=500)


# --- View para Enviar XML para API Externa (API) ---
@method_decorator(csrf_exempt, name='dispatch')
class SendXMLToExternalAPIView(View):
    """Recebe um XML do frontend (Streamlit) e o envia para uma API externa."""

    def post(self, request):
        try:
            data = json.loads(request.body)
            xml_content = data.get("xml_content")
            file_name = data.get("file_name", "unknown_file")

            if not xml_content:
                return JsonResponse({"status": "error", "error": "Conteúdo XML ausente."}, status=400)

            external_api_url = os.getenv("EXTERNAL_API_SEND_URL", "https://api.example.com/send_nfse")

            if not external_api_url:
                logger.error("EXTERNAL_API_SEND_URL não configurada nas variáveis de ambiente.")
                return JsonResponse({"status": "error", "error": "URL da API externa não configurada."}, status=500)

            headers = {
                "Content-Type": "application/xml",
            }

            logger.info(f"Enviando XML de {file_name} para API externa em {external_api_url}.")
            api_response = requests.post(external_api_url, data=xml_content.encode('utf-8'), headers=headers, timeout=30)
            api_response.raise_for_status() # Lança HTTPError para status de erro (4xx ou 5xx)

            # Tenta ler a resposta como JSON
            try:
                external_api_data = api_response.json()
            except json.JSONDecodeError:
                logger.warning(f"Resposta da API externa não é JSON: {api_response.text}")
                # Se a API externa não retorna JSON, pode ser um sucesso HTTP 2xx sem corpo.
                if 200 <= api_response.status_code < 300:
                    return JsonResponse({"status": "success", "message": f"XML enviado com sucesso! API retornou status {api_response.status_code}."})
                else:
                    return JsonResponse({"status": "error", "error": f"API externa retornou status {api_response.status_code} e resposta não-JSON: {api_response.text}"}, status=500)

            uuid_retornado = external_api_data.get("uuid", "N/A")

            logger.info(f"XML de {file_name} enviado com sucesso. UUID: {uuid_retornado}")
            return JsonResponse({"status": "success", "uuid": uuid_retornado, "message": "XML enviado com sucesso!"})

        except json.JSONDecodeError:
            logger.error("Requisição JSON inválida recebida na SendXMLToExternalAPIView.", exc_info=True)
            return JsonResponse({"status": "error", "error": "Requisição JSON inválida."}, status=400)
        except requests.exceptions.RequestException as e:
            error_message = f"Erro ao comunicar com API externa: {str(e)}"
            if e.response is not None:
                try:
                    error_data = e.response.json()
                    error_message += f" - Detalhes da API: {error_data}"
                except json.JSONDecodeError:
                    error_message += f" - Detalhes da API (texto): {e.response.text}"
            logger.error(error_message, exc_info=True)
            return JsonResponse({"status": "error", "error": error_message}, status=500)
        except Exception as e:
            logger.error(f"Erro inesperado no envio de XML para API externa: {e}", exc_info=True)
            return JsonResponse({"status": "error", "error": f"Erro interno do servidor: {str(e)}"}, status=500)