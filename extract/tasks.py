import os
import io
import zipfile
from celery import shared_task
from django.core.files.base import ContentFile
from .document_ai_processor import DocumentAIProcessor
from .xml_generator import XMLGenerator
from django.core.files.storage import default_storage

@shared_task
def processar_pdfs(files_data):
    """Processa múltiplos PDFs e gera um ZIP com os XMLs."""
    processor = DocumentAIProcessor()
    project_id = os.getenv("PROJECT_ID")
    location = os.getenv("LOCATION")
    processor_id = os.getenv("PROCESSOR_ID")

    # Criar buffer para ZIP
    zip_buffer = io.BytesIO()
    
    with zipfile.ZipFile(zip_buffer, "w", zipfile.ZIP_DEFLATED) as zip_file:
        for file_name, pdf_bytes in files_data.items():
            try:
                print(f"Processando: {file_name}...")
                document_json = processor.processar_pdf(project_id, location, processor_id, pdf_bytes)
                
                # Mapeia os campos do JSON e gera XML
                dados_extraidos = processor.mapear_campos(document_json)
                xml = XMLGenerator.gerar_xml_abrasf(dados_extraidos)

                # Adicionar ao ZIP
                xml_filename = os.path.splitext(file_name)[0] + ".xml"
                zip_file.writestr(xml_filename, xml)

            except Exception as e:
                print(f"Erro ao processar {file_name}: {e}")
                continue

    # Salvar o ZIP gerado
    zip_buffer.seek(0)
    zip_path = f"xml_processados/{os.urandom(8).hex()}.zip"
    default_storage.save(zip_path, ContentFile(zip_buffer.getvalue()))

    return zip_path  # Retorna o caminho do arquivo ZIP
