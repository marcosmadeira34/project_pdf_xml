import os
import io
import zipfile
from celery import shared_task
from celery.exceptions import SoftTimeLimitExceeded
from django.core.files.base import ContentFile
from .services import DocumentAIProcessor
from .services import XMLGenerator, ExcelGenerator
from django.core.files.storage import default_storage
import base64
import logging

logger = logging.getLogger(__name__)

@shared_task(bind=True)
def processar_pdfs(self, files_data):
    """Processa múltiplos PDFs, gera XMLs e cria um ZIP."""
    processor = DocumentAIProcessor()
    project_id = os.getenv("PROJECT_ID")
    location = os.getenv("LOCATION")
    processor_id = os.getenv("PROCESSOR_ID")

    print(f"Iniciando processamento com project_id={project_id}, location={location}, processor_id={processor_id}")

    if not project_id or not location or not processor_id:
        raise ValueError("As variáveis de ambiente PROJECT_ID, LOCATION e PROCESSOR_ID devem estar definidas.")

    # Verifica se files_data é um dicionário
    if not isinstance(files_data, dict):
        raise ValueError("files_data deve ser um dicionário com nomes de arquivos como chaves e bytes como valores.")

    total_files = len(files_data)
    processed_files = 0
    erros = []  # Lista para armazenar arquivos que falharam

    # Criar buffer para ZIP
    zip_buffer = io.BytesIO()

    with zipfile.ZipFile(zip_buffer, "w", zipfile.ZIP_DEFLATED) as zip_file:
        for file_name, pdf_bytes in files_data.items():
            try:
                print(f"Processando: {file_name}...")

                self.update_state(state="PROGRESS", meta={"processed": processed_files, "total": total_files})

                document_json = processor.processar_pdf(project_id, location, processor_id, pdf_bytes)
                dados_extraidos = processor.mapear_campos(document_json)
                xml = XMLGenerator.gerar_xml_abrasf(dados_extraidos)

                # Adicionar XML ao ZIP
                xml_filename = os.path.splitext(file_name)[0] + ".xml"
                zip_file.writestr(xml_filename, xml)

                processed_files += 1

            except SoftTimeLimitExceeded:
                print(f"Timeout ao processar {file_name}")
                erros.append(file_name)
                break
            except Exception as e:
                print(f"Erro ao processar {file_name}: {e}")
                erros.append(file_name)
                continue

    zip_buffer.seek(0)  # Posiciona o ponteiro no início do buffer

    return {
        "zip_bytes": base64.b64encode(zip_buffer.getvalue()).decode(),  # Retorna os bytes como string Base64
        "erros": erros
    }



@shared_task(bind=True)
def gerar_excel(self, files_data):
    """Processa múltiplos PDFs, gera um único Excel e cria um ZIP."""
    processor = DocumentAIProcessor()
    project_id = os.getenv("PROJECT_ID")
    location = os.getenv("LOCATION")
    processor_id = os.getenv("PROCESSOR_ID")

    print(f"Iniciando processamento com project_id={project_id}, location={location}, processor_id={processor_id}")

    if not project_id or not location or not processor_id:
        raise ValueError("As variáveis de ambiente PROJECT_ID, LOCATION e PROCESSOR_ID devem estar definidas.")
    
    # Verifica se files_data é um dicionário
    if not isinstance(files_data, dict):
        raise ValueError("files_data deve ser um dicionário com nomes de arquivos como chaves e bytes como valores.")

    total_files = len(files_data)
    processed_files = 0
    erros = []  # Lista para armazenar arquivos que falharam

    # Criar buffer para ZIP
    zip_buffer = io.BytesIO()

    with zipfile.ZipFile(zip_buffer, "w", zipfile.ZIP_DEFLATED) as zip_file:
        for file_name, pdf_bytes in files_data.items():
            try:
                print(f"Processando: {file_name}...")

                self.update_state(state="PROGRESS", meta={"processed": processed_files, "total": total_files})
                
                document_json = processor.processar_pdf(project_id, location, processor_id, pdf_bytes)
                dados_extraidos = processor.mapear_campos(document_json)
                excel_bytes = ExcelGenerator.gerar_excel(dados_extraidos)
                
                # Adicionar Excel ao ZIP
                excel_filename = os.path.splitext(file_name)[0] + ".xlsx"
                zip_file.writestr(excel_filename, excel_bytes)  
                
                processed_files += 1

            except SoftTimeLimitExceeded:
                print(f"Timeout ao processar {file_name}")
                erros.append(file_name)
                break
            except Exception as e:
                print(f"Erro ao processar {file_name}: {e}")
                erros.append(file_name)
                continue
    zip_buffer.seek(0)  # Posiciona o ponteiro no início do buffer

    return {
        "zip_bytes": base64.b64encode(zip_buffer.getvalue()).decode(),  # Retorna os bytes como string Base64
        "erros": erros
    }