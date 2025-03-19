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


load_dotenv()
print("Variáveis de ambiente carregadas.")

class UploadEProcessarPDFView(View):
    """View para processar um PDF e gerar um XML."""

    @method_decorator(login_required)
    def get(self, request):
        """Exibe o formulário de upload."""
        return render(request, "test_processar.html")
    

    @method_decorator(login_required)
    def post(self, request):
        """Processa múltiplos PDFs e retorna um ZIP com os XMLs."""
        files = request.FILES.getlist("files")  # Obtém todos os arquivos enviados

        if not files:
            return JsonResponse({"error": "Nenhum arquivo enviado"}, status=400)

        processor = DocumentAIProcessor()
        project_id = os.getenv("PROJECT_ID")
        location = os.getenv("LOCATION")
        processor_id = os.getenv("PROCESSOR_ID")

        # Criar um buffer de memória para armazenar o ZIP
        zip_buffer = io.BytesIO()

        with zipfile.ZipFile(zip_buffer, "w", zipfile.ZIP_DEFLATED) as zip_file:
            for pdf_file in files:
                try:
                    print(f"Processando: {pdf_file.name}...")
                    pdf_data = pdf_file.read()
                    document_json = processor.processar_pdf(project_id, location, processor_id, pdf_data)
                    
                    # Extrai os dados do JSON retornado pelo Document AI
                    dados_extraidos = processor.mapear_campos(document_json)
                    xml = XMLGenerator.gerar_xml_abrasf(dados_extraidos)

                    # Adicionar ao ZIP com o nome do arquivo original convertido para .xml
                    xml_filename = os.path.splitext(pdf_file.name)[0] + ".xml"
                    zip_file.writestr(xml_filename, xml)

                except Exception as e:
                    print(f"Erro ao processar {pdf_file.name}: {e}")
                    return JsonResponse({"error": f"Erro ao processar {pdf_file.name}: {str(e)}"}, status=500)

        # Preparar o ZIP para download
        zip_buffer.seek(0)
        response = HttpResponse(zip_buffer.read(), content_type="application/zip")
        response["Content-Disposition"] = 'attachment; filename="xml_convertidos.zip"'

        return response
        
   


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