import os
import io
import zipfile
from celery import shared_task
from celery.exceptions import SoftTimeLimitExceeded
from django.core.files.base import ContentFile
from .services import DocumentAIProcessor
from .services import XMLGenerator
from django.core.files.storage import default_storage
import uuid

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
    zip_buffer = io.BytesIO()

    with zipfile.ZipFile(zip_buffer, "w", zipfile.ZIP_DEFLATED) as zip_file:
        for file_name, pdf_bytes in files_data.items():
            try:
                print(f"[INFO] Processando: {file_name}...")

                document_json = processor.processar_pdf(project_id, location, processor_id, pdf_bytes)

                if not document_json:
                    print(f"[ERRO] processar_pdf() falhou para {file_name}")
                    continue

                dados_extraidos = processor.mapear_campos(document_json)
                print(f"[DEBUG] Dados extraídos: {dados_extraidos}")

                if not dados_extraidos:
                    print(f"[ERRO] Nenhum dado extraído para {file_name}")
                    continue

                xml = XMLGenerator.gerar_xml_abrasf(dados_extraidos)

                if not xml:
                    print(f"[ERRO] XML não gerado para {file_name}")
                    continue

                xml_filename = os.path.splitext(file_name)[0] + ".xml"
                zip_file.writestr(xml_filename, xml)
                xml_files.append(xml_filename)  # Armazena o nome do arquivo gerado

                processed_files += 1
                self.update_state(state="PROGRESS", meta={"processed": processed_files, "total": total_files})

            except SoftTimeLimitExceeded:
                print(f"[ERRO] Timeout ao processar {file_name}")
                break
            except Exception as e:
                print(f"[ERRO] Exceção ao processar {file_name}: {e}")
                continue

    zip_buffer.seek(0)
    zip_filename = f"{uuid.uuid4().hex}.zip"  # Nome único para o arquivo ZIP
    zip_path = os.path.join("xml_processados", zip_filename)

    if xml_files:
        default_storage.save(zip_path, ContentFile(zip_buffer.getvalue()))
        print(f"[INFO] ZIP salvo em: {zip_path}")
        task_status = "SUCCESS"
    else:
        print("[ERRO] Nenhum XML gerado, abortando salvamento.")
        task_status = "FAILURE"

    # Retornar resultado final
    return {"status": task_status, "zip_path": zip_path if xml_files else None, "xml_files": xml_files}