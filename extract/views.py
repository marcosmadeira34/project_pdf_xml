# extract/views.py

import json
import logging
import os
import requests
import base64 # Importe base64 para lidar com o ZIP
import uuid  # Adicionar import do uuid
from celery.result import AsyncResult
from django.contrib import messages
from django.contrib.auth import authenticate, login as auth_login, logout as auth_logout
from django.http import HttpResponseRedirect, JsonResponse
from django.shortcuts import render, redirect
from django.views import View
from django.views.decorators.csrf import csrf_exempt
from django.utils.decorators import method_decorator
from django.http import FileResponse, Http404
from .models import ArquivoZip
from django.http import FileResponse, Http404
from io import BytesIO
from .models import ArquivoZip, UserCredits
# Importa as classes e funções do seu processador e tarefas Celery
# Certifique-se de que esses imports estão corretos para o seu projeto
from extract.services import DocumentAIProcessor
from extract.tasks import processar_pdfs, merge_pdfs_task  # Removido processar_pdf_com_ai

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
        #streamlit_app_url = "http://localhost:8501"
        if not streamlit_app_url:
            # Em um ambiente de produção, logue isso, mas evite expor detalhes sensíveis
            logger.error("STREAMLIT_APP_URL não configurada nas variáveis de ambiente.")
            return JsonResponse({"error": "Configuração de URL do Streamlit ausente."}, status=500)
        return HttpResponseRedirect(streamlit_app_url)

# --- View para Upload e Processamento de PDF (API) ---
@method_decorator(csrf_exempt, name='dispatch')
class UploadEProcessarPDFView(View):
    def post(self, request):
        try:
            # Debug log para verificar o usuário
            import logging
            logger = logging.getLogger(__name__)
            logger.info(f"UploadEProcessarPDFView - request.user: {request.user}")
            logger.info(f"UploadEProcessarPDFView - request.user.id: {getattr(request.user, 'id', 'No ID')}")
            logger.info(f"UploadEProcessarPDFView - is_authenticated: {request.user.is_authenticated}")
            
            # Verifica se o usuário está autenticado
            if not request.user.is_authenticated:
                return JsonResponse({
                    'error': 'Usuário não autenticado',
                    'message': 'Faça login para continuar'
                }, status=401)
            
            # Verifica se o usuário tem créditos suficientes ANTES de processar
            user_credits, created = UserCredits.objects.get_or_create(user=request.user)
            
            # Conta quantos arquivos serão processados
            files = request.FILES.getlist('files[]')
            required_credits = len(files)
            
            logger.info(f"Files received: {len(files)}")
            logger.info(f"Required credits: {required_credits}")
            logger.info(f"User credits: {user_credits.balance}")
            
            if not user_credits.has_credits(required_credits):
                return JsonResponse({
                    'error': 'Créditos insuficientes',
                    'message': f'Você precisa de {required_credits} crédito(s) para processar {len(files)} arquivo(s)',
                    'current_balance': user_credits.balance,
                    'required_credits': required_credits
                }, status=402)  # 402 Payment Required
            
            # CONSOME OS CRÉDITOS ANTES DE PROCESSAR
            success = user_credits.use_credits(
                required_credits, 
                f"Conversão de {required_credits} PDF(s)"
            )
            
            if not success:
                return JsonResponse({
                    'error': 'Erro ao consumir créditos',
                    'message': 'Houve um erro ao descontar os créditos'
                }, status=500)
            
            logger.info(f"Credits consumed successfully. New balance: {user_credits.balance}")
            
            # Agora processa os arquivos
            merge_id = uuid.uuid4()
            
            # Verifica se deve fazer merge
            merge_pdfs_param = request.POST.get('merge_pdfs', 'false').lower() == 'true'
            
            if merge_pdfs_param and len(files) > 1:
                # Para merge, prepara os dados no formato esperado
                files_dict = {}
                for file in files:
                    files_dict[file.name] = file.read()
                
                merge_task = merge_pdfs_task.delay(files_dict, str(merge_id))
                
                return JsonResponse({
                    'success': True,
                    'task_id': merge_task.id,
                    'merge_id': str(merge_id),
                    'message': f'Créditos consumidos: {required_credits}. Processamento iniciado!',
                    'files_count': len(files),
                    'credits_used': required_credits,
                    'remaining_credits': user_credits.balance
                })
            else:
                # Para processar individualmente, vamos criar uma única tarefa com todos os arquivos
                # A função processar_pdfs espera um dicionário {nome_arquivo: bytes}
                files_dict = {}
                for file in files:
                    files_dict[file.name] = file.read()
                
                logger.info(f"Files dictionary created with {len(files_dict)} files")
                
                # Chama a tarefa com o dicionário de arquivos
                task = processar_pdfs.delay(files_dict)
                
                return JsonResponse({
                    'success': True,
                    'task_id': task.id,  # Retorna um único task_id
                    'merge_id': str(merge_id),
                    'message': f'Créditos consumidos: {required_credits}. Processamento iniciado!',
                    'files_count': len(files),
                    'credits_used': required_credits,
                    'remaining_credits': user_credits.balance
                })
                
        except Exception as e:
            # Log detalhado do erro
            import logging
            logger = logging.getLogger(__name__)
            logger.error(f'Erro em UploadEProcessarPDFView: {str(e)}', exc_info=True)
            
            # Se houver erro APÓS consumir créditos, reembolsa
            try:
                if 'required_credits' in locals() and 'success' in locals() and success:
                    # Reembolsa os créditos
                    user_credits.add_credits(
                        required_credits,
                        f"Reembolso - Erro no processamento: {str(e)}"
                    )
                    logger.info(f"Credits refunded: {required_credits}")
            except Exception as refund_error:
                logger.error(f"Error during refund: {str(refund_error)}")
                pass  # Evita erro duplo
            
            return JsonResponse({
                'error': f'Erro no processamento: {str(e)}',
                'message': 'Créditos reembolsados devido ao erro'
            }, status=500)

# --- View para Verificar o Status da Tarefa Celery (API) ---
@method_decorator(csrf_exempt, name='dispatch')
class TaskStatusView(View):
    """
    Verifica o status de uma tarefa Celery e retorna o resultado se concluída.
    """

    def get(self, request, task_id):
        try:
            result = AsyncResult(task_id)
            response_data = {"state": result.status}

            if result.status == "SUCCESS":
                task_result = result.result
                logger.info(f"[Celery Status] Task result type: {type(task_result)}")
                logger.info(f"[Celery Status] Task result keys: {task_result.keys() if isinstance(task_result, dict) else 'Not a dict'}")
                
                # Estrutura esperada do result:
                # {
                #   'success': True,
                #   'arquivos_resultado': {'arquivo.pdf': 'xml_string'},
                #   'zip_id': 'uuid',
                #   'processed_files': 1,
                #   'total_files': 1
                # }
                
                if isinstance(task_result, dict) and task_result.get('success'):
                    response_data["meta"] = {
                        "arquivos_resultado": task_result.get('arquivos_resultado', {}),
                        "zip_id": task_result.get('zip_id'),
                        "processed_files": task_result.get('processed_files', 0),
                        "total_files": task_result.get('total_files', 0),
                        "erros": task_result.get('erros', [])
                    }
                else:
                    response_data["meta"] = {
                        "error": task_result.get('error', 'Erro desconhecido') if isinstance(task_result, dict) else str(task_result)
                    }
                    
                logger.info(f"[Celery Status] Response meta: {response_data['meta']}")

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
            zip_model = ArquivoZip.objects.get(id=task_id)

            if not zip_model.zip_bytes:
                raise Http404("Arquivo ZIP não disponível no banco de dados.")

            return FileResponse(
                BytesIO(zip_model.zip_bytes),
                content_type="application/zip",
                filename=f"{task_id}.zip",
                as_attachment=True,
            )
        except ArquivoZip.DoesNotExist:
            raise Http404("Arquivo ZIP não encontrado.")


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