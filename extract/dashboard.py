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

# --- Importações do sistema de autenticação ---
from streamlit_auth import StreamlitAuthManager, require_auth, show_login_page
from streamlit_credits import show_credits_sidebar, show_credit_store, show_payment_details, CreditManager

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

# --- Configuração da Página ---
st.set_page_config(
    page_title="NFS-e Control - Sistema de Gerenciamento",
    page_icon="🧾",
    layout="wide"
)

# --- CSS Customizado com Identidade Visual ---
def load_custom_css():
    st.markdown("""
    <style>
    /* Importar fontes do Google */
    @import url('https://fonts.googleapis.com/css2?family=Poppins:wght@300;400;600;700&family=Lato:wght@300;400;700&display=swap');
    
    /* Paleta de cores */
    :root {
        --love-red: #E63946;
        --professional-blue: #1D3557;
        --warm-beige: #F1FAEE;
        --accent-blue: #457B9D;
        --success-green: #2D7D32;
        --warning-orange: #F57C00;
    }
    
    /* Reset e base */
    .main {
        background: linear-gradient(135deg, var(--warm-beige) 0%, #ffffff 100%);
        font-family: 'Lato', sans-serif;
    }
    
    /* Header principal */
    .main-header {
        background: linear-gradient(90deg, var(--professional-blue) 0%, var(--accent-blue) 100%);
        padding: 2rem;
        border-radius: 15px;
        margin-bottom: 2rem;
        box-shadow: 0 8px 32px rgba(29, 53, 87, 0.1);
        text-align: center;
        position: relative;
        overflow: hidden;
    }
    
    .main-header::before {
        content: '';
        position: absolute;
        top: -50%;
        right: -50%;
        width: 200%;
        height: 200%;
        background: radial-gradient(circle, rgba(241, 250, 238, 0.1) 0%, transparent 70%);
        animation: float 6s ease-in-out infinite;
    }
    
    @keyframes float {
        0%, 100% { transform: translateY(0px) rotate(0deg); }
        50% { transform: translateY(-10px) rotate(2deg); }
    }
    
    .main-header h1 {
        font-family: 'Poppins', sans-serif;
        font-weight: 700;
        font-size: 3rem;
        color: white;
        margin: 0;
        text-shadow: 2px 2px 4px rgba(0,0,0,0.1);
        position: relative;
        z-index: 2;
    }
    
    .main-header .subtitle {
        font-family: 'Lato', sans-serif;
        font-size: 1.2rem;
        color: var(--warm-beige);
        margin-top: 0.5rem;
        position: relative;
        z-index: 2;
    }
    
    /* Mascote */
    .mascot {
        font-size: 4rem;
        
        margin: 1rem 0;
        position: relative;
        z-index: 2;
    }
    
    @keyframes bounce {
        0%, 100% { transform: translateY(0px); }
        50% { transform: translateY(-10px); }
    }
    
    /* Títulos */
    h1, h2, h3 {
        font-family: 'Poppins', sans-serif !important;
        font-weight: 700 !important;
        color: var(--professional-blue) !important;
    }
    
    h1 { font-size: 2.5rem !important; }
    h2 { font-size: 2rem !important; }
    h3 { font-size: 1.5rem !important; }
    
    /* Abas customizadas */
    .stTabs [data-baseweb="tab-list"] {
        gap: 10px;
        background: white;
        border-radius: 10px;
        padding: 0.5rem;
        box-shadow: 0 4px 16px rgba(29, 53, 87, 0.1);
    }
    
    .stTabs [data-baseweb="tab"] {
        background: var(--warm-beige);
        border-radius: 8px;
        font-family: 'Poppins', sans-serif;
        font-weight: 600;
        color: var(--professional-blue);
        border: 2px solid transparent;
        transition: all 0.3s ease;
    }
    
    .stTabs [data-baseweb="tab"]:hover {
        background: var(--love-red);
        color: white;
        transform: translateY(-2px);
        box-shadow: 0 4px 12px rgba(230, 57, 70, 0.3);
    }
    
    .stTabs [aria-selected="true"] {
        background: var(--love-red) !important;
        color: white !important;
        border-color: var(--professional-blue) !important;
    }
    
    /* Botões customizados */
    .stButton button {
        background: linear-gradient(45deg, var(--love-red), #ff4757);
        color: white;
        border: none;
        border-radius: 25px;
        font-family: 'Poppins', sans-serif;
        font-weight: 600;
        padding: 0.75rem 2rem;
        transition: all 0.3s ease;
        box-shadow: 0 4px 15px rgba(230, 57, 70, 0.3);
    }
    
    .stButton button:hover {
        transform: translateY(-2px);
        box-shadow: 0 6px 20px rgba(230, 57, 70, 0.4);
        background: linear-gradient(45deg, #d12d3c, var(--love-red));
    }
    
    /* Botões secundários */
    .secondary-button {
        background: linear-gradient(45deg, var(--professional-blue), var(--accent-blue)) !important;
        color: white !important;
        border-radius: 20px !important;
        font-family: 'Poppins', sans-serif !important;
        font-weight: 500 !important;
        box-shadow: 0 3px 10px rgba(29, 53, 87, 0.3) !important;
    }
    
    /* Cards e containers */
    .metric-card {
        background: white;
        padding: 1.5rem;
        border-radius: 15px;
        box-shadow: 0 4px 20px rgba(29, 53, 87, 0.1);
        border-left: 4px solid var(--love-red);
        margin: 1rem 0;
        transition: transform 0.3s ease;
    }
    
    .metric-card:hover {
        transform: translateY(-5px);
        box-shadow: 0 8px 30px rgba(29, 53, 87, 0.15);
    }
    
    .info-box {
        background: linear-gradient(135deg, var(--warm-beige), white);
        padding: 1.5rem;
        border-radius: 12px;
        border: 1px solid rgba(29, 53, 87, 0.1);
        margin: 1rem 0;
    }
    
    /* Expanders customizados */
    .streamlit-expanderHeader {
        background: var(--warm-beige) !important;
        border-radius: 10px !important;
        font-family: 'Poppins', sans-serif !important;
        font-weight: 600 !important;
        color: var(--professional-blue) !important;
    }
    
    /* File uploader */
    .stFileUploader > div > div {
        background: var(--warm-beige);
        border: 2px dashed var(--love-red);
        border-radius: 15px;
        padding: 2rem;
        text-align: center;
    }
    
    /* Progress bars */
    .stProgress .st-bo {
        background: var(--love-red);
    }
    
    /* Selectbox e multiselect */
    .stSelectbox > div > div {
        background: white;
        border: 2px solid var(--warm-beige);
        border-radius: 10px;
        font-family: 'Lato', sans-serif;
    }
    
    /* Dataframes */
    .dataframe {
        border-radius: 10px;
        overflow: hidden;
        box-shadow: 0 4px 15px rgba(29, 53, 87, 0.1);
    }
    
    /* Sidebar */
    .css-1d391kg {
        background: linear-gradient(180deg, var(--professional-blue), var(--accent-blue));
    }
    
    .sidebar .sidebar-content {
        background: white;
        border-radius: 15px;
        margin: 1rem;
        padding: 1rem;
    }
    
    /* Mensagens de status */
    .stSuccess {
        background: linear-gradient(90deg, #4CAF50, #66BB6A);
        color: white;
        border-radius: 10px;
        font-family: 'Lato', sans-serif;
    }
    
    .stError {
        background: linear-gradient(90deg, #F44336, #EF5350);
        color: white;
        border-radius: 10px;
        font-family: 'Lato', sans-serif;
    }
    
    .stWarning {
        background: linear-gradient(90deg, #FF9800, #FFB74D);
        color: white;
        border-radius: 10px;
        font-family: 'Lato', sans-serif;
    }
    
    .stInfo {
        background: linear-gradient(90deg, var(--accent-blue), #64B5F6);
        color: white;
        border-radius: 10px;
        font-family: 'Lato', sans-serif;
    }
    
    /* Ícones customizados */
    .icon {
        font-size: 1.5rem;
        margin-right: 0.5rem;
        vertical-align: middle;
    }
    
    /* Animações de entrada */
    .fade-in {
        animation: fadeIn 0.8s ease-in;
    }
    
    @keyframes fadeIn {
        from { opacity: 0; transform: translateY(20px); }
        to { opacity: 1; transform: translateY(0); }
    }
    
    /* Responsive */
    @media (max-width: 768px) {
        .main-header h1 { font-size: 2rem !important; }
        .main-header .subtitle { font-size: 1rem !important; }
        .mascot { font-size: 3rem; }
    }
    </style>
    """, unsafe_allow_html=True)

# Aplicar CSS customizado
load_custom_css()

# --- Header Principal com Mascote ---
def render_main_header():
    st.markdown("""
    <div class="main-header fade-in">
        <h1>LoveNFSE</h1>
        <div class="subtitle">A ferramenta que faz você amar até a nota fiscal da prefeitura</div>
    </div>
    """, unsafe_allow_html=True)

# --- Sidebar com Informações do Usuário ---
def render_user_sidebar():
    show_credits_sidebar()

# --- Cards de Métricas ---
def render_metrics_cards():
    col1, col2, col3, col4 = st.columns(4)
    
    total_files = len(st.session_state.uploaded_files_info)
    processed_files = len([f for f in st.session_state.uploaded_files_info if f['Status'] == 'Concluído'])
    success_rate = (processed_files / total_files * 100) if total_files > 0 else 0
    
    with col1:
        st.markdown(f"""
        <div class="metric-card">
            <div style="font-size: 2rem; color: #E63946; margin-bottom: 0.5rem;">📄</div>
            <div style="font-family: 'Poppins', sans-serif; font-weight: 700; font-size: 2rem; color: #1D3557;">{total_files}</div>
            <div style="font-family: 'Lato', sans-serif; color: #457B9D;">PDFs Carregados</div>
        </div>
        """, unsafe_allow_html=True)
    
    with col2:
        st.markdown(f"""
        <div class="metric-card">
            <div style="font-size: 2rem; color: #2D7D32; margin-bottom: 0.5rem;">✅</div>
            <div style="font-family: 'Poppins', sans-serif; font-weight: 700; font-size: 2rem; color: #1D3557;">{processed_files}</div>
            <div style="font-family: 'Lato', sans-serif; color: #457B9D;">Processados</div>
        </div>
        """, unsafe_allow_html=True)
    
    with col3:
        st.markdown(f"""
        <div class="metric-card">
            <div style="font-size: 2rem; color: #F57C00; margin-bottom: 0.5rem;">📊</div>
            <div style="font-family: 'Poppins', sans-serif; font-weight: 700; font-size: 2rem; color: #1D3557;">{success_rate:.1f}%</div>
            <div style="font-family: 'Lato', sans-serif; color: #457B9D;">Taxa de Sucesso</div>
        </div>
        """, unsafe_allow_html=True)
    
    with col4:
        estimated_time_saved = processed_files * 5  # 5 minutos economizados por arquivo
        st.markdown(f"""
        <div class="metric-card">
            <div style="font-size: 2rem, color: #E63946, margin-bottom: 0.5rem;">⏱️</div>
            <div style="font-family: 'Poppins', sans-serif; font-weight: 700; font-size: 2rem; color: #1D3557;">{estimated_time_saved}</div>
            <div style="font-family: 'Lato', sans-serif; color: #457B9D;">Minutos Economizados</div>
        </div>
        """, unsafe_allow_html=True)


# --- Inicialização do Sistema de Autenticação ---
StreamlitAuthManager.initialize_session_state()

# --- Inicialização de Estado da Sessão (MOVER PARA ANTES DA AUTENTICAÇÃO) ---
if 'uploaded_files_info' not in st.session_state:
    st.session_state.uploaded_files_info = []
    

# Verifica autenticação antes de mostrar qualquer conteúdo
if not StreamlitAuthManager.ensure_authenticated():
    show_login_page()
    st.stop()  # Para a execução aqui se não estiver autenticado

# Se chegou até aqui, o usuário está autenticado
render_main_header()
render_user_sidebar()

# --- Verifica se deve mostrar a loja de créditos ---
if st.session_state.get('show_payment_details'):
    show_payment_details()
    st.stop()

if st.session_state.get('show_credit_store'):
    show_credit_store()
    st.stop()

# --- Métricas Dashboard ---
render_metrics_cards()

# Se chegou até aqui, o usuário está autenticado
# st.title("Sistema de Automação para Notas Fiscais de Serviço")
# st.markdown("Automatize a extração inteligente de dados de NFS-e em PDF utilizando IA e integre diretamente com seu sistema Domínio via API de forma segura e eficiente.")

# --- Diretórios de Upload e Saída ---
UPLOAD_DIR = Path("data/uploads")
XML_DIR = Path("data/xmls")

UPLOAD_DIR.mkdir(parents=True, exist_ok=True)
XML_DIR.mkdir(parents=True, exist_ok=True)





# --- Função Genérica de Comunicação com o Backend Django ---
def call_django_backend(endpoint: str, method: str = "POST", 
                        files_data: dict = None, 
                        json_data: dict = None,
                        raw_bytes: bool = False) -> dict:
    """
    Função genérica para fazer requisições HTTP autenticadas para o backend Django.
    Exibe mensagens de depuração na sidebar.
    :param endpoint: O caminho da URL no backend (ex: "/upload-e-processar-pdf/").
    :param method: O método HTTP ("POST" ou "GET").
    :param files_data: Dicionário de arquivos para enviar (para POST com files).
                       Formato: {"nome_arquivo.pdf": conteudo_bytes}
    :param json_data: Dicionário de dados JSON para enviar (para POST com JSON).
    :return: A resposta JSON do backend ou None em caso de erro.
    """
    # Verifica se está autenticado
    if not StreamlitAuthManager.ensure_authenticated():
        st.error("Sessão expirada. Por favor, faça login novamente.")
        return None
    
    url = f"{DJANGO_BACKEND_URL}{endpoint}"
    headers = StreamlitAuthManager.get_auth_headers()
    
    # Debug para verificar se o token está sendo enviado
    import logging
    logger = logging.getLogger(__name__)
    logger.info(f"Calling {method} {url}")
    logger.info(f"Headers: {headers}")

    try:
        response = None
        if method.upper() == "POST":
            if files_data:
                # Para files, não incluir Content-Type no header (requests define automaticamente)
                file_headers = {k: v for k, v in headers.items() if k != 'Content-Type'}
                
                # Transforma o dicionário files_data no formato que requests.post espera para 'files'
                files_payload = []
                for name, content in files_data.items():
                    files_payload.append(("files[]", (name, content, "application/pdf")))
                
                response = requests.post(url, files=files_payload, headers=file_headers, timeout=120)
            elif json_data:
                response = requests.post(url, json=json_data, headers=headers, timeout=120)
            else:
                response = requests.post(url, headers=headers, timeout=120)
        elif method.upper() == "GET":
            response = requests.get(url, headers=headers, timeout=120)
        else:
            st.error(f"Método HTTP '{method}' não suportado na função de backend.")
            return None

        response.raise_for_status() # Lança um HTTPError para respostas 4xx/5xx

        try:
            return response.json()
        except json.JSONDecodeError:
            st.error(f"Backend retornou uma resposta não-JSON válida do endpoint '{endpoint}': {response.text[:500]}...")
            return None

    except requests.exceptions.Timeout:
        st.error(f"O tempo limite de conexão com o backend em '{url}' foi excedido. Tente novamente mais tarde.")
        return None
    except requests.exceptions.ConnectionError:
        st.error(f"Não foi possível conectar ao backend Django em '{url}'. Verifique o URL ou se o servidor está online.")
        return None
    except requests.exceptions.HTTPError as e:
        if e.response.status_code == 401:
            st.error("Sessão expirada. Por favor, faça login novamente.")
            StreamlitAuthManager.logout()
            st.rerun()
            return None
        
        error_detail = ""
        try:
            error_data = e.response.json()
            error_detail = error_data.get("detail", error_data.get("error", "Erro desconhecido na resposta JSON."))
        except json.JSONDecodeError:
            error_detail = e.response.text
        st.error(f"Erro HTTP do backend ({e.response.status_code}) ao chamar '{endpoint}': {error_detail}")
        return None
    except Exception as e:
        st.error(f"Erro inesperado ao chamar o backend em '{endpoint}': {str(e)}")
        return None


# --- Função Genérica de Comunicação com o Backend Django (para ZIPs) ---
def call_django_backend_zip_bytes(endpoint: str, method: str = "GET") -> bytes | None:
    url = f"{DJANGO_BACKEND_URL}{endpoint}"
    headers = {}
    #st.sidebar.markdown(f"**Chamando:** `{method.upper()}` `{url}`")

    try:
        if method.upper() == "GET":
            response = requests.get(url, headers=headers, timeout=120)
        else:
            st.error(f"Método HTTP '{method}' não suportado para download ZIP.")
            return None

        response.raise_for_status()
        return response.content

    except requests.exceptions.Timeout:
        st.error(f"Tempo limite excedido para '{url}'.")
        return None
    except requests.exceptions.ConnectionError:
        st.error(f"Erro de conexão ao '{url}'.")
        return None
    except requests.exceptions.HTTPError as e:
        st.error(f"Erro HTTP ({e.response.status_code}) ao chamar '{endpoint}': {e.response.text[:500]}")
        return None
    except Exception as e:
        st.error(f"Erro inesperado ao chamar '{endpoint}': {str(e)}")
        return None

# --- Função para Enviar XML para a API Externa (Via Backend Django) ---
def send_xml_to_external_api(xml_content: str, file_name: str) -> dict:
    """
    Envia um único conteúdo XML para a API externa através do endpoint do Django.
    :param xml_content: Conteúdo XML como string.
    :param file_name: Nome do arquivo XML.
    :return: Resposta JSON da API externa via Django.
    """
    st.sidebar.info(f"Preparando envio de '{file_name}' para a API externa...")
    data_to_send = {
        "xml_content": xml_content,
        "file_name": file_name
    }
    response = call_django_backend("/send-xml-to-external-api/", method="POST", json_data=data_to_send)
    return response

# --- Função Principal de Processamento de PDFs e Armazenamento dos XMLs ---
def process_pdfs_for_extraction(uploaded_pdfs: list) -> None:
    """
    Coordena o upload de PDFs, polling do status da tarefa Celery e armazena os XMLs extraídos
    em st.session_state para posterior seleção e envio.
    """
    if not uploaded_pdfs:
        st.error("Nenhum arquivo PDF foi fornecido para processamento.")
        return

    # Limpa estados anteriores para um novo processo
    st.session_state.extracted_xmls = {}
    st.session_state.selected_xmls_to_send = []
    st.session_state.processing_status = "processing"

    files_data_for_backend = {file.name: file.read() for file in uploaded_pdfs}

    # 1. Enviar PDFs para processamento e obter task_ids
    st.info("Passo 1: Enviando PDFs para processamento no backend...")
    response_data = call_django_backend("/upload-e-processar-pdf/", method="POST", 
                                        files_data=files_data_for_backend,
                                        raw_bytes=True
                                        )

    if not response_data or "task_ids" not in response_data:
        st.session_state.processing_status = "failed"
        st.error("Erro ao iniciar o processamento no backend: Resposta inesperada ou 'task_ids' ausente.")
        return

    task_ids = response_data["task_ids"]
    st.success(f"Processamento iniciado para {len(task_ids)} tarefa(s) no backend. Aguarde a conclusão...")

    # 2. Polling para verificar o status de cada tarefa e extrair XMLs
    # Este spinner vai cobrir todo o tempo de processamento das tarefas no Celery
    with st.spinner("Processando PDFs e gerando XMLs (pode levar alguns minutos, por favor, não feche esta aba)..."):
        all_tasks_successful = True
        temp_extracted_xmls = {} # Acumula XMLs de todas as tarefas

        for i, task_id in enumerate(task_ids):
            task_succeeded_locally = False # Flag para controle de loop de polling para esta tarefa
            polling_attempts = 0
            max_polling_attempts = 120 # 120 tentativas * 5 segundos = 600 segundos (10 minutos)
            
            # Placeholder específico para feedback desta tarefa
            task_feedback_placeholder = st.empty()
            task_feedback_placeholder.info(f"Aguardando tarefa {i+1}/{len(task_ids)} (**{task_id}**)...")

            while not task_succeeded_locally and polling_attempts < max_polling_attempts:
                time.sleep(5) # Espera 5 segundos antes de verificar novamente
                polling_attempts += 1
                status_response = call_django_backend(f"/task-status/{task_id}/", method="GET")

                if status_response and "status" in status_response:
                    status = status_response["status"]
                    if status == "SUCCESS":
                        task_feedback_placeholder.success(f"Tarefa {task_id} concluída!")
                        task_result_data = status_response.get("result")
                        if task_result_data and "extracted_xmls" in task_result_data:
                            # A resposta da tarefa Celery agora deve ter 'extracted_xmls'
                            for xml_file_name, xml_content in task_result_data["extracted_xmls"].items():
                                temp_extracted_xmls[xml_file_name] = xml_content
                            task_succeeded_locally = True # Marca esta tarefa como concluída localmente
                        else:
                            st.error(f"Tarefa {task_id} concluída, mas 'extracted_xmls' ausente no resultado. Verifique os logs do Celery.")
                            all_tasks_successful = False
                            break # Sai do loop de polling para esta tarefa
                    elif status == "FAILURE":
                        error_message = status_response.get('error_message', 'Erro desconhecido')
                        task_feedback_placeholder.error(f"A tarefa {task_id} falhou: {error_message}")
                        all_tasks_successful = False
                        break # Sai do loop de polling para esta tarefa
                    else:
                        task_feedback_placeholder.info(f"Status da tarefa {task_id}: **{status}** (tentativa {polling_attempts})")
                else:
                    task_feedback_placeholder.warning(f"Não foi possível obter o status para a tarefa {task_id}. Tentando novamente...")
                    # O tempo de sleep já está no loop, não adicionar mais.

            if polling_attempts >= max_polling_attempts and not task_succeeded_locally:
                st.error(f"Tempo limite excedido para a tarefa {task_id}. O processamento não foi concluído.")
                all_tasks_successful = False
                break # Sai do loop principal de tarefas

    # Após o loop de todas as tarefas
    if all_tasks_successful and temp_extracted_xmls:
        st.session_state.extracted_xmls = temp_extracted_xmls
        st.session_state.processing_status = "completed"
        st.success("🎉 Todos os PDFs foram processados e os XMLs estão prontos para envio!")
        # Força o re-render da página para mostrar a seção de XMLs extraídos imediatamente
        st.experimental_rerun()
    else:
        st.session_state.processing_status = "failed"
        st.error("❌ O processamento falhou ou nenhum XML foi extraído. Verifique os logs do backend.")

# --- Função para Juntar PDFs (mantida como está, sem grandes refatorações aqui) ---
def merge_pdfs_and_download(merge_files: list, output_filename: str) -> None:
    """
    Função para gerenciar o processo de juntar PDFs e permitir o download.
    :param merge_files: Lista de arquivos PDF uploaded para merge.
    :param output_filename: Nome do arquivo de saída para o PDF combinado.
    """
    if len(merge_files) < 2:
        st.warning("Por favor, selecione pelo menos dois PDFs para juntar.")
        return

    pdf_contents_base64 = {file.name: base64.b64encode(file.read()).decode('utf-8') for file in merge_files}
    st.info("Enviando PDFs para merge no backend...")
    merge_response = call_django_backend(
        "/merge_pdfs/",
        method="POST",
        json_data={"pdf_contents_base64": pdf_contents_base64, "output_filename": output_filename}
    )

    if merge_response and "task_id" in merge_response:
        merge_task_id = merge_response["task_id"]
        st.success(f"Tarefa de merge iniciada! ID: {merge_task_id}")

        merge_status_placeholder = st.empty()
        merge_status = "PENDING"
        merge_polling_attempts = 0
        max_merge_polling_attempts = 60 # 5 minutos de espera max

        with st.spinner(f"Aguardando merge da tarefa {merge_task_id}..."):
            while merge_status in ["PENDING", "STARTED", "RETRY"] and merge_polling_attempts < max_merge_polling_attempts:
                merge_status_placeholder.info(f"Status do merge da tarefa {merge_task_id}: **{merge_status}**. Tentativa {merge_polling_attempts + 1}/{max_merge_polling_attempts}")
                time.sleep(5)
                merge_polling_attempts += 1
                status_check = call_django_backend(f"/task-status/{merge_task_id}/", method="GET") # Use TaskStatusView

                if status_check and "status" in status_check:
                    merge_status = status_check["status"]
                    if merge_status == "SUCCESS":
                        merged_data = status_check.get("result") # O resultado do merge_pdfs_task
                        if merged_data and "merged_pdf_bytes" in merged_data:
                            merged_pdf_bytes = base64.b64decode(merged_data["merged_pdf_bytes"])
                            st.success("PDFs combinados com sucesso!")
                            st.download_button(
                                label="Baixar PDF Combinado",
                                data=merged_pdf_bytes,
                                file_name=output_filename,
                                mime="application/pdf"
                            )
                        else:
                            st.error("Erro: Merge concluído, mas o PDF combinado não foi retornado.")
                        break
                    elif merge_status == "FAILURE":
                        st.error(f"Falha na tarefa de merge: {status_check.get('error_message', 'Erro desconhecido')}")
                        break
                else:
                    merge_status_placeholder.warning("Não foi possível obter o status do merge.")
            
            if merge_polling_attempts >= max_merge_polling_attempts:
                st.error(f"Tempo limite excedido para a tarefa de merge {merge_task_id}. O merge não foi concluído.")
    else:
        st.error("Erro ao iniciar a tarefa de merge no backend.")


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
    Baixa o ZIP gerado diretamente do backend.
    Retorna os bytes do ZIP ou None em caso de erro.
    """
    download_url = f"{DJANGO_BACKEND_URL}/download-zip/{task_id}/"
    try:
        response = requests.get(download_url, timeout=60)
        response.raise_for_status()
        return response.content  # <-- agora retorna bytes direto
    except requests.exceptions.RequestException as e:
        logger.error(f"Erro ao baixar ZIP: {e}")
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
    st.markdown("""
    <div class="fade-in">
        <h2><span class="icon">📥</span>Importar Suas Notas Fiscais</h2>
        <div class="info-box">
            <p style="font-family: 'Lato', sans-serif; margin: 0;">
                <strong>💡 Dica:</strong> Arraste e solte seus arquivos PDF ou use o botão abaixo. 
                Nossa IA processará automaticamente os dados com precisão!
            </p>
        </div>
    </div>
    """, unsafe_allow_html=True)

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
                with open(file_path, "wb") as out:
                    out.write(f.read())
                
                # Verifica se o arquivo já existe na lista (evita duplicação na interface)
                existing_file = next((info for info in st.session_state.uploaded_files_info 
                                    if info["Nome do Arquivo"] == f.name), None)
                
                if existing_file:
                    # Atualiza o arquivo existente para status "Carregado" novamente
                    existing_file["Status"] = "Carregado"
                    existing_file["XML Gerado"] = "-"
                    existing_file["Status Envio"] = "-"
                    existing_file["Detalhes"] = "Arquivo recarregado"
                else:
                    # Adiciona novo arquivo à lista
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
                st.success(f"{new_uploads_count} arquivo(s) salvo(s) com sucesso!")

# --- TAB 2: Processar & Converter ---
with tab2:
    st.markdown("""
    <div class="fade-in">
        <h2><span class="icon">🔄</span>Processar e Converter</h2>
        <div class="info-box">
            <p style="font-family: 'Lato', sans-serif; margin: 0;">
                <strong>🚀 Nossa IA:</strong> Extrai dados automaticamente com 99.9% de precisão. 
                Selecione os PDFs e deixe a mágica acontecer!
            </p>
        </div>
    </div>
    """, unsafe_allow_html=True)

    if not st.session_state.uploaded_files_info:
        st.info("Nenhum PDF carregado ainda. Volte para a aba 'Importar PDFs'.")
        # Cria DataFrame vazio para evitar erro
        df_files = pd.DataFrame(columns=['Nome do Arquivo', 'Status', 'XML Gerado', 'Status Envio'])
    else:
        # Cria DataFrame com os arquivos carregados
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
                    # Verifica créditos BASEADO NO NÚMERO DE ARQUIVOS SELECIONADOS
                    credit_check = CreditManager.check_credits_for_files(len(selected_files_indices))
                    
                    if not credit_check['has_enough']:
                        st.error(f"""
                        ❌ **Créditos Insuficientes!**
                        
                        - **Arquivos selecionados:** {len(selected_files_indices)}
                        - **Créditos necessários:** {credit_check['required']}
                        - **Seus créditos:** {credit_check['current_balance']}
                        - **Faltam:** {credit_check['missing']} crédito(s)
                        
                        Cada arquivo consome 1 crédito. Compre mais créditos para continuar! 🛒
                        """)
                        
                        if st.button("🛒 Comprar Créditos Agora", type="primary"):
                            st.session_state.show_credit_store = True
                            st.rerun()
                        
                        st.stop()
                    
                    # Mostra confirmação DETALHADA de consumo
                    st.info(f"""
                    ℹ️ **Confirmação de Créditos**
                    
                    - **Arquivos a processar:** {len(selected_files_indices)}
                    - **Créditos que serão consumidos:** {credit_check['required']}
                    - **Seus créditos atuais:** {credit_check['current_balance']}
                    - **Créditos restantes após processamento:** {credit_check['remaining_after']}
                    
                    💡 **Importante:** Os créditos serão debitados ANTES do processamento iniciar.
                    """)
                    
                    selected_files = [st.session_state.uploaded_files_info[i] for i in selected_files_indices]
                    
                    # Prepara os arquivos para envio
                    files_dict = {}
                    for file_info in selected_files:
                        # Lê o arquivo do disco
                        file_path = Path(file_info["Caminho"])
                        if file_path.exists():
                            with open(file_path, "rb") as f:
                                files_dict[file_info["Nome do Arquivo"]] = f.read()
                    
                    with st.spinner("🚀 Enviando arquivos para processamento..."):
                        response = call_django_backend("/upload-e-processar-pdf/", files_data=files_dict)
                    
                    if response:
                        if response.get("success"):
                            # CORRIGIDO: Agora recebemos um único task_id
                            task_id = response.get("task_id")  # Em vez de task_ids
                            merge_id = response.get("merge_id", "")
                            
                            st.session_state.task_status = {
                                "task_id": task_id,  # Único task_id
                                "merge_id": merge_id,
                                "files_count": response.get("files_count", len(selected_files)),
                                "credits_used": response.get("credits_used", len(selected_files)),
                                "remaining_credits": response.get("remaining_credits", 0)
                            }
                            
                            st.success(f"""
                            ✅ **Processamento Iniciado com Sucesso!**
                            
                            - **Arquivos enviados:** {len(selected_files)}
                            - **Créditos consumidos:** {response.get('credits_used', len(selected_files))}
                            - **Créditos restantes:** {response.get('remaining_credits', 0)}
                            - **Task ID:** {task_id}
                            
                            ⏳ Aguarde o processamento ser concluído...
                            """)
                            
                            st.rerun()
                        else:
                            st.error(f"❌ Erro no processamento: {response.get('error', 'Erro desconhecido')}")
                    else:
                        st.error("❌ Falha na comunicação com o backend para iniciar o processamento. Verifique logs.")

    # Seção de Status - SEMPRE EXIBIDA (fora dos if/else anteriores)
    st.markdown("---")
    st.subheader("Status dos PDFs Carregados:")
    
    if not df_files.empty:
        st.dataframe(df_files[['Nome do Arquivo', 'Status', 'XML Gerado', 'Status Envio']], use_container_width=True)
    else:
        st.info("Nenhum arquivo carregado ainda.")

    # Verificação de status de tarefas em andamento
    if "task_status" in st.session_state and st.session_state.task_status:
        task_id = st.session_state.task_status["task_id"]
        
        with st.spinner("🔄 Verificando status do processamento..."):
            status_response = call_django_backend(f"/task-status/{task_id}/", method="GET")
        
        if status_response:
            state = status_response.get("state", "UNKNOWN")
            
            if state == "SUCCESS":
                st.success("✅ Processamento concluído com sucesso!")
                
                meta = status_response.get("meta", {})
                arquivos_resultado = meta.get("arquivos_resultado", {})
                zip_id = meta.get("zip_id")
                erros = meta.get("erros", [])
                
                # Log para debug
                st.write("**Debug - Tipo de arquivos_resultado:**", type(arquivos_resultado))
                st.write("**Debug - Chaves:**", list(arquivos_resultado.keys()) if isinstance(arquivos_resultado, dict) else "Não é dict")
                
                if arquivos_resultado and isinstance(arquivos_resultado, dict):
                    # Armazena XMLs corretamente
                    st.session_state.xmls_gerados = {}
                    
                    for file_name, xml_content in arquivos_resultado.items():
                        if isinstance(xml_content, str):
                            # Verifica se é XML válido
                            if xml_content.strip().startswith('<?xml') or xml_content.strip().startswith('<'):
                                st.session_state.xmls_gerados[file_name] = xml_content
                                st.write(f"✅ XML válido para {file_name} (tamanho: {len(xml_content)} chars)")
                            else:
                                st.error(f"❌ XML inválido para {file_name}: não começa com '<'")
                                st.write(f"Conteúdo recebido: {xml_content[:100]}...")
                        else:
                            st.error(f"❌ Formato incorreto para {file_name}: {type(xml_content)}")
                    
                    # Atualiza status dos arquivos processados
                    for file_name in arquivos_resultado.keys():
                        for i, file_info in enumerate(st.session_state.uploaded_files_info):
                            if file_info["Nome do Arquivo"] == file_name:
                                st.session_state.uploaded_files_info[i]["Status"] = "Concluído"
                                st.session_state.uploaded_files_info[i]["XML Gerado"] = "Sim"
                
                if zip_id:
                    st.session_state.zip_id = zip_id
                
                if erros:
                    st.warning(f"⚠️ Alguns arquivos tiveram problemas: {erros}")
                
                # Limpa o status da tarefa
                del st.session_state.task_status
                st.rerun()
                
            elif state == "FAILURE":
                st.error("❌ Erro no processamento!")
                error_message = status_response.get("meta", {}).get("error", "Erro desconhecido")
                st.error(f"Detalhes: {error_message}")
                
                # Limpa o status da tarefa
                del st.session_state.task_status
                
            elif state in ["PENDING", "STARTED"]:
                st.info(f"⏳ Status: {state} - Aguardando conclusão...")
                time.sleep(2)
                st.rerun()
            else:
                st.warning(f"⚠️ Status desconhecido: {state}")

    # Botões de download corrigidos:
    if st.session_state.get('xmls_gerados'):
        st.markdown("---")
        st.markdown("### 📄 XMLs Gerados:")
        
        xmls_gerados = st.session_state.get('xmls_gerados', {})
        
        if isinstance(xmls_gerados, dict) and xmls_gerados:
            for file_name, xml_content in xmls_gerados.items():
                
                # Verifica se é string válida
                if isinstance(xml_content, str) and xml_content.strip():
                    
                    # Verifica se é XML válido
                    if xml_content.strip().startswith('<?xml') or xml_content.strip().startswith('<'):
                        
                        # Mostra preview do XML
                        with st.expander(f"📄 Preview: {file_name}"):
                            st.code(xml_content[:500] + "..." if len(xml_content) > 500 else xml_content, language="xml")
                        
                        # Botão de download
                        button_key = f"download_btn_{file_name}_{len(xml_content)}"
                        
                        st.download_button(
                            label=f"📅 Baixar XML - {file_name.replace('.pdf', '.xml')}",
                            data=xml_content,
                            file_name=file_name.replace('.pdf', '.xml'),
                            mime="application/xml",
                            key=button_key
                        )
                    else:
                        st.error(f"❌ XML inválido para {file_name}: não é XML válido")
                        st.code(xml_content[:200], language="text")
                else:
                    st.error(f"❌ Conteúdo inválido para {file_name}: {type(xml_content)}")
        else:
            st.warning("⚠️ Nenhum XML válido encontrado.")

    if 'zip_id' in st.session_state:
        st.markdown("### 📦 Baixar todos os XMLs em um único ZIP")
        download_url = f"{DJANGO_BACKEND_URL}/download-zip/{st.session_state['zip_id']}/"

        st.markdown(
            f"""
            <a href="{download_url}" target="_blank">
                <button style="background-color:#4CAF50;color:white;padding:10px 20px;border:none;border-radius:5px;cursor:pointer;">
                    📅 Baixar ZIP
                </button>
            </a>
            """,
            unsafe_allow_html=True
        )


# --- TAB 3: Enviar para API ---
with tab3:
    st.markdown("""
    <div class="fade-in">
        <h2><span class="icon">🚀</span>Enviar para API</h2>
        <div class="info-box">
            <p style="font-family: 'Lato', sans-serif; margin: 0;">
                <strong>🎯 Integração:</strong> Envie seus XMLs processados diretamente para o sistema externo. 
                Rápido, seguro e confiável!
            </p>
        </div>
    </div>
    """, unsafe_allow_html=True)

    # A lógica aqui assume que você baixou o ZIP e extraiu os XMLs para algum lugar localmente
    # ou que o Streamlit agora pode fazer requisições para pegar XMLs individuais se o Django os expor.
    # Por simplicidade, para este exemplo, vamos simular que o XML está "disponível" no Streamlit
    # se o status for "Concluído" e "XML Gerado" for "Sim".
    # Em um cenário real, você teria que gerenciar os arquivos XML baixados/extraídos e carregá-los aqui.

    xmls_to_send_info = []
    for idx, info in enumerate(st.session_state.uploaded_files_info):
        if info["XML Gerado"] == "Sim" and info["Status Envio"] != "Enviado com Sucesso":
            # PARA O PROD: Substitua este placeholder pelo carregamento do conteúdo XML real.
            # Ex: Se você salvou os XMLs localmente após baixar o ZIP na TAB 2:
            # xml_file_path_local = XML_DIR / Path(info["Nome do Arquivo"]).with_suffix(".xml").name
            # if xml_file_path_local.exists():
            #     with open(xml_file_path_local, "r", encoding="utf-8") as f:
            #         xml_content = f.read()
            # else:
            #     xml_content = f"<Nfse><Erro>XML local não encontrado para {info['Nome do Arquivo']}</Erro></Nfse>"
            xml_content_placeholder = f"<Nfse><DadosServico><IdentificacaoServico><NomeArquivo>{info['Nome do Arquivo']}</NomeArquivo></IdentificacaoServico></DadosServico></Nfse>"

            xmls_to_send_info.append({
                "Nome do Arquivo": info["Nome do Arquivo"],
                "Caminho": info["Caminho"], # Caminho do PDF original
                "XML Content": xml_content_placeholder, # Substituir por conteúdo XML real
                "Original Index": idx # Usar o índice real no st.session_state.uploaded_files_info
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

                    # Chama a função genérica para interagir com o backend Django para enviar o XML
                    send_response = call_django_backend(
                        endpoint="/send-xml-to-external-api/", # ENDPOINT REAL NO SEU DJANGO para envio de XMLs
                        method="POST",
                        json_data={
                            "xml_content": file_data_to_send["XML Content"], # Conteúdo XML real
                            "file_name": file_data_to_send["Nome do Arquivo"]
                        }
                    )
                    
                    if send_response is None:
                        status_send = "Falha no Envio"
                        details_send = "Erro de comunicação com o backend."
                    else:
                        status_send = send_response.get("status", "Desconhecido") # Assumindo que backend retorna 'status'
                        details_send = send_response.get("message", send_response.get("error", "Sem detalhes.")) # Assumindo 'message' ou 'error'

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

# --- TAB 4: Relatórios ---
with tab4:
    st.markdown("""
    <div class="fade-in">
        <h2><span class="icon">📊</span>Relatórios e Histórico</h2>
        <div class="info-box">
            <p style="font-family: 'Lato', sans-serif; margin: 0;">
                <strong>📈 Analytics:</strong> Acompanhe seu progresso, métricas de sucesso e histórico completo. 
                Dados que ajudam você a crescer!
            </p>
        </div>
    </div>
    """, unsafe_allow_html=True)
    
    if st.session_state.uploaded_files_info:
        df_history = pd.DataFrame(st.session_state.uploaded_files_info)
        
        # Gráfico de pizza para status
        col1, col2 = st.columns(2)
        
        with col1:
            st.markdown("#### 📊 Distribuição de Status")
            status_counts = df_history['Status'].value_counts()
            st.bar_chart(status_counts)
        
        with col2:
            st.markdown("#### ⏱️ Economia de Tempo")
            total_processed = len(df_history[df_history['Status'] == 'Concluído'])
            time_saved = total_processed * 3  # 3 minutos por arquivo
            
            st.markdown(f"""
            <div class="metric-card">
                <div style="text-align: center;">
                    <div style="font-size: 3rem; color: #E63946;">⏰</div>
                    <div style="font-family: 'Poppins', sans-serif; font-weight: 700; font-size: 2.5rem; color: #1D3557;">
                        {time_saved} min
                    </div>
                    <div style="font-family: 'Lato', sans-serif; color: #457B9D;">
                        Tempo Total Economizado
                    </div>
                    <div style="font-family: 'Lato', sans-serif; color: #2D7D32; font-size: 0.9rem; margin-top: 0.5rem;">
                        ≈ R$ {time_saved * 2:.2f} em produtividade
                    </div>
                </div>
            </div>
            """, unsafe_allow_html=True)
        
        st.markdown("---")
        st.markdown("#### 🔍 **Filtros Avançados:**")
        
        col1, col2 = st.columns(2)
        
        with col1:
            status_filter = st.multiselect(
                "📊 **Status de Processamento:**",
                options=df_history['Status'].unique().tolist(),
                default=df_history['Status'].unique().tolist(),
                key="multiselect_history_status"
            )
        
        with col2:
            send_status_filter = st.multiselect(
                "🚀 **Status de Envio:**",
                options=df_history['Status Envio'].unique().tolist(),
                default=df_history['Status Envio'].unique().tolist(),
                key="multiselect_history_send_status"
            )

        filtered_df = df_history[
            (df_history['Status'].isin(status_filter)) &
            (df_history['Status Envio'].isin(send_status_filter))
        ]

        st.markdown("#### 📋 **Histórico Detalhado:**")
        st.dataframe(
            filtered_df[['Nome do Arquivo', 'Status', 'XML Gerado', 'Status Envio', 'Detalhes']],
            use_container_width=True
        )
    else:
        st.info("Nenhum dado de histórico disponível. Faça upload e processe alguns PDFs primeiro.")