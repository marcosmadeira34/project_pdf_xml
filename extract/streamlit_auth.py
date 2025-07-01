import streamlit as st
import requests
import json
from typing import Optional, Dict, Any
import os

# Configurações do backend Django
DJANGO_BACKEND_URL = os.getenv("DJANGO_BACKEND_URL", "http://127.0.0.1:8001")


class StreamlitAuthManager:
    """Gerenciador de autenticação para Streamlit"""
    
    @staticmethod
    def initialize_session_state():
        """Inicializa o estado da sessão para autenticação"""
        if 'authenticated' not in st.session_state:
            st.session_state.authenticated = False
        if 'access_token' not in st.session_state:
            st.session_state.access_token = None
        if 'refresh_token' not in st.session_state:
            st.session_state.refresh_token = None
        if 'user_info' not in st.session_state:
            st.session_state.user_info = None
    
    @staticmethod
    def login(username: str, password: str) -> tuple[bool, str]:
        """
        Realiza login no backend Django
        
        Args:
            username: Nome de usuário
            password: Senha
            
        Returns:
            Tuple (sucesso, mensagem)
        """
        try:
            response = requests.post(
                f"{DJANGO_BACKEND_URL}/auth/login/",
                json={
                    'username': username,
                    'password': password
                },
                timeout=30
            )
            
            if response.status_code == 200:
                data = response.json()
                
                # Armazena tokens e informações do usuário na sessão
                st.session_state.authenticated = True
                st.session_state.access_token = data['tokens']['access_token']
                st.session_state.refresh_token = data['tokens']['refresh_token']
                st.session_state.user_info = data['user']
                
                return True, "Login realizado com sucesso!"
            
            elif response.status_code == 401:
                error_data = response.json()
                return False, error_data.get('error', 'Credenciais inválidas')
            
            else:
                return False, f"Erro no servidor: {response.status_code}"
                
        except requests.exceptions.RequestException as e:
            return False, f"Erro de conexão: {str(e)}"
        except Exception as e:
            return False, f"Erro inesperado: {str(e)}"
    
    @staticmethod
    def logout():
        """Realiza logout e limpa a sessão"""
        try:
            if st.session_state.get('access_token'):
                requests.post(
                    f"{DJANGO_BACKEND_URL}/auth/logout/",
                    headers={
                        'Authorization': f"Bearer {st.session_state.access_token}"
                    },
                    timeout=10
                )
        except:
            pass  # Ignora erros de logout no backend
        
        # Limpa o estado da sessão
        st.session_state.authenticated = False
        st.session_state.access_token = None
        st.session_state.refresh_token = None
        st.session_state.user_info = None
    
    @staticmethod
    def verify_token() -> bool:
        """
        Verifica se o token atual é válido
        
        Returns:
            True se o token é válido, False caso contrário
        """
        if not st.session_state.get('access_token'):
            return False
        
        try:
            response = requests.post(
                f"{DJANGO_BACKEND_URL}/auth/verify/",
                headers={
                    'Authorization': f"Bearer {st.session_state.access_token}"
                },
                timeout=10
            )
            
            return response.status_code == 200
            
        except:
            return False
    
    @staticmethod
    def refresh_token() -> bool:
        """
        Renova o access token usando o refresh token
        
        Returns:
            True se a renovação foi bem-sucedida, False caso contrário
        """
        if not st.session_state.get('refresh_token'):
            return False
        
        try:
            response = requests.post(
                f"{DJANGO_BACKEND_URL}/auth/refresh/",
                json={
                    'refresh_token': st.session_state.refresh_token
                },
                timeout=30
            )
            
            if response.status_code == 200:
                data = response.json()
                st.session_state.access_token = data['tokens']['access_token']
                return True
            
            return False
            
        except:
            return False
    
    @staticmethod
    def ensure_authenticated():
        """
        Garante que o usuário está autenticado, renovando o token se necessário
        
        Returns:
            True se autenticado, False caso contrário
        """
        if not st.session_state.get('authenticated'):
            return False
        
        # Verifica se o token atual é válido
        if StreamlitAuthManager.verify_token():
            return True
        
        # Tenta renovar o token
        if StreamlitAuthManager.refresh_token():
            return True
        
        # Se não conseguiu renovar, faz logout
        StreamlitAuthManager.logout()
        return False
    
    @staticmethod
    def get_auth_headers() -> Dict[str, str]:
        """
        Retorna headers de autenticação para requisições
        
        Returns:
            Dict com headers de autenticação
        """
        if st.session_state.get('access_token'):
            return {
                'Authorization': f"Bearer {st.session_state.access_token}"
            }
        return {}
    
    @staticmethod
    def authenticated_request(method: str, endpoint: str, **kwargs) -> Optional[requests.Response]:
        """
        Faz uma requisição autenticada ao backend Django
        
        Args:
            method: Método HTTP (GET, POST, etc.)
            endpoint: Endpoint da API
            **kwargs: Argumentos adicionais para requests
            
        Returns:
            Response object ou None se não autenticado
        """
        if not StreamlitAuthManager.ensure_authenticated():
            st.error("Sessão expirada. Por favor, faça login novamente.")
            return None
        
        # Adiciona headers de autenticação
        headers = kwargs.get('headers', {})
        headers.update(StreamlitAuthManager.get_auth_headers())
        kwargs['headers'] = headers
        
        try:
            url = f"{DJANGO_BACKEND_URL}{endpoint}"
            response = getattr(requests, method.lower())(url, **kwargs)
            return response
        except Exception as e:
            st.error(f"Erro na requisição: {str(e)}")
            return None


def show_login_page():
    """Exibe a página de login"""
    st.title("🔐 Login - NFS-e Control")
    st.markdown("Entre com suas credenciais para acessar o sistema")
    
    with st.form("login_form"):
        col1, col2, col3 = st.columns([1, 2, 1])
        
        with col2:
            username = st.text_input("👤 Usuário", placeholder="Digite seu usuário")
            password = st.text_input("🔒 Senha", type="password", placeholder="Digite sua senha")
            
            submitted = st.form_submit_button("🚀 Entrar", use_container_width=True)
            
            if submitted:
                if not username or not password:
                    st.error("Por favor, preencha todos os campos.")
                else:
                    with st.spinner("Autenticando..."):
                        success, message = StreamlitAuthManager.login(username, password)
                    
                    if success:
                        st.success(message)
                        st.rerun()
                    else:
                        st.error(message)
    
    # Informações adicionais
    with st.expander("ℹ️ Informações de Acesso"):
        st.markdown("""
        **Sistema de Autenticação JWT**
        
        - Tokens de acesso válidos por 24 horas
        - Renovação automática quando necessário
        - Logout automático em caso de token inválido
        
        **Problemas de Acesso?**
        - Verifique suas credenciais
        - Entre em contato com o administrador do sistema
        """)


def show_user_info():
    """Exibe informações do usuário logado"""
    user_info = st.session_state.get('user_info', {})
    
    with st.sidebar:
        st.markdown("---")
        st.markdown("👤 **Usuário Logado**")
        st.markdown(f"**Nome:** {user_info.get('username', 'N/A')}")
        if user_info.get('first_name') or user_info.get('last_name'):
            st.markdown(f"**Nome Completo:** {user_info.get('first_name', '')} {user_info.get('last_name', '')}")
        st.markdown(f"**Email:** {user_info.get('email', 'N/A')}")
        
        if user_info.get('is_staff'):
            st.markdown("🛡️ **Administrador**")
        
        if st.button("🚪 Sair", use_container_width=True):
            StreamlitAuthManager.logout()
            st.rerun()


def require_auth(func):
    """
    Decorator para páginas que requerem autenticação
    """
    def wrapper(*args, **kwargs):
        StreamlitAuthManager.initialize_session_state()
        
        if not StreamlitAuthManager.ensure_authenticated():
            show_login_page()
            return
        
        show_user_info()
        return func(*args, **kwargs)
    
    return wrapper
