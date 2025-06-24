import streamlit as st
from pathlib import Path
import time
import pandas as pd
import random
import json
import re
from datetime import datetime
from dateutil.parser import parse
import logging
import os 
import base64
import requests
import io
import zipfile

# --- Suas importações existentes ---
#from services import XMLGenerator


# Configurar logging (opcional, mas bom para depuração)
logger = logging.getLogger(__name__)
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')


# --- Variáveis de Ambiente para DocumentAIProcessor ---
PROJECT_ID = os.getenv("PROJECT_ID")
LOCATION = os.getenv("LOCATION")
PROCESSOR_ID = os.getenv("PROCESSOR_ID")

DJANGO_BACKEND_URL = os.getenv("DJANGO_BACKEND_URL", "http://127.0.0.1:8001")

# --- Instância da sua classe XMLGenerator (criada uma vez) ---
# try:
#     xml_generator_instance = XMLGenerator()
#     st.session_state['xml_generator_ready'] = True
# except Exception as e:
#     st.error(f"Erro ao inicializar XMLGenerator: {e}. Verifique se as dependências estão corretas.")
#     st.session_state['xml_generator_ready'] = False
#     xml_generator_instance = None # Define como None se a inicialização falhar

# # --- Instância da sua classe DocumentAIProcessor (criada uma vez) ---
# try:
#     processor_instance = DocumentAIProcessor()
#     st.session_state['doc_ai_processor_ready'] = True
# except Exception as e:
#     st.error(f"Erro ao inicializar DocumentAIProcessor: {e}. Verifique se as dependências estão corretas.")
#     st.session_state['doc_ai_processor_ready'] = False
#     processor_instance = None # Define como None se a inicialização falhar


# --- Configuração da Página ---
st.set_page_config(
    page_title="NFS-e Control - Sistema de Gerenciamento",
    page_icon="🧾",
    layout="wide"
)

st.title("Sistema de Automação para Notas Fiscais de Serviço")
st.markdown("Automatize a extração inteligente de dados de NFS-e em PDF utilizando IA e integre diretamente com seu sistema Domínio via API de forma segura e eficiente.")

# --- Diretórios de Upload e Saída ---
UPLOAD_DIR = Path("data/uploads")
XML_DIR = Path("data/xmls")

UPLOAD_DIR.mkdir(parents=True, exist_ok=True)
XML_DIR.mkdir(parents=True, exist_ok=True)

# --- FUNÇÃO ATUALIZADA PARA INTERAGIR COM O BACKEND DJANGO ---
def call_django_backend_to_process_pdfs(files_data: dict) -> tuple[list, list]:
    """
    Chama o endpoint de upload e processamento do Django backend.
    files_data: um dicionário com {file_name: pdf_bytes}
    Retorna uma tupla (lista de task_ids, mensagem de erro ou None).
    """
    upload_url = f"{DJANGO_BACKEND_URL}/upload-e-processar-pdf/" # Corrigido para a rota correta do Django

    # Preparar os arquivos para envio multipart/form-data
    files_to_send = []
    for file_name, pdf_bytes in files_data.items():
        files_to_send.append(("files", (file_name, pdf_bytes, "application/pdf")))

    try:
        # Aumente o timeout para uploads grandes
        response = requests.post(upload_url, files=files_to_send, timeout=120)
        response.raise_for_status() # Lança um erro para status de erro HTTP (4xx, 5xx)

        response_data = response.json()
        if response.status_code == 200 and "task_ids" in response_data:
            return response_data["task_ids"], None
        else:
            return [], response_data.get("error", "Erro desconhecido no backend.")

    except requests.exceptions.Timeout:
        return [], "O tempo limite de conexão com o backend foi excedido."
    except requests.exceptions.ConnectionError:
        return [], "Não foi possível conectar ao backend Django. Verifique o URL ou se o servidor está rodando."
    except requests.exceptions.HTTPError as e:
        error_detail = e.response.json().get("error", str(e)) if e.response.content else str(e)
        return [], f"Erro HTTP do backend: {e.response.status_code} - {error_detail}"
    except Exception as e:
        return [], f"Erro inesperado ao chamar o backend: {str(e)}"
def call_django_backend(endpoint: str, method: str = "POST", files_data: dict = None, json_data: dict = None) -> dict:
    """
    Função genérica para fazer requisições HTTP para o backend Django.
    :param endpoint: O caminho da URL no backend (ex: "/upload-e-processar-pdf/").
    :param method: O método HTTP ("POST" ou "GET").
    :param files_data: Dicionário de arquivos para enviar (para POST com files).
                       Formato: {"nome_campo": ("nome_arquivo.pdf", conteudo_bytes, "application/pdf")}
    :param json_data: Dicionário de dados JSON para enviar (para POST com JSON).
    :return: A resposta JSON do backend ou None em caso de erro.
    """
    url = f"{DJANGO_BACKEND_URL}{endpoint}"
    headers = {} # Nenhuma autenticação adicional (login_required removido)

    st.sidebar.markdown(f"**Chamando:** `{method}` `{url}`")

    try:
        response = None
        if method.upper() == "POST":
            if files_data:
                # requests.post com 'files' cuida do Content-Type como multipart/form-data
                # files_data deve ser um dicionário onde o valor é (filename, content_bytes, content_type)
                # Ex: {"files": [("file1.pdf", b"...", "application/pdf"), ...]}
                # No seu caso, files_data já está no formato {name: content_bytes}, então precisamos ajustar
                files_payload = {
                    "files": [(name, content, "application/pdf") for name, content in files_data.items()]
                }
                response = requests.post(url, files=files_payload, headers=headers, timeout=120)
            elif json_data:
                headers["Content-Type"] = "application/json"
                response = requests.post(url, json=json_data, headers=headers, timeout=120)
            else:
                response = requests.post(url, headers=headers, timeout=120) # POST sem dados
        elif method.upper() == "GET":
            response = requests.get(url, headers=headers, timeout=120)
        else:
            st.error(f"Método HTTP '{method}' não suportado na função de backend.")
            return None

        response.raise_for_status()  # Lança um HTTPError para respostas 4xx/5xx

        # Tenta retornar JSON, caso contrário, loga e retorna None
        try:
            return response.json()
        except json.JSONDecodeError:
            st.error(f"Backend retornou uma resposta não-JSON válida do endpoint '{endpoint}': {response.text[:500]}...")
            st.sidebar.error(f"Resposta bruta (não-JSON): {response.text[:500]}...") # Exibir no sidebar para debug
            return None

    except requests.exceptions.Timeout:
        st.error(f"O tempo limite de conexão com o backend em '{url}' foi excedido. Tente novamente mais tarde.")
        return None
    except requests.exceptions.ConnectionError:
        st.error(f"Não foi possível conectar ao backend Django em '{url}'. Verifique o URL ou se o servidor está online.")
        return None
    except requests.exceptions.HTTPError as e:
        error_detail = ""
        try:
            error_data = e.response.json()
            error_detail = error_data.get("detail", error_data.get("error", "Erro desconhecido na resposta JSON."))
        except json.JSONDecodeError:
            error_detail = e.response.text # Se não for JSON, pegue o texto puro
        st.error(f"Erro HTTP do backend ({e.response.status_code}) ao chamar '{endpoint}': {error_detail}")
        st.sidebar.error(f"Detalhes do erro HTTP: {e.response.text[:500]}...")
        return None
    except Exception as e:
        st.error(f"Erro inesperado ao chamar o backend em '{endpoint}': {str(e)}")
        return None

# --- Função para Enviar XML para a API Externa (Via Backend Django) ---
def send_xml_to_external_api(xml_content: str, file_name: str) -> dict:
    """
    Envia um único conteúdo XML para a API externa através do endpoint do Django.
    :param xml_content: Conteúdo XML como string.
    :param file_name: Nome do arquivo XML.
    :return: Resposta JSON da API externa via Django.
    """
    st.sidebar.info(f"Preparando envio de '{file_name}'...")
    data_to_send = {
        "xml_content": xml_content,
        "file_name": file_name
    }
    # Chama o endpoint do Django que, por sua vez, chama a API externa
    response = call_django_backend("/send-xml-to-external-api/", method="POST", json_data=data_to_send)
    return response

# --- Função Principal de Processamento e Envio ---
def process_pdfs_and_send_to_api(uploaded_pdfs: list) -> tuple[bool, str]:
    """
    Coordena o upload de PDFs, polling do status da tarefa e envio de XMLs para a API externa.
    :param uploaded_pdfs: Lista de arquivos PDF uploaded pelo usuário.
    :return: Tupla (sucesso: bool, mensagem de erro: str ou None).
    """
    if not uploaded_pdfs:
        return False, "Nenhum arquivo PDF foi fornecido para processamento."

    # Prepara os dados dos arquivos para enviar ao backend
    # Note que aqui estamos passando uma lista de tuplas para 'files', como o requests espera
    files_data_for_backend = {file.name: file.read() for file in uploaded_pdfs}

    # 1. Enviar PDFs para processamento e obter task_ids
    st.info("Passo 1/3: Enviando PDFs para processamento no backend...")
    # call_django_backend espera files_data como {filename: content_bytes}
    response_data = call_django_backend("/upload-e-processar-pdf/", method="POST", files_data=files_data_for_backend)

    if not response_data or "task_ids" not in response_data:
        return False, "Erro ao iniciar o processamento no backend: Resposta inesperada ou 'task_ids' ausente."

    task_ids = response_data["task_ids"]
    st.success(f"Processamento iniciado para {len(task_ids)} tarefa(s) no backend.")

    all_extracted_xmls = {} # Para armazenar os XMLs de todas as tarefas

    # 2. Polling para verificar o status de cada tarefa e extrair XMLs
    st.info("Passo 2/3: Aguardando conclusão das tarefas e extraindo XMLs...")
    for i, task_id in enumerate(task_ids):
        st.write(f"Monitorando tarefa {i+1}/{len(task_ids)}: **{task_id}**...")
        status = "PENDING"
        task_result_data = None

        # Usar um placeholder para atualizar o status em tempo real
        status_placeholder = st.empty()

        polling_attempts = 0
        max_polling_attempts = 60 # 60 * 5 segundos = 5 minutos de espera max
        
        while status in ["PENDING", "STARTED", "RETRY"] and polling_attempts < max_polling_attempts:
            status_placeholder.info(f"Status da tarefa {task_id}: **{status}**. Tentativa {polling_attempts + 1}/{max_polling_attempts}")
            time.sleep(5) # Espera 5 segundos
            polling_attempts += 1

            status_response = call_django_backend(f"/task-status/{task_id}/", method="GET")

            if status_response and "status" in status_response:
                status = status_response["status"]
                if status == "SUCCESS":
                    task_result_data = status_response.get("result")
                    if task_result_data and "zip_bytes" in task_result_data:
                        zip_base64_string = task_result_data["zip_bytes"]
                        zip_decoded_bytes = base64.b64decode(zip_base64_string)

                        # Abrir o ZIP em memória e extrair os XMLs
                        try:
                            with io.BytesIO(zip_decoded_bytes) as zip_buffer:
                                with zipfile.ZipFile(zip_buffer, 'r') as zf:
                                    for xml_file_name in zf.namelist():
                                        if xml_file_name.endswith('.xml'):
                                            with zf.open(xml_file_name) as xml_file:
                                                xml_content = xml_file.read().decode('utf-8')
                                                all_extracted_xmls[xml_file_name] = xml_content
                            status_placeholder.success(f"Tarefa {task_id} concluída e XML(s) extraído(s) com sucesso!")
                            break # Sai do loop de polling, tarefa concluída e dados extraídos
                        except zipfile.BadZipFile:
                            return False, f"Erro: O arquivo ZIP retornado pela tarefa {task_id} está corrompido ou não é um ZIP válido."
                        except Exception as e:
                            return False, f"Erro ao extrair XMLs do ZIP da tarefa {task_id}: {str(e)}"
                    else:
                        return False, f"Tarefa {task_id} concluída, mas não retornou os dados ZIP esperados ('zip_bytes' ausente no 'result')."
                elif status == "FAILURE":
                    error_message = status_response.get('error_message', 'Erro desconhecido')
                    status_placeholder.error(f"A tarefa {task_id} falhou: {error_message}")
                    return False, f"Tarefa {task_id} falhou: {error_message}"
            else:
                status_placeholder.warning(f"Não foi possível obter o status para a tarefa {task_id}. Tentando novamente...")
                # Não sleep extra aqui, o loop já tem 5s.

        if polling_attempts >= max_polling_attempts:
            return False, f"Tempo limite excedido para a tarefa {task_id}. O processamento não foi concluído."

    if not all_extracted_xmls:
        return False, "Nenhum arquivo XML foi extraído para envio. Verifique os logs do Celery para possíveis erros de parsing."

    # 3. Enviar XMLs extraídos para a API Externa via Django
    st.info("Passo 3/3: Enviando XMLs extraídos para a API externa...")
    success_count = 0
    fail_count = 0
    for file_name, xml_content in all_extracted_xmls.items():
        send_result = send_xml_to_external_api(xml_content, file_name)
        if send_result and send_result.get("status") == "success":
            st.success(f"'{file_name}' enviado com sucesso! UUID: {send_result.get('uuid', 'N/A')}")
            success_count += 1
        else:
            st.error(f"Falha ao enviar '{file_name}'. Detalhes: {send_result.get('error', 'Erro desconhecido')}")
            fail_count += 1

    if fail_count == 0:
        return True, f"✅ Todos os {success_count} XML(s) foram enviados com sucesso para a API externa!"
    else:
        return False, f"❌ {success_count} XML(s) enviados com sucesso, {fail_count} falharam no envio."




# --- FUNÇÃO PARA PEGAR O STATUS E RESULTADO DA TAREFA CELERY ---
def get_celery_task_status(task_id: str):
    """
    Consulta o endpoint de status da tarefa Celery no Django backend.
    Retorna o status e meta data da tarefa.
    """
    status_url = f"{DJANGO_BACKEND_URL}/task-status/{task_id}/"
    try:
        response = requests.get(status_url, timeout=30)
        response.raise_for_status()
        return response.json()
    except requests.exceptions.RequestException as e:
        logger.error(f"Erro ao consultar status da tarefa {task_id}: {e}")
        return {"state": "FAILURE", "meta": {"error": str(e)}}


# --- FUNÇÃO PARA DOWNLOAD DO ZIP (se necessário) ---
def get_zip_from_backend(task_id: str):
    """
    Baixa o arquivo ZIP do backend para uma tarefa concluída.
    Retorna os bytes do ZIP ou None em caso de erro.
    """
    download_url = f"{DJANGO_BACKEND_URL}/download-zip/{task_id}/"
    try:
        response = requests.get(download_url, timeout=60)
        response.raise_for_status()
        # O Django retorna base64 do ZIP, então decodifique aqui
        zip_base64 = response.json().get("zip_bytes")
        if zip_base64:
            return base64.b64decode(zip_base64)
        return None
    except requests.exceptions.RequestException as e:
        logger.error(f"Erro ao baixar ZIP para a tarefa {task_id}: {e}")
        return None


# --- Função para enviar XML para a API via Backend Django ---
def send_xml_via_django_backend(xml_content: str, file_name: str) -> tuple[str, str]:
    """
    Envia o conteúdo XML para a API externa via endpoint do Django.
    Retorna o status ("Enviado com Sucesso" ou "Erro no Envio") e detalhes.
    """
    send_url = f"{DJANGO_BACKEND_URL}/send-xml-to-external-api/" # Você precisaria criar este endpoint no Django!

    payload = {
        "xml_content": xml_content,
        "file_name": file_name # Opcional: para o backend saber qual arquivo está enviando
    }

    try:
        response = requests.post(send_url, json=payload, timeout=60)
        response.raise_for_status()

        response_data = response.json()
        if response_data.get("status") == "success":
            return "Enviado com Sucesso", response_data.get("uuid", "UUID não retornado.")
        else:
            return "Erro no Envio", response_data.get("error", "Erro desconhecido no envio.")

    except requests.exceptions.RequestException as e:
        error_detail = e.response.json().get("error", str(e)) if e.response and e.response.content else str(e)
        return "Erro no Envio", f"Erro de rede ou HTTP: {error_detail}"
    

# --- NOVA FUNÇÃO SÍNCRONA PARA PROCESSAR UM ÚNICO PDF ---
# def process_single_pdf_for_xml(pdf_path: Path, doc_ai_processor: DocumentAIProcessor, xml_gen: XMLGenerator) -> tuple[str, str]:
#     """
#     Processa um único PDF para extrair dados e gerar XML.
#     Retorna o status ("Concluído" ou "Erro") e os detalhes (conteúdo XML ou mensagem de erro).
#     """
#     if not (st.session_state.get('doc_ai_processor_ready', False) and st.session_state.get('xml_generator_ready', False)):
#         return "Erro", "Processadores DocumentAI ou XML não inicializados corretamente."

#     if not PROJECT_ID or not LOCATION or not PROCESSOR_ID:
#         return "Erro", "Variáveis de ambiente PROJECT_ID, LOCATION ou PROCESSOR_ID não definidas."

#     try:
#         # Ler os bytes do PDF
#         with open(pdf_path, "rb") as f:
#             pdf_bytes = f.read()

#         logger.info(f"Processando PDF com DocumentAI: {pdf_path.name}")
#         document_json = doc_ai_processor.processar_pdf(PROJECT_ID, LOCATION, PROCESSOR_ID, pdf_bytes)
        
#         logger.info(f"Mapeando campos do JSON: {pdf_path.name}")
#         dados_extraidos = doc_ai_processor.mapear_campos(document_json)
        
#         logger.info(f"Gerando XML ABRASF para: {pdf_path.name}")
#         xml_content = xml_gen.gerar_xml_abrasf(dados_extraidos)

#         # Salva o XML gerado no diretório de XMLs
#         xml_file_path = XML_DIR / pdf_path.with_suffix(".xml").name
#         with open(xml_file_path, "w", encoding="utf-8") as f:
#             f.write(xml_content)

#         logger.info(f"XML gerado e salvo para: {pdf_path.name}")
#         return "Concluído", xml_content

#     except Exception as e:
#         logger.error(f"Erro no processamento de {pdf_path.name}: {e}", exc_info=True)
#         return "Erro", f"Falha no processamento: {str(e)}"

# --- Função de Simulação de Envio para API (Mantenha se ainda não tiver a real) ---
def simulate_api_send(xml_path):
    """Simula o envio do XML para a API."""
    time.sleep(random.uniform(1, 3)) # Simula tempo de envio
    if random.random() < 0.9: # 90% de chance de sucesso
        return "Enviado com Sucesso", "UUID_ABC123" # Exemplo de retorno da API
    else:
        return "Erro no Envio", "Falha de conexão com a API."



# --- Inicialização de Estado da Sessão ---
if 'uploaded_files_info' not in st.session_state:
    st.session_state.uploaded_files_info = []

# --- Abas para Organização do Fluxo ---
tab1, tab2, tab3, tab4 = st.tabs(["📥 Importar PDFs", "🔍 Revisar & Converter", "✉️ Enviar para API", "📊 Histórico"])

# --- TAB 1: Importar PDFs ---
with tab1:
    st.header("Passo 1: Importar Notas em PDF")
    st.markdown("Arraste e solte seus arquivos PDF ou use o botão para selecioná-los.")

    with st.expander("⬆️ Enviar arquivos PDF"):
        uploaded_files = st.file_uploader(
            "Selecione os arquivos de notas fiscais (PDF):",
            type=["pdf"],
            accept_multiple_files=True,
            help="Você pode enviar um ou vários arquivos de uma vez.",
            key="pdf_uploader"
        )

        if uploaded_files:
            new_uploads_count = 0
            for f in uploaded_files:
                file_path = UPLOAD_DIR / f.name
                if not file_path.exists():
                    with open(file_path, "wb") as out:
                        out.write(f.read())
                    st.session_state.uploaded_files_info.append({
                        "Nome do Arquivo": f.name,
                        "Caminho": str(file_path),
                        "Status": "Carregado",
                        "XML Gerado": "-",
                        "Status Envio": "-",
                        "Detalhes": ""
                    })
                    new_uploads_count += 1
                
            if new_uploads_count > 0:
                st.success(f"{new_uploads_count} arquivo(s) novo(s) salvo(s) com sucesso!")

# --- TAB 2: Revisar & Converter ---
with tab2:
    st.header("Passo 2: Revisar e Converter PDFs para XML")
    st.markdown("Verifique os PDFs carregados e inicie o processo de conversão para XML.")

    if not st.session_state.uploaded_files_info:
        st.info("Nenhum PDF carregado ainda. Volte para a aba 'Importar PDFs'.")
    else:
        df_files = pd.DataFrame(st.session_state.uploaded_files_info)
        # Filtra arquivos que ainda não foram processados ou falharam
        df_to_process = df_files[~df_files['Status'].isin(['Concluído', 'Erro'])]

        if not df_to_process.empty:
            st.subheader("PDFs Prontos para Conversão:")

            all_options = df_to_process.index.tolist()
            select_all = st.checkbox("Marcar/Desmarcar Todos", key="checkbox_select_all_convert")

            if select_all:
                default_selection = all_options
            else:
                default_selection = []

            selected_files_indices = st.multiselect(
                "Selecione os PDFs para converter:",
                options=all_options,
                default=default_selection,
                format_func=lambda x: df_to_process.loc[x, "Nome do Arquivo"] + f" ({df_to_process.loc[x, 'Status']})",
                key="multiselect_convert_pdfs"
            )

            if st.button("Converter PDFs Selecionados para XML", key="btn_convert_pdfs"):
                if selected_files_indices:
                    st.info("Preparando arquivos para envio...")
                    files_data_for_backend = {}
                    original_indices_map = {} # Mapeia file_name para o índice original no session_state
                    for idx in selected_files_indices:
                        file_info = st.session_state.uploaded_files_info[idx]
                        file_path = Path(file_info["Caminho"])
                        if file_path.exists():
                            with open(file_path, "rb") as f:
                                files_data_for_backend[file_path.name] = f.read()
                                original_indices_map[file_path.name] = idx
                        else:
                            st.warning(f"Arquivo não encontrado: {file_path.name}. Pulando.")

                    if files_data_for_backend:
                        st.info("Enviando PDFs para processamento no backend...")
                        task_ids, error_message = call_django_backend_to_process_pdfs(files_data_for_backend)

                        if error_message:
                            st.error(f"Falha ao iniciar processamento: {error_message}")
                        elif task_ids:
                            st.success(f"Processamento iniciado para {len(task_ids)} lote(s).")
                            st.session_state['active_task_ids'] = task_ids
                            # Atualiza o status no Streamlit para 'Processando'
                            for file_name, original_idx in original_indices_map.items():
                                st.session_state.uploaded_files_info[original_idx]["Status"] = "Processando"
                                st.session_state.uploaded_files_info[original_idx]["Detalhes"] = "Aguardando resultado do backend..."

                            # Agora, entraremos em um loop para consultar o status
                            st.subheader("Verificando status do processamento...")
                            progress_bar = st.progress(0)
                            all_tasks_completed = False
                            start_time = time.time()
                            total_files_in_tasks = len(files_data_for_backend) # Total de arquivos que foram enviados

                            while not all_tasks_completed and (time.time() - start_time < 300): # Timeout de 5 minutos
                                all_tasks_completed = True
                                completed_count = 0
                                for task_id in st.session_state['active_task_ids']:
                                    status_response = get_celery_task_status(task_id)
                                    state = status_response.get("state")
                                    meta = status_response.get("meta", {})
                                    processed_files_in_task = meta.get("processed", 0)
                                    errored_files_in_task = meta.get("erros", [])

                                    # Atualizar o status dos arquivos individuais se possível
                                    # Esta parte é complexa sem um mapeamento direto de task_id para file_name no meta
                                    # Para simplificar, vamos atualizar o status geral e o resultado final
                                    # Se a API do Django puder retornar o nome do arquivo junto com o status do lote, seria ideal

                                    if state == "SUCCESS":
                                        # Assumimos que o lote foi processado com sucesso
                                        # Para cada arquivo do lote, marcar como Concluído
                                        # Se o backend retornar o XML no meta, você pode salvá-lo aqui
                                        # Por enquanto, vamos buscar o ZIP no final.
                                        completed_count += processed_files_in_task
                                        # Se a tarefa retornou um erro para alguns arquivos dentro do lote
                                        if errored_files_in_task:
                                            for err_file in errored_files_in_task:
                                                if err_file in original_indices_map:
                                                    idx = original_indices_map[err_file]
                                                    st.session_state.uploaded_files_info[idx]["Status"] = "Erro"
                                                    st.session_state.uploaded_files_info[idx]["Detalhes"] = f"Erro no backend: {meta.get('error', 'Erro desconhecido')}"
                                                    st.session_state.uploaded_files_info[idx]["XML Gerado"] = "Não"
                                        # Marcar arquivos processados com sucesso no lote
                                        # Isso requer que 'meta' contenha quais arquivos foram bem-sucedidos
                                        # ou que a API de download seja mais granular
                                        # Por enquanto, vamos presumir que se a tarefa é SUCESSO, todos os arquivos do LOTE foram
                                        # ou que o ZIP final conterá os XMLs.
                                        # Uma abordagem mais robusta seria ter um endpoint que retorne o status de CADA ARQUIVO no lote.

                                    elif state == "PENDING" or state == "PROGRESS":
                                        all_tasks_completed = False
                                        completed_count += processed_files_in_task # Se já processou alguns dentro do lote
                                    elif state == "FAILURE":
                                        # Toda a tarefa falhou, marcar todos os arquivos do lote como erro
                                        for file_name, original_idx in original_indices_map.items():
                                            if not file_info["Status"] == "Concluído": # Para não sobrescrever se já foi concluído
                                                st.session_state.uploaded_files_info[original_idx]["Status"] = "Erro"
                                                st.session_state.uploaded_files_info[original_idx]["Detalhes"] = f"Falha na tarefa Celery: {meta.get('error', 'Erro desconhecido')}"
                                                st.session_state.uploaded_files_info[original_idx]["XML Gerado"] = "Não"
                                        all_tasks_completed = True # Esta tarefa terminou com falha
                                        completed_count += total_files_in_tasks # Marca como completo para a barra de progresso

                                current_progress = min(1.0, completed_count / total_files_in_tasks) if total_files_in_tasks > 0 else 0
                                progress_bar.progress(current_progress)

                                if not all_tasks_completed:
                                    time.sleep(2) # Espera 2 segundos antes de consultar novamente

                            progress_bar.empty()

                            # Após o loop, se todas as tarefas terminaram (sucesso ou falha)
                            if all_tasks_completed:
                                st.success("Verificação de status concluída!")
                                # Tenta baixar o ZIP para cada tarefa concluída
                                for task_id in st.session_state['active_task_ids']:
                                    task_status = get_celery_task_status(task_id)
                                    if task_status.get("state") == "SUCCESS":
                                        zip_bytes = get_zip_from_backend(task_id)
                                        if zip_bytes:
                                            # Aqui você pode salvar o ZIP ou oferecer para download
                                            st.download_button(
                                                label=f"Baixar XMLs Processados (Tarefa {task_id[:6]})",
                                                data=zip_bytes,
                                                file_name=f"xmls_processados_{task_id}.zip",
                                                mime="application/zip",
                                                key=f"download_zip_{task_id}"
                                            )
                                            # Atualize o status dos arquivos que foram parte desta task_id
                                            # Isso é genérico, uma vez que o backend envia um ZIP de múltiplos XMLs
                                            for file_name, original_idx in original_indices_map.items():
                                                if st.session_state.uploaded_files_info[original_idx]["Status"] == "Processando":
                                                    st.session_state.uploaded_files_info[original_idx]["Status"] = "Concluído"
                                                    st.session_state.uploaded_files_info[original_idx]["XML Gerado"] = "Sim"
                                                    st.session_state.uploaded_files_info[original_idx]["Detalhes"] = "XML gerado e pronto para download."
                                        else:
                                            st.error(f"Falha ao baixar o ZIP da tarefa {task_id}.")
                                    elif task_status.get("state") == "FAILURE":
                                        st.error(f"Tarefa {task_id} falhou. Detalhes: {task_status.get('meta', {}).get('error', 'Verifique os logs do backend.')}")
                                # Limpa as tasks ativas
                                st.session_state['active_task_ids'] = []
                            else:
                                st.warning("Processamento ainda em andamento ou tempo limite excedido.")

                            st.rerun() # Reruns para atualizar o DataFrame

        st.subheader("Status dos PDFs Carregados:")
        st.dataframe(df_files[['Nome do Arquivo', 'Status', 'XML Gerado', 'Status Envio']], use_container_width=True)

        # A visualização de PDF e XML agora precisa ser mais dinâmica.
        # Você não tem mais os dados_extraidos diretamente aqui.
        # Você pode:
        # 1. Armazenar os XMLs (após download do ZIP) localmente no Streamlit para visualização.
        # 2. Se o backend puder expor um endpoint para retornar o XML de um arquivo específico (mais complexo).
        # Por simplicidade, vamos apenas mostrar o status.
        pdfs_ready = [info for info in st.session_state.uploaded_files_info if Path(info["Caminho"]).exists()]
        if pdfs_ready:
            selected_pdf_name = st.selectbox(
                "Selecione um PDF para visualizar status:",
                options=[info["Nome do Arquivo"] for info in pdfs_ready],
                format_func=lambda x: x,
                key="selectbox_view_pdf"
            )
            if selected_pdf_name:
                selected_pdf_info = next(info for info in pdfs_ready if info["Nome do Arquivo"] == selected_pdf_name)
                selected_pdf_path = Path(selected_pdf_info["Caminho"])

                col_pdf, col_data = st.columns([1, 1])

                with col_pdf:
                    st.markdown(f"**Visualizando PDF:** `{selected_pdf_name}`")
                    st.components.v1.iframe(str(selected_pdf_path.as_posix()), height=600, scrolling=True)

                with col_data:
                    st.markdown(f"**Status de Processamento:**")
                    st.info(f"Status: {selected_pdf_info['Status']}")
                    st.info(f"XML Gerado: {selected_pdf_info['XML Gerado']}")
                    st.info(f"Detalhes: {selected_pdf_info['Detalhes']}")
                    # Para mostrar o XML, você precisaria salvá-lo após o download do ZIP
                    # Exemplo:
                    # if selected_pdf_info["XML Gerado"] == "Sim":
                    #    xml_file_path_local = XML_DIR / Path(selected_pdf_name).with_suffix(".xml").name
                    #    if xml_file_path_local.exists():
                    #        with open(xml_file_path_local, "r", encoding="utf-8") as f:
                    #            st.code(f.read(), language="xml")
                    #    else:
                    #        st.warning("XML não disponível localmente. Baixe o ZIP para ver.")

        else:
            st.info("Nenhum PDF disponível para visualização.")

# --- TAB 3: Enviar para API ---
with tab3:
    st.header("Passo 3: Enviar XMLs para a API")
    st.markdown("Selecione os XMLs que já foram gerados e envie-os para a API de integração.")

    # A lógica aqui assume que você baixou o ZIP e extraiu os XMLs para algum lugar localmente
    # ou que o Streamlit agora pode fazer requisições para pegar XMLs individuais se o Django os expor.
    # Por simplicidade, para este exemplo, vamos simular que o XML está "disponível" no Streamlit
    # se o status for "Concluído" e "XML Gerado" for "Sim".
    # Em um cenário real, você teria que gerenciar os arquivos XML baixados/extraídos.

    xmls_to_send_info = []
    for info in st.session_state.uploaded_files_info:
        if info["XML Gerado"] == "Sim" and info["Status Envio"] != "Enviado com Sucesso":
            # Para este exemplo, precisamos do conteúdo do XML.
            # Idealmente, o backend retornaria o XML individualmente ou você teria um cache local.
            # Por enquanto, vamos simular o conteúdo XML.
            # Em produção, você precisaria ter o XML real disponível aqui (via download/extração).
            xml_content_placeholder = f"<Nfse><DadosServico><IdentificacaoServico><NomeArquivo>{info['Nome do Arquivo']}</NomeArquivo></IdentificacaoServico></DadosServico></Nfse>"
            xmls_to_send_info.append({
                "Nome do Arquivo": info["Nome do Arquivo"],
                "Caminho": info["Caminho"], # Caminho do PDF original
                "XML Content": xml_content_placeholder, # Substituir por conteúdo XML real
                "Original Index": st.session_state.uploaded_files_info.index(info)
            })

    if not xmls_to_send_info:
        st.info("Nenhum XML pronto para envio ou todos já foram enviados.")
    else:
        df_xmls_to_send = pd.DataFrame(xmls_to_send_info)

        all_xml_options = df_xmls_to_send.index.tolist()
        select_all_xmls = st.checkbox("Marcar/Desmarcar Todos os XMLs para Envio", key="checkbox_select_all_send_xmls")

        if select_all_xmls:
            default_xml_selection = all_xml_options
        else:
            default_xml_selection = []

        selected_xml_indices = st.multiselect(
            "Selecione os XMLs para enviar:",
            options=all_xml_options,
            default=default_xml_selection,
            format_func=lambda x: df_xmls_to_send.loc[x, "Nome do Arquivo"],
            key="multiselect_send_xmls"
        )

        if st.button("Enviar XMLs Selecionados para API", key="btn_send_xmls"):
            if selected_xml_indices:
                st.info("Iniciando envio para a API via backend...")
                progress_bar_send = st.progress(0)
                for i, df_index in enumerate(selected_xml_indices):
                    file_data_to_send = df_xmls_to_send.loc[df_index]
                    original_idx = file_data_to_send["Original Index"]

                    st.session_state.uploaded_files_info[original_idx]["Status Envio"] = "Enviando..."
                    progress_bar_send.progress((i + 1) / len(selected_xml_indices))

                    # Chama a função que interage com o backend Django para enviar o XML
                    status_send, details_send = send_xml_via_django_backend(
                        file_data_to_send["XML Content"], # Usar o conteúdo XML real aqui
                        file_data_to_send["Nome do Arquivo"]
                    )

                    st.session_state.uploaded_files_info[original_idx]["Status Envio"] = status_send
                    st.session_state.uploaded_files_info[original_idx]["Detalhes"] += f" | Envio: {details_send}"

                    time.sleep(0.5)
                progress_bar_send.empty()
                st.success("Processo de envio concluído!")
                st.rerun()

    st.subheader("Status de Envio dos XMLs:")
    if st.session_state.uploaded_files_info:
        df_current_status = pd.DataFrame(st.session_state.uploaded_files_info)
        st.dataframe(df_current_status[['Nome do Arquivo', 'Status', 'XML Gerado', 'Status Envio']], use_container_width=True)
    else:
        st.info("Nenhum arquivo carregado ou processado ainda.")

# --- TAB 4: Histórico ---
with tab4:
    st.header("Passo 4: Histórico de Processamento")
    st.markdown("Consulte o status e os detalhes de todos os arquivos processados.")

    if st.session_state.uploaded_files_info:
        df_history = pd.DataFrame(st.session_state.uploaded_files_info)
        st.dataframe(df_history, use_container_width=True)

        st.markdown("---")
        st.subheader("Filtros de Histórico (Exemplo):")

        status_filter = st.multiselect(
            "Filtrar por Status de Conversão:",
            options=df_history['Status'].unique().tolist(),
            default=df_history['Status'].unique().tolist(),
            key="multiselect_history_status"
        )

        send_status_filter = st.multiselect(
            "Filtrar por Status de Envio:",
            options=df_history['Status Envio'].unique().tolist(),
            default=df_history['Status Envio'].unique().tolist(),
            key="multiselect_history_send_status"
        )

        filtered_df = df_history[
            (df_history['Status'].isin(status_filter)) &
            (df_history['Status Envio'].isin(send_status_filter))
        ]

        st.dataframe(filtered_df[['Nome do Arquivo', 'Status', 'XML Gerado', 'Status Envio', 'Detalhes']], use_container_width=True)
    else:
        st.info("Nenhum histórico disponível ainda.")