import os
import io
import zipfile
from celery import shared_task
from celery.exceptions import SoftTimeLimitExceeded
from django.core.files.base import ContentFile
from .services import DocumentAIProcessor
from .services import XMLGenerator
from django.core.files.storage import default_storage

@shared_task(bind=True)
def processar_pdfs(self, files_data):
    """Processa múltiplos PDFs, gera XMLs e cria um ZIP."""
    processor = DocumentAIProcessor()
    project_id = os.getenv("PROJECT_ID")
    location = os.getenv("LOCATION")
    processor_id = os.getenv("PROCESSOR_ID")

    total_files = len(files_data)
    processed_files = 0
    xml_files = []  # Lista para armazenar os nomes dos arquivos XML

    # Criar buffer para ZIP
    zip_buffer = io.BytesIO()

    with zipfile.ZipFile(zip_buffer, "w", zipfile.ZIP_DEFLATED) as zip_file:
        for file_name, pdf_bytes in files_data.items():
            try:
                print(f"Processando: {file_name}...")

                document_json = processor.processar_pdf(project_id, location, processor_id, pdf_bytes)
                dados_extraidos = processor.mapear_campos(document_json)
                xml = XMLGenerator.gerar_xml_abrasf(dados_extraidos)

                # Adicionar XML ao ZIP
                xml_filename = os.path.splitext(file_name)[0] + ".xml"
                zip_file.writestr(xml_filename, xml)
                xml_files.append(xml_filename)  # Armazena o nome do arquivo gerado

                processed_files += 1
                self.update_state(state="PROGRESS", meta={"processed": processed_files, "total": total_files})

            except SoftTimeLimitExceeded:
                print(f"Timeout ao processar {file_name}")
                break
            except Exception as e:
                print(f"Erro ao processar {file_name}: {e}")
                continue

    # Salvar o ZIP gerado
    zip_buffer.seek(0)
    zip_path = f"xml_processados/{os.urandom(8).hex()}.zip"
    default_storage.save(zip_path, ContentFile(zip_buffer.getvalue()))

    return {"zip_path": zip_path, "xml_files": xml_files}  # Retorna o caminho do ZIP e lista de XMLs gerados
