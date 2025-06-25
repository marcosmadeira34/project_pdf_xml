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
import PyPDF2
import json
import uuid
from .models import ArquivoZip

logger = logging.getLogger(__name__)

@shared_task(bind=True)
def processar_pdfs(self, files_data):
    """Processa múltiplos PDFs, gera XMLs e salva o ZIP no banco de dados."""
    processor = DocumentAIProcessor()
    project_id = os.getenv("PROJECT_ID")
    location = os.getenv("LOCATION")
    processor_id = os.getenv("PROCESSOR_ID")

    logger.info(f"Iniciando processamento com project_id={project_id}, location={location}, processor_id={processor_id}")

    if not project_id or not location or not processor_id:
        raise ValueError("As variáveis de ambiente PROJECT_ID, LOCATION e PROCESSOR_ID devem estar definidas.")

    if not isinstance(files_data, dict):
        raise ValueError("files_data deve ser um dicionário com nomes de arquivos como chaves e bytes como valores.")

    processed_data = {}
    zip_buffer = io.BytesIO()

    with zipfile.ZipFile(zip_buffer, 'w', zipfile.ZIP_DEFLATED) as zipf:
        for file_name, file_content in files_data.items():
            try:
                base_name = os.path.splitext(file_name)[0]
                xml_file_name = f"{base_name}.xml"
                json_extraido = processor.processar_pdf(project_id, location, processor_id, file_content)

                if json_extraido:
                    try:
                        # Aqui você converte o JSON extraído em XML de verdade
                        xml_content = XMLGenerator.gerar_xml_abrasf(json_extraido)
                        zipf.writestr(xml_file_name, xml_content)
                        logger.info(f"XML gerado e adicionado ao ZIP para {file_name}.")
                    except Exception as e:
                        logger.error(f"Erro ao gerar XML para {file_name}: {e}", exc_info=True)
                        processed_data[file_name] = f"Erro ao gerar XML: {e}"
                        raise

                processed_data[file_name] = "Processado com sucesso"
            except Exception as e:
                logger.error(f"Erro ao processar o PDF {file_name}: {e}", exc_info=True)
                processed_data[file_name] = f"Erro no processamento: {str(e)}"
                raise  # re-lança para o Celery marcar como FAILED

    zip_buffer.seek(0)
    zip_bytes = zip_buffer.read()

    zip_model = ArquivoZip.objects.create(zip_bytes=zip_bytes)

    return {
        'zip_id': str(zip_model.id),
        'processed_files_summary': processed_data,
    }


@shared_task(bind=True)
def merge_pdfs_task(self, pdf_contents_base64: dict, output_filename: str):
    """
    Junta múltiplos PDFs cujos conteúdos são passados em base64.
    Retorna o PDF combinado em base64.
    """
    try:
        # Certifique-se de que PyPDF2 está importado se esta função for usada.
        # import PyPDF2
        pdf_merger = PyPDF2.PdfMerger()

        for file_name, base64_content in pdf_contents_base64.items():
            pdf_bytes = base64.b64decode(base64_content)
            pdf_file = io.BytesIO(pdf_bytes)
            pdf_merger.append(pdf_file)

        output_buffer = io.BytesIO()
        pdf_merger.write(output_buffer)
        output_buffer.seek(0)
        merged_pdf_bytes_base64 = base64.b64encode(output_buffer.read()).decode('utf-8')

        return {"merged_pdf_bytes": merged_pdf_bytes_base64, "filename": output_filename}
    except Exception as e:
        logger.error(f"Erro ao juntar PDFs: {e}", exc_info=True)
        raise



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