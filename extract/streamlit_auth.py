import streamlit as st
import requests
import json
from typing import Optional, Dict, Any
import os
import time

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
    """
    Exibe a página de login com identidade visual
    """
    # CSS específico para login
    st.markdown("""
    <style>
    @import url('https://fonts.googleapis.com/css2?family=Poppins:wght@300;400;600;700&family=Lato:wght@300;400;700&display=swap');
    
    .login-container {
        max-width: 400px;
        margin: 0 auto;
        padding: 2rem;
        background: linear-gradient(135deg, #ffffff, #F1FAEE);
        border-radius: 20px;
        box-shadow: 0 20px 60px rgba(29, 53, 87, 0.1);
        text-align: center;
        margin-top: 5rem;
    }
    
    .login-header {
        margin-bottom: 2rem;
    }
    
    .login-mascot {
        font-size: 5rem;
        animation: pulse 2s infinite;
        margin-bottom: 1rem;
    }
    
    @keyframes pulse {
        0%, 100% { transform: scale(1); }
        50% { transform: scale(1.1); }
    }
    
    .login-title {
        font-family: 'Poppins', sans-serif;
        font-weight: 700;
        font-size: 2.5rem;
        color: #1D3557;
        margin: 0;
        background: linear-gradient(45deg, #1D3557, #E63946);
        -webkit-background-clip: text;
        -webkit-text-fill-color: transparent;
        background-clip: text;
                text-align: center;
        margin-top: 0.5rem;
                animation: fadeIn 1s ease-in-out;
    }
    
    .login-subtitle {
        font-family: 'Lato', sans-serif;
        color: #457B9D;
        font-size: 1.1rem;
        margin-top: 0.5rem;
    }
    
    .login-form {
        margin-top: 2rem;
    }
    
    .stTextInput > div > div > input {
        border-radius: 15px !important;
        border: 2px solid #F1FAEE !important;
        font-family: 'Lato', sans-serif !important;
        padding: 1rem !important;
        font-size: 1rem !important;
        transition: all 0.3s ease !important;
    }
    
    .stTextInput > div > div > input:focus {
        border-color: #E63946 !important;
        box-shadow: 0 0 15px rgba(230, 57, 70, 0.2) !important;
    }
    
    .login-button {
        background: linear-gradient(45deg, #E63946, #ff4757) !important;
        color: white !important;
        border: none !important;
        border-radius: 25px !important;
        font-family: 'Poppins', sans-serif !important;
        font-weight: 600 !important;
        padding: 0.75rem 3rem !important;
        font-size: 1.1rem !important;
        margin-top: 1rem !important;
        transition: all 0.3s ease !important;
        box-shadow: 0 6px 20px rgba(230, 57, 70, 0.3) !important;
        width: 100% !important;
    }
    
    .login-button:hover {
        transform: translateY(-2px) !important;
        box-shadow: 0 8px 25px rgba(230, 57, 70, 0.4) !important;
    }
    
    .login-footer {
        margin-top: 2rem;
        font-family: 'Lato', sans-serif;
        color: #457B9D;
        font-size: 0.9rem;
    }
    
    .demo-info {
        background: linear-gradient(135deg, #F1FAEE, white);
        padding: 1.5rem;
        border-radius: 15px;
        margin-top: 2rem;
        border: 1px solid rgba(230, 57, 70, 0.1);
    }
    
    .demo-info h4 {
        color: #1D3557;
        font-family: 'Poppins', sans-serif;
        font-weight: 600;
        margin-bottom: 1rem;
    }
    
    .demo-credentials {
        background: white;
        padding: 1rem;
        border-radius: 10px;
        border-left: 4px solid #E63946;
        margin: 0.5rem 0;
        font-family: 'Lato', sans-serif;
        color: #1D3557;
        font-size: 0.9rem;
    }
    </style>
    """, unsafe_allow_html=True)
    
    # Container principal de login
    st.markdown("""
    <div class="">
        <h1 class="login-title">LoveNFSE</h1>
    </div>
    """, unsafe_allow_html=True)
    
    # Formulário de login centralizado
    col1, col2, col3 = st.columns([1, 2, 1])
    
    with col2:
        with st.form("login_form", clear_on_submit=False):
            st.markdown("### Acessao ao Sistema")
            
            username = st.text_input(
                "👤 Usuário:",
                placeholder="Digite seu usuário",
                key="login_username"
            )
            
            password = st.text_input(
                "🔑 Senha:",
                type="password",
                placeholder="Digite sua senha",
                key="login_password"
            )
            
            submitted = st.form_submit_button(
                "🚀 ENTRAR NO SISTEMA",
                use_container_width=True
            )
            
            if submitted:
                if username and password:
                    with st.spinner("🔍 Verificando credenciais..."):
                        success, message = StreamlitAuthManager.login(username, password)
                    
                    if success:
                        st.success(f"✅ {message}")
                        st.balloons()
                        time.sleep(1)
                        st.rerun()
                    else:
                        st.error(f"❌ {message}")
                else:
                    st.warning("⚠️ Por favor, preencha usuário e senha.")
        
        # Informações de demonstração
        # st.markdown("""
        # <div class="demo-info">
        #     <h4>🎯 Demonstração</h4>
        #     <div class="demo-credentials">
        #         <strong>Usuário:</strong> admin<br>
        #         <strong>Senha:</strong> sua_senha_admin
        #     </div>
        #     <div style="font-size: 0.8rem; color: #457B9D; margin-top: 1rem;">
        #         💡 Use as credenciais acima para testar o sistema
        #     </div>
        # </div>
        # """, unsafe_allow_html=True)
    
    # Footer da página de login
    st.markdown("""
    <div style="text-align: center; margin-top: 3rem; color: #457B9D; font-family: 'Lato', sans-serif;">
        <div style="font-size: 1.5rem; margin-bottom: 0.5rem;"></div>
        <div>Transformando processos em experiências incríveis</div>
        <div style="font-size: 0.8rem; margin-top: 0.5rem; opacity: 0.7;">
            © 2025 NFS-e LOVE • Feito com amor e tecnologia
        </div>
    </div>
    """, unsafe_allow_html=True)


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
