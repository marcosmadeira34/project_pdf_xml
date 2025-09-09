import os
import io
import zipfile
import base64
from celery import shared_task
from .services import DocumentAIProcessor
from .services import XMLGenerator, ExcelGenerator, EmailSender
from .models import ArquivoZip, TaskStatusModel
import logging
import PyPDF2
from extract.minio_service import download_file_from_minio
import json
from django.conf import settings
from datetime import datetime



logger = logging.getLogger(__name__)

def update_task_status(task_id, status, result=None):
    """
    Atualiza o status de uma tarefa no banco de dados.
    """
    try:
        task = TaskStatusModel.objects.get(task_id=task_id)
        task.status = status
        task.result = result
        task.save()
        logger.info(f"Tarefa {task_id} atualizada para status: {status}")

    except TaskStatusModel.DoesNotExist:
        logger.warning(f"TaskStatusModel não encontrado para task_id {task_id}")
    except Exception as e:
        logger.error(f"Erro ao atualizar status da tarefa {task_id}: {str(e)}", exc_info=True)




@shared_task(bind=True)
def merge_pdfs_task(self, temp_file_paths, output_filename):
    """
    Junta múltiplos PDFs cujos conteúdos são passados em base64.
    Retorna o PDF combinado em base64.
    """
    try:
        pdf_merger = PyPDF2.PdfMerger()
        
        # Lê arquivos um por um do disco
        for temp_path in temp_file_paths:
            with open(temp_path, 'rb') as pdf_file:
                pdf_merger.append(pdf_file)
        
        output_buffer = io.BytesIO()
        pdf_merger.write(output_buffer)
        output_buffer.seek(0)
        merged_pdf_bytes_base64 = base64.b64encode(output_buffer.read()).decode('utf-8')
        
        # Limpa arquivos temporários
        for temp_path in temp_file_paths:
            try:
                os.remove(temp_path)
            except:
                pass
        
        return {"merged_pdf_bytes": merged_pdf_bytes_base64, "filename": output_filename}
    
    except Exception as e:
        logger.error(f"Erro ao juntar PDFs: {e}", exc_info=True)
        # Tenta limpar mesmo em caso de erro
        for temp_path in temp_file_paths:
            try:
                os.remove(temp_path)
            except:
                pass
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



@shared_task(bind=True)
def processar_pdfs(self, file_keys):
    """
    Processa múltiplos PDFs já enviados via presigned URL para o MinIO.
    :param file_keys: lista de chaves (keys) no bucket, ex: ["uploads/20240823_arquivo1.pdf"]
    """
    update_task_status(self.request.id, 'PROCESSANDO')
    try:
        processor = DocumentAIProcessor()
        project_id = os.getenv("PROJECT_ID")
        print(f"Project ID: {project_id}")
        location = os.getenv("LOCATION")
        print(f"Location: {location}")
        processor_id = os.getenv("PROCESSOR_ID")
        print(f"Processor ID: {processor_id}")

        total_files = len(file_keys)
        processed_files = 0
        arquivos_resultado = {}  # Vai armazenar {nome_arquivo: xml_content_string}
        erros = []

        # Criar ZIP em memória para download
        zip_buffer = io.BytesIO()

        with zipfile.ZipFile(zip_buffer, "w", zipfile.ZIP_DEFLATED) as zip_file:
            try:
                for file_key in file_keys:
                    # Define o nome do arquivo a partir da chave
                    file_name = file_key.split('/')[-1]  # Definido fora do try

                    
                    logger.info(f"Baixando arquivo do Addon Bucketeer: {file_key}")
                    
                    # Baixa o arquivo do MinIO
                    pdf_bytes = download_file_from_minio(file_key)
                    logger.info(f"Arquivo baixado: {file_name}, tamanho: {len(pdf_bytes)} bytes")
                    
                
                    # Processa com DocumentAI
                    document_json = processor.processar_pdf(project_id, location, processor_id, pdf_bytes)
                    logger.info(f"Documento processado: {file_name}")

                    # Mapeia campos e converte para XML válido
                    dados_extraidos = processor.mapear_campos(document_json)
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

                    

                # Gera relatório Excel
                excel_bytes = ExcelGenerator.gerar_excel(arquivos_resultado)
                zip_file.writestr(f"relatorio.xlsx", excel_bytes)
                logger.info(f"Relatório Excel adicionado ao ZIP, tamanho: {len(excel_bytes)} bytes")
                processed_files += 1
                logger.info(f"Arquivo {file_name} processado com sucesso")

                # envia o relatório Excel por email
                # date = datetime.strftime("%Y%m%d")
                email_sender = EmailSender()
                email_sender.send_email(
                    destinatario="mvinicius.madeira@gmail.com",
                    assunto="Relatório de Processamento de PDFs",
                    corpo="Segue em anexo o relatório Excel com os dados extraídos.",
                    anexos=[(f"relatorio_de_conversoes.xlsx", excel_bytes)]
                )

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
        logger.info(f"Dicionário de arquivos resultado: {list(arquivos_resultado.keys())}")

        # Resultados do processamento
        result = {
            'success': True,
            'arquivos_resultado': arquivos_resultado,  # Dict com XMLs como strings
            'zip_id': str(arquivo_zip.id),
            'processed_files': processed_files,
            'total_files': total_files,
            'erros': erros
        }

        # Atualiza o status da tarefa para COMPLETO
        update_task_status(self.request.id, 'SUCESSO', json.dumps(result))

        # # cria um relatório excel com os dados extraídos de todos os arquivos processados e adiciona ao zip
        # excel_bytes = ExcelGenerator.gerar_excel(arquivos_resultado)
        # print(f"Dicionário de arquivos resultado: {list(arquivos_resultado.keys())}")
        # zip_file.writestr(f"relatorio.xlsx", excel_bytes)
        # print(f"Relatório Excel adicionado ao ZIP, tamanho: {len(excel_bytes)} bytes")

        # Retorna resultado estruturado
        return result
    
    except Exception as e:
        logger.error(f"Erro geral no processamento: {str(e)}", exc_info=True)
        resultado_erro = {
            'success': False,
            'error': str(e),
            'arquivos_resultado': {},
            'processed_files': 0,
            'total_files': len(file_keys) if file_keys else 0
        }
        update_task_status(self.request.id, 'ERRO', json.dumps(resultado_erro))  # <-- Aqui
        return resultado_erro



@shared_task()
def heartbeat_task():
    logger.info("Celery keep-alive: worker ainda está ativo no servidor")
    return "ok"

