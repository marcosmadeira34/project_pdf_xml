import streamlit as st
import requests
import json
from typing import Dict, List, Optional
import base64
from io import BytesIO
from PIL import Image
import os

DJANGO_BACKEND_URL = os.getenv("DJANGO_BACKEND_URL", "http://127.0.0.1:8001")

class CreditManager:
    """Gerenciador de créditos para Streamlit"""
    
    @staticmethod
    def get_user_credits() -> Optional[Dict]:
        """Busca informações de créditos do usuário"""
        if not st.session_state.get('access_token'):
            return None
        
        try:
            response = requests.post(
                f"{DJANGO_BACKEND_URL}/credits/info/",
                headers={
                    'Authorization': f"Bearer {st.session_state.access_token}"
                },
                timeout=10
            )
            
            if response.status_code == 200:
                return response.json()
            
        except Exception as e:
            st.error(f"Erro ao buscar créditos: {str(e)}")
        
        return None
    
    @staticmethod
    def check_credits_for_files(file_count: int) -> Dict:
        """Verifica se tem créditos suficientes para processar os arquivos"""
        credits_info = CreditManager.get_user_credits()
        
        if not credits_info or not credits_info.get('success'):
            return {
                'has_enough': False,
                'current_balance': 0,
                'required': file_count,
                'missing': file_count,
                'error': 'Erro ao verificar créditos'
            }
        
        current_balance = credits_info['credits']['balance']
        
        return {
            'has_enough': current_balance >= file_count,
            'current_balance': current_balance,
            'required': file_count,
            'missing': max(0, file_count - current_balance),
            'remaining_after': current_balance - file_count
        }
    
    @staticmethod
    def get_credit_packages() -> List[Dict]:
        """Busca pacotes de créditos disponíveis"""
        try:
            response = requests.get(
                f"{DJANGO_BACKEND_URL}/credits/packages/",
                timeout=10
            )
            
            if response.status_code == 200:
                data = response.json()
                return data.get('packages', [])
            
        except Exception as e:
            st.error(f"Erro ao buscar pacotes: {str(e)}")
        
        return []
    
    @staticmethod
    def create_payment_order(package_id: int) -> Optional[Dict]:
        """Cria uma ordem de pagamento PIX"""
        if not st.session_state.get('access_token'):
            return None
        
        try:
            response = requests.post(
                f"{DJANGO_BACKEND_URL}/credits/create-payment/",
                headers={
                    'Authorization': f"Bearer {st.session_state.access_token}",
                    'Content-Type': 'application/json'
                },
                json={'package_id': package_id},
                timeout=30
            )
            
            if response.status_code == 200:
                return response.json()
            else:
                error_data = response.json()
                st.error(f"Erro ao criar pagamento: {error_data.get('error', 'Erro desconhecido')}")
            
        except Exception as e:
            st.error(f"Erro ao criar pagamento: {str(e)}")
        
        return None
    
    @staticmethod
    def confirm_payment(payment_order_id: str, payment_proof: str = "") -> bool:
        """Confirma pagamento manual"""
        if not st.session_state.get('access_token'):
            return False
        
        try:
            response = requests.post(
                f"{DJANGO_BACKEND_URL}/credits/confirm-payment/",
                headers={
                    'Authorization': f"Bearer {st.session_state.access_token}",
                    'Content-Type': 'application/json'
                },
                json={
                    'payment_order_id': payment_order_id,
                    'payment_proof': payment_proof
                },
                timeout=30
            )
            
            if response.status_code == 200:
                data = response.json()
                st.success(f"✅ {data.get('message', 'Pagamento confirmado!')}")
                st.balloons()
                return True
            else:
                error_data = response.json()
                st.error(f"❌ {error_data.get('error', 'Erro ao confirmar pagamento')}")
            
        except Exception as e:
            st.error(f"Erro ao confirmar pagamento: {str(e)}")
        
        return False


def show_credits_sidebar():
    """Mostra informações de créditos na sidebar"""
    with st.sidebar:
        st.markdown("---")
        st.markdown("### 💰 Seus Créditos")
        
        # Busca informações de créditos
        credits_info = CreditManager.get_user_credits()
        
        if credits_info and credits_info.get('success'):
            credits = credits_info['credits']
            
            # Card de créditos
            st.markdown(f"""
            <div style="background: linear-gradient(135deg, #E63946, #ff4757); padding: 1rem; border-radius: 10px; color: white; text-align: center; margin-bottom: 1rem;">
                <div style="font-size: 2rem; margin-bottom: 0.5rem;">💎</div>
                <div style="font-size: 1.5rem; font-weight: bold;">{credits['balance']}</div>
                <div style="font-size: 0.9rem; opacity: 0.9;">Créditos Disponíveis</div>
            </div>
            """, unsafe_allow_html=True)
            
            # Botão para comprar mais créditos
            if st.button("🛒 Comprar Créditos", use_container_width=True):
                st.session_state.show_credit_store = True
                st.rerun()
            
            # Estatísticas em expander
            with st.expander("📊 Estatísticas"):
                st.metric("Total Comprado", credits['total_purchased'])
                st.metric("Total Usado", credits['total_used'])
                
                # Últimas transações
                if credits_info.get('recent_transactions'):
                    st.markdown("**Últimas Transações:**")
                    for trans in credits_info['recent_transactions'][:3]:
                        icon = "🟢" if trans['amount'] > 0 else "🔴"
                        st.markdown(f"{icon} {trans['description']} ({trans['amount']:+d})")
        else:
            st.error("❌ Erro ao carregar créditos")
            if st.button("🛒 Comprar Créditos", use_container_width=True):
                st.session_state.show_credit_store = True
                st.rerun()


def show_credit_store():
    """Mostra a loja de créditos"""
    st.markdown("""
    <div style="text-align: center; padding: 2rem; background: linear-gradient(135deg, #F1FAEE, white); border-radius: 15px; margin-bottom: 2rem;">
        <h1 style="color: #1D3557; margin-bottom: 0.5rem;">🛒 Loja de Créditos</h1>
        <p style="color: #457B9D;">Escolha o pacote ideal para suas necessidades</p>
    </div>
    """, unsafe_allow_html=True)
    
    # Busca pacotes disponíveis
    packages = CreditManager.get_credit_packages()
    
    if not packages:
        st.error("❌ Erro ao carregar pacotes de créditos")
        return
    
    # Mostra pacotes em colunas
    cols = st.columns(min(len(packages), 3))
    
    for i, package in enumerate(packages):
        with cols[i % 3]:
            # Destaque para pacote popular
            popular_badge = "🌟 MAIS POPULAR" if package.get('is_popular') else ""
            
            st.markdown(f"""
            <div style="background: white; padding: 1.5rem; border-radius: 15px; border: {'3px solid #E63946' if package.get('is_popular') else '1px solid #ddd'}; text-align: center; margin-bottom: 1rem; box-shadow: 0 4px 15px rgba(0,0,0,0.1);">
                <div style="color: #E63946; font-weight: bold; margin-bottom: 0.5rem;">{popular_badge}</div>
                <h3 style="color: #1D3557; margin-bottom: 1rem;">{package['name']}</h3>
                
                <div style="font-size: 2.5rem; color: #E63946; margin-bottom: 0.5rem;">{package['total_credits']}</div>
                <div style="color: #457B9D; margin-bottom: 1rem;">créditos</div>
                
                <div style="background: #F1FAEE; padding: 0.5rem; border-radius: 8px; margin-bottom: 1rem;">
                    <div style="font-size: 1.5rem; font-weight: bold; color: #1D3557;">R$ {package['price']:.2f}</div>
                    <div style="font-size: 0.8rem; color: #457B9D;">R$ {package['price_per_credit']:.2f} por crédito</div>
                </div>
                
                {f'<div style="color: #2D7D32; font-size: 0.9rem; margin-bottom: 1rem;">+{package["bonus_credits"]} créditos bônus!</div>' if package['bonus_credits'] > 0 else ''}
            </div>
            """, unsafe_allow_html=True)
            
            if st.button(f"💳 Comprar {package['name']}", key=f"buy_{package['id']}", use_container_width=True):
                # Cria ordem de pagamento
                payment_order = CreditManager.create_payment_order(package['id'])
                
                if payment_order and payment_order.get('success'):
                    st.session_state.current_payment_order = payment_order['payment_order']
                    st.session_state.show_payment_details = True
                    st.rerun()
    
    # Botão para voltar
    if st.button("⬅️ Voltar ao Dashboard", use_container_width=True):
        st.session_state.show_credit_store = False
        st.rerun()


def show_payment_details():
    """Mostra detalhes do pagamento PIX"""
    payment_order = st.session_state.get('current_payment_order')
    
    if not payment_order:
        st.error("❌ Erro: Ordem de pagamento não encontrada")
        return
    
    st.markdown("""
    <div style="text-align: center; padding: 2rem; background: linear-gradient(135deg, #F1FAEE, white); border-radius: 15px; margin-bottom: 2rem;">
        <h1 style="color: #1D3557; margin-bottom: 0.5rem;">💳 Finalizar Pagamento</h1>
        <p style="color: #457B9D;">Use o PIX abaixo para completar sua compra</p>
    </div>
    """, unsafe_allow_html=True)
    
    col1, col2 = st.columns([1, 1])
    
    with col1:
        st.markdown("### 📋 Detalhes do Pedido")
        st.info(f"**Créditos:** {payment_order['credits_amount']}")
        st.info(f"**Valor:** R$ {payment_order['price']:.2f}")
        st.info(f"**ID do Pedido:** {payment_order['id'][:8]}...")
        
        # Timer de expiração
        import datetime as dt
        expires_at = dt.datetime.fromisoformat(payment_order['expires_at'].replace('Z', '+00:00'))
        now = dt.datetime.now(dt.timezone.utc)
        time_left = expires_at - now
        
        if time_left.total_seconds() > 0:
            minutes_left = int(time_left.total_seconds() // 60)
            st.warning(f"⏰ Expira em {minutes_left} minutos")
        else:
            st.error("❌ PIX expirado")
            return
    
    with col2:
        st.markdown("### 📱 QR Code PIX")
        
        # Mostra QR Code
        if payment_order.get('qr_code'):
            try:
                qr_image = Image.open(BytesIO(base64.b64decode(payment_order['qr_code'])))
                st.image(qr_image, width=200)
            except Exception as e:
                st.error(f"Erro ao carregar QR Code: {str(e)}")
        
        # Código PIX copiável
        st.markdown("### 📝 Código PIX")
        st.code(payment_order.get('pix_code', 'Código não disponível'), language='text')
        
        # Instruções
        st.markdown("""
        **📋 Como pagar:**
        1. Abra seu app do banco
        2. Escaneie o QR Code ou copie o código PIX
        3. Confirme o pagamento
        4. Clique em "Confirmar Pagamento" abaixo
        """)
    
    st.markdown("---")
    
    # Confirmação de pagamento
    col1, col2, col3 = st.columns([1, 1, 1])
    
    with col2:
        if st.button("✅ CONFIRMAR PAGAMENTO", use_container_width=True, type="primary"):
            success = CreditManager.confirm_payment(payment_order['id'])
            
            if success:
                # Limpa estado do pagamento
                if 'current_payment_order' in st.session_state:
                    del st.session_state.current_payment_order
                if 'show_payment_details' in st.session_state:
                    del st.session_state.show_payment_details
                if 'show_credit_store' in st.session_state:
                    del st.session_state.show_credit_store
                
                st.rerun()
    
    # Botões de navegação
    col1, col2 = st.columns(2)
    
    with col1:
        if st.button("⬅️ Voltar à Loja", use_container_width=True):
            st.session_state.show_payment_details = False
            st.rerun()
    
    with col2:
        if st.button("🏠 Voltar ao Dashboard", use_container_width=True):
            # Limpa todos os estados da loja
            for key in ['show_credit_store', 'show_payment_details', 'current_payment_order']:
                if key in st.session_state:
                    del st.session_state[key]
            st.rerun()