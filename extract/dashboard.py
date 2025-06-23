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
import os # Importar para acessar variáveis de ambiente

# --- Suas importações existentes ---
from services import XMLGenerator, DocumentAIProcessor


# Configurar logging (opcional, mas bom para depuração)
logger = logging.getLogger(__name__)
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')


# --- Variáveis de Ambiente para DocumentAIProcessor ---
PROJECT_ID = os.getenv("PROJECT_ID")
LOCATION = os.getenv("LOCATION")
PROCESSOR_ID = os.getenv("PROCESSOR_ID")

# --- Instância da sua classe XMLGenerator (criada uma vez) ---
try:
    xml_generator_instance = XMLGenerator()
    st.session_state['xml_generator_ready'] = True
except Exception as e:
    st.error(f"Erro ao inicializar XMLGenerator: {e}. Verifique se as dependências estão corretas.")
    st.session_state['xml_generator_ready'] = False
    xml_generator_instance = None # Define como None se a inicialização falhar

# --- Instância da sua classe DocumentAIProcessor (criada uma vez) ---
try:
    processor_instance = DocumentAIProcessor()
    st.session_state['doc_ai_processor_ready'] = True
except Exception as e:
    st.error(f"Erro ao inicializar DocumentAIProcessor: {e}. Verifique se as dependências estão corretas.")
    st.session_state['doc_ai_processor_ready'] = False
    processor_instance = None # Define como None se a inicialização falhar


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


# --- NOVA FUNÇÃO SÍNCRONA PARA PROCESSAR UM ÚNICO PDF ---
def process_single_pdf_for_xml(pdf_path: Path, doc_ai_processor: DocumentAIProcessor, xml_gen: XMLGenerator) -> tuple[str, str]:
    """
    Processa um único PDF para extrair dados e gerar XML.
    Retorna o status ("Concluído" ou "Erro") e os detalhes (conteúdo XML ou mensagem de erro).
    """
    if not (st.session_state.get('doc_ai_processor_ready', False) and st.session_state.get('xml_generator_ready', False)):
        return "Erro", "Processadores DocumentAI ou XML não inicializados corretamente."

    if not PROJECT_ID or not LOCATION or not PROCESSOR_ID:
        return "Erro", "Variáveis de ambiente PROJECT_ID, LOCATION ou PROCESSOR_ID não definidas."

    try:
        # Ler os bytes do PDF
        with open(pdf_path, "rb") as f:
            pdf_bytes = f.read()

        logger.info(f"Processando PDF com DocumentAI: {pdf_path.name}")
        document_json = doc_ai_processor.processar_pdf(PROJECT_ID, LOCATION, PROCESSOR_ID, pdf_bytes)
        
        logger.info(f"Mapeando campos do JSON: {pdf_path.name}")
        dados_extraidos = doc_ai_processor.mapear_campos(document_json)
        
        logger.info(f"Gerando XML ABRASF para: {pdf_path.name}")
        xml_content = xml_gen.gerar_xml_abrasf(dados_extraidos)

        # Salva o XML gerado no diretório de XMLs
        xml_file_path = XML_DIR / pdf_path.with_suffix(".xml").name
        with open(xml_file_path, "w", encoding="utf-8") as f:
            f.write(xml_content)

        logger.info(f"XML gerado e salvo para: {pdf_path.name}")
        return "Concluído", xml_content

    except Exception as e:
        logger.error(f"Erro no processamento de {pdf_path.name}: {e}", exc_info=True)
        return "Erro", f"Falha no processamento: {str(e)}"

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
        df_to_process = df_files[~df_files['Status'].isin(['Concluído', 'Erro']) | (df_files['Status'] == 'Erro')]

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
                    st.info("Iniciando conversão...")
                    progress_bar = st.progress(0)
                    for i, idx in enumerate(selected_files_indices):
                        file_info = st.session_state.uploaded_files_info[idx]
                        if file_info["Status"] != "Concluído":
                            # --- CHAME A NOVA FUNÇÃO SÍNCRONA AQUI ---
                            status, details = process_single_pdf_for_xml(
                                Path(file_info["Caminho"]), 
                                processor_instance, 
                                xml_generator_instance
                            )
                            
                            file_info["Status"] = status
                            file_info["Detalhes"] = details
                            if status == "Concluído":
                                file_info["XML Gerado"] = "Sim"
                            else:
                                file_info["XML Gerado"] = "Não"
                            
                            progress_bar.progress((i + 1) / len(selected_files_indices))
                            time.sleep(0.1)
                    progress_bar.empty()
                    st.success("Processo de conversão concluído!")
                    st.rerun()

        st.subheader("Status dos PDFs Carregados:")
        st.dataframe(df_files[['Nome do Arquivo', 'Status', 'XML Gerado', 'Status Envio']], use_container_width=True)

        pdfs_ready = [info for info in st.session_state.uploaded_files_info if Path(info["Caminho"]).exists()]
        if pdfs_ready:
            selected_pdf_name = st.selectbox(
                "Selecione um PDF para visualizar e revisar dados:",
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
                    st.markdown(f"**Dados Extraídos / XML Gerado:**")
                    if selected_pdf_info["Status"] == "Concluído":
                        st.code(selected_pdf_info["Detalhes"], language="xml")
                    elif selected_pdf_info["Status"] == "Erro":
                        st.error(f"Erro na conversão: {selected_pdf_info['Detalhes']}")
                    else:
                        st.info("Aguardando conversão ou processamento.")
        else:
            st.info("Nenhum PDF disponível para visualização.")

# --- TAB 3: Enviar para API ---
with tab3:
    st.header("Passo 3: Enviar XMLs para a API")
    st.markdown("Selecione os XMLs que já foram gerados e envie-os para a API de integração.")

    xmls_to_send = [
        info for info in st.session_state.uploaded_files_info
        if info["XML Gerado"] == "Sim" and info["Status Envio"] != "Enviado com Sucesso"
    ]

    if not xmls_to_send:
        st.info("Nenhum XML pronto para envio ou todos já foram enviados.")
    else:
        df_xmls_to_send = pd.DataFrame(xmls_to_send)

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
                st.info("Iniciando envio para a API...")
                progress_bar_send = st.progress(0)
                for i, idx in enumerate(selected_xml_indices):
                    file_info = xmls_to_send[i]
                    original_idx = next(j for j, item in enumerate(st.session_state.uploaded_files_info) if item["Nome do Arquivo"] == file_info["Nome do Arquivo"])

                    st.session_state.uploaded_files_info[original_idx]["Status Envio"] = "Enviando..."
                    progress_bar_send.progress((i + 1) / len(selected_xml_indices))

                    xml_file_path = XML_DIR / Path(file_info["Caminho"]).with_suffix(".xml").name
                    status_send, details_send = simulate_api_send(xml_file_path)
                    
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