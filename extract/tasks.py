import os
import io
import zipfile
import base64
from celery import shared_task
from .services import DocumentAIProcessor
from .services import XMLGenerator, ExcelGenerator
from .models import ArquivoZip
import logging
import PyPDF2

logger = logging.getLogger(__name__)

@shared_task(bind=True)
def processar_pdfs(self, files_data):
    """
    Processa múltiplos PDFs e retorna XMLs gerados
    files_data: dict {nome_arquivo: bytes_content}
    """
    try:
        processor = DocumentAIProcessor()
        project_id = os.getenv("PROJECT_ID")
        location = os.getenv("LOCATION")
        processor_id = os.getenv("PROCESSOR_ID")

        total_files = len(files_data)
        processed_files = 0
        arquivos_resultado = {}  # Vai armazenar {nome_arquivo: xml_content_string}
        erros = []

        # Criar ZIP em memória para download
        zip_buffer = io.BytesIO()

        with zipfile.ZipFile(zip_buffer, "w", zipfile.ZIP_DEFLATED) as zip_file:
            for file_name, pdf_bytes in files_data.items():
                try:
                    logger.info(f"Processando arquivo: {file_name}")
                    
                    # Processa com DocumentAI
                    document_json = processor.processar_pdf(project_id, location, processor_id, pdf_bytes)
                    logger.info(f"Documento processado: {file_name}")

                    # Mapeia campos e converte para XML válido
                    dados_extraidos = processor.mapear_campos(document_json)
                    logger.info(f"Dados extraídos: {dados_extraidos}")

                    # Gera XML válido usando XMLGenerator
                    xml_str = XMLGenerator.gerar_xml_abrasf(dados_extraidos)
                    logger.info(f"XML gerado para {file_name}, tamanho: {len(xml_str)} chars")

                    # Verifica se o XML é válido (começa com <)
                    if not xml_str.strip().startswith('<'):
                        raise ValueError(f"XML inválido gerado para {file_name}: não começa com '<'")

                    # Armazena o XML como string
                    xml_filename = file_name.replace('.pdf', '.xml')
                    arquivos_resultado[file_name] = xml_str  # STRING do XML, não dict
                    
                    # Adiciona ao ZIP
                    zip_file.writestr(xml_filename, xml_str.encode('utf-8'))
                    
                    processed_files += 1
                    logger.info(f"Arquivo {file_name} processado com sucesso")

                except Exception as e:
                    error_msg = f"Erro ao processar {file_name}: {str(e)}"
                    logger.error(error_msg, exc_info=True)
                    erros.append(error_msg)
                    
                    # Adiciona XML de erro
                    error_xml = f'''<?xml version="1.0" encoding="UTF-8"?>
<Erro>
    <Arquivo>{file_name}</Arquivo>
    <Mensagem>{str(e)}</Mensagem>
</Erro>'''
                    arquivos_resultado[file_name] = error_xml
                    zip_file.writestr(file_name.replace('.pdf', '_ERROR.xml'), error_xml.encode('utf-8'))

        # Salva ZIP no banco de dados
        zip_buffer.seek(0)
        zip_bytes = zip_buffer.getvalue()
        
        # Nome do arquivo ZIP
        zip_filename = f"xmls_processados_{self.request.id}.zip"
        
        # Cria registro no banco
        arquivo_zip = ArquivoZip.objects.create(
            zip_bytes=zip_bytes,
            nome_arquivo=zip_filename  # Agora funciona com o novo campo
        )
        
        logger.info(f"ZIP salvo no banco com ID: {arquivo_zip.id}")
        logger.info(f"Nome do arquivo: {zip_filename}")
        logger.info(f"Arquivos processados: {list(arquivos_resultado.keys())}")

        # Retorna resultado estruturado
        return {
            'success': True,
            'arquivos_resultado': arquivos_resultado,  # Dict com XMLs como strings
            'zip_id': str(arquivo_zip.id),
            'processed_files': processed_files,
            'total_files': total_files,
            'erros': erros
        }

    except Exception as e:
        logger.error(f"Erro geral no processamento: {str(e)}", exc_info=True)
        return {
            'success': False,
            'error': str(e),
            'arquivos_resultado': {},
            'processed_files': 0,
            'total_files': len(files_data) if files_data else 0
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

            
            except Exception as e:
                print(f"Erro ao processar {file_name}: {e}")
                erros.append(file_name)
                continue
    zip_buffer.seek(0)  # Posiciona o ponteiro no início do buffer

    return {
        "zip_bytes": base64.b64encode(zip_buffer.getvalue()).decode(),  # Retorna os bytes como string Base64
        "erros": erros
    }