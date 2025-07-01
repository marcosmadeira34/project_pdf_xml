#!/usr/bin/env python3
"""
Script de teste para o sistema de autenticação JWT
Execute este script para testar todos os endpoints de autenticação
"""

import requests
import json
import time
import sys
import os

# Configurações
DJANGO_URL = "http://127.0.0.1:8001"
TEST_USERNAME = "admin"  # Altere conforme necessário
TEST_PASSWORD = "admin123"  # Altere conforme necessário

class AuthTester:
    def __init__(self):
        self.access_token = None
        self.refresh_token = None
        self.base_url = DJANGO_URL
    
    def print_status(self, message, success=True):
        """Imprime status colorido"""
        color = "\033[92m" if success else "\033[91m"  # Verde ou Vermelho
        reset = "\033[0m"
        status = "✓" if success else "✗"
        print(f"{color}{status} {message}{reset}")
    
    def test_login(self):
        """Testa o endpoint de login"""
        print("\n" + "="*50)
        print("🔑 TESTANDO LOGIN")
        print("="*50)
        
        try:
            response = requests.post(
                f"{self.base_url}/extract/auth/login/",
                json={
                    "username": TEST_USERNAME,
                    "password": TEST_PASSWORD
                },
                timeout=10
            )
            
            if response.status_code == 200:
                data = response.json()
                self.access_token = data['tokens']['access_token']
                self.refresh_token = data['tokens']['refresh_token']
                
                self.print_status(f"Login realizado com sucesso!")
                self.print_status(f"Usuário: {data['user']['username']}")
                self.print_status(f"Email: {data['user']['email']}")
                self.print_status(f"Access Token: {self.access_token[:50]}...")
                self.print_status(f"Refresh Token: {self.refresh_token[:50]}...")
                return True
            else:
                error_data = response.json()
                self.print_status(f"Erro no login: {error_data.get('error', 'Erro desconhecido')}", False)
                return False
                
        except requests.exceptions.RequestException as e:
            self.print_status(f"Erro de conexão: {str(e)}", False)
            return False
    
    def test_verify_token(self):
        """Testa a verificação de token"""
        print("\n" + "="*50)
        print("🔍 TESTANDO VERIFICAÇÃO DE TOKEN")
        print("="*50)
        
        if not self.access_token:
            self.print_status("Nenhum token disponível para verificar", False)
            return False
        
        try:
            response = requests.post(
                f"{self.base_url}/extract/auth/verify/",
                headers={
                    "Authorization": f"Bearer {self.access_token}"
                },
                timeout=10
            )
            
            if response.status_code == 200:
                data = response.json()
                self.print_status("Token verificado com sucesso!")
                self.print_status(f"Token válido para usuário: {data['user']['username']}")
                return True
            else:
                error_data = response.json()
                self.print_status(f"Erro na verificação: {error_data.get('error', 'Token inválido')}", False)
                return False
                
        except requests.exceptions.RequestException as e:
            self.print_status(f"Erro de conexão: {str(e)}", False)
            return False
    
    def test_user_info(self):
        """Testa endpoint de informações do usuário"""
        print("\n" + "="*50)
        print("👤 TESTANDO INFORMAÇÕES DO USUÁRIO")
        print("="*50)
        
        if not self.access_token:
            self.print_status("Nenhum token disponível", False)
            return False
        
        try:
            response = requests.get(
                f"{self.base_url}/extract/auth/user-info/",
                headers={
                    "Authorization": f"Bearer {self.access_token}"
                },
                timeout=10
            )
            
            if response.status_code == 200:
                data = response.json()
                user = data['user']
                self.print_status("Informações do usuário obtidas com sucesso!")
                self.print_status(f"ID: {user['id']}")
                self.print_status(f"Username: {user['username']}")
                self.print_status(f"Email: {user['email']}")
                self.print_status(f"Nome: {user['first_name']} {user['last_name']}")
                self.print_status(f"Staff: {user['is_staff']}")
                self.print_status(f"Superuser: {user['is_superuser']}")
                return True
            else:
                error_data = response.json()
                self.print_status(f"Erro ao obter informações: {error_data.get('error', 'Erro desconhecido')}", False)
                return False
                
        except requests.exceptions.RequestException as e:
            self.print_status(f"Erro de conexão: {str(e)}", False)
            return False
    
    def test_refresh_token(self):
        """Testa renovação de token"""
        print("\n" + "="*50)
        print("🔄 TESTANDO RENOVAÇÃO DE TOKEN")
        print("="*50)
        
        if not self.refresh_token:
            self.print_status("Nenhum refresh token disponível", False)
            return False
        
        old_access_token = self.access_token
        
        try:
            response = requests.post(
                f"{self.base_url}/extract/auth/refresh/",
                json={
                    "refresh_token": self.refresh_token
                },
                timeout=10
            )
            
            if response.status_code == 200:
                data = response.json()
                self.access_token = data['tokens']['access_token']
                
                self.print_status("Token renovado com sucesso!")
                self.print_status(f"Novo Access Token: {self.access_token[:50]}...")
                self.print_status(f"Token mudou: {old_access_token != self.access_token}")
                return True
            else:
                error_data = response.json()
                self.print_status(f"Erro na renovação: {error_data.get('error', 'Erro desconhecido')}", False)
                return False
                
        except requests.exceptions.RequestException as e:
            self.print_status(f"Erro de conexão: {str(e)}", False)
            return False
    
    def test_protected_endpoint(self):
        """Testa um endpoint protegido"""
        print("\n" + "="*50)
        print("🔒 TESTANDO ENDPOINT PROTEGIDO")
        print("="*50)
        
        if not self.access_token:
            self.print_status("Nenhum token disponível", False)
            return False
        
        try:
            # Testa endpoint de upload (sem arquivos, só para testar autenticação)
            response = requests.post(
                f"{self.base_url}/extract/upload-e-processar-pdf/",
                headers={
                    "Authorization": f"Bearer {self.access_token}"
                },
                timeout=10
            )
            
            # Esperamos erro 400 (sem arquivos), mas não 401 (não autorizado)
            if response.status_code != 401:
                self.print_status("Endpoint protegido acessível com token válido!")
                if response.status_code == 400:
                    self.print_status("Erro 400 esperado (sem arquivos enviados)")
                return True
            else:
                self.print_status("Endpoint protegido negou acesso - token inválido", False)
                return False
                
        except requests.exceptions.RequestException as e:
            self.print_status(f"Erro de conexão: {str(e)}", False)
            return False
    
    def test_logout(self):
        """Testa logout"""
        print("\n" + "="*50)
        print("🚪 TESTANDO LOGOUT")
        print("="*50)
        
        if not self.access_token:
            self.print_status("Nenhum token disponível para logout", False)
            return False
        
        try:
            response = requests.post(
                f"{self.base_url}/extract/auth/logout/",
                headers={
                    "Authorization": f"Bearer {self.access_token}"
                },
                timeout=10
            )
            
            if response.status_code == 200:
                self.print_status("Logout realizado com sucesso!")
                return True
            else:
                error_data = response.json()
                self.print_status(f"Erro no logout: {error_data.get('error', 'Erro desconhecido')}", False)
                return False
                
        except requests.exceptions.RequestException as e:
            self.print_status(f"Erro de conexão: {str(e)}", False)
            return False
    
    def test_invalid_token(self):
        """Testa comportamento com token inválido"""
        print("\n" + "="*50)
        print("🚫 TESTANDO TOKEN INVÁLIDO")
        print("="*50)
        
        fake_token = "eyJ0eXAiOiJKV1QiLCJhbGciOiJIUzI1NiJ9.invalid_token"
        
        try:
            response = requests.post(
                f"{self.base_url}/extract/auth/verify/",
                headers={
                    "Authorization": f"Bearer {fake_token}"
                },
                timeout=10
            )
            
            if response.status_code == 401:
                self.print_status("Token inválido rejeitado corretamente!")
                return True
            else:
                self.print_status("Sistema aceitou token inválido - PROBLEMA DE SEGURANÇA!", False)
                return False
                
        except requests.exceptions.RequestException as e:
            self.print_status(f"Erro de conexão: {str(e)}", False)
            return False
    
    def run_all_tests(self):
        """Executa todos os testes"""
        print("🧪 INICIANDO TESTES DO SISTEMA DE AUTENTICAÇÃO JWT")
        print("="*60)
        print(f"🎯 Testando servidor: {self.base_url}")
        print(f"👤 Usuário de teste: {TEST_USERNAME}")
        
        results = []
        
        # 1. Teste de login
        results.append(("Login", self.test_login()))
        
        # 2. Teste de verificação de token
        results.append(("Verificação de Token", self.test_verify_token()))
        
        # 3. Teste de informações do usuário
        results.append(("Informações do Usuário", self.test_user_info()))
        
        # 4. Teste de renovação de token
        results.append(("Renovação de Token", self.test_refresh_token()))
        
        # 5. Teste de endpoint protegido
        results.append(("Endpoint Protegido", self.test_protected_endpoint()))
        
        # 6. Teste de token inválido
        results.append(("Token Inválido", self.test_invalid_token()))
        
        # 7. Teste de logout
        results.append(("Logout", self.test_logout()))
        
        # Resumo dos resultados
        print("\n" + "="*60)
        print("📊 RESUMO DOS TESTES")
        print("="*60)
        
        passed = 0
        failed = 0
        
        for test_name, result in results:
            if result:
                self.print_status(f"{test_name}: PASSOU")
                passed += 1
            else:
                self.print_status(f"{test_name}: FALHOU", False)
                failed += 1
        
        print("\n" + "="*60)
        print(f"✅ Testes Passaram: {passed}")
        print(f"❌ Testes Falharam: {failed}")
        print(f"📈 Taxa de Sucesso: {(passed/(passed+failed)*100):.1f}%")
        
        if failed == 0:
            print("\n🎉 TODOS OS TESTES PASSARAM! Sistema de autenticação funcionando corretamente.")
        else:
            print(f"\n⚠️  {failed} teste(s) falharam. Verifique os logs acima para detalhes.")
        
        return failed == 0


def check_server_running():
    """Verifica se o servidor Django está rodando"""
    try:
        response = requests.get(f"{DJANGO_URL}/extract/", timeout=5)
        return True
    except requests.exceptions.RequestException:
        return False


if __name__ == "__main__":
    print("🚀 TESTE DO SISTEMA DE AUTENTICAÇÃO JWT - NFS-e Control")
    print("="*60)
    
    # Verifica se o servidor está rodando
    if not check_server_running():
        print(f"❌ Servidor Django não está acessível em {DJANGO_URL}")
        print("📝 Para iniciar o servidor, execute:")
        print(f"   cd /home/marcosmadeira/nfse-abrasf-project")
        print(f"   python manage.py runserver 8001")
        sys.exit(1)
    
    print(f"✅ Servidor Django está rodando em {DJANGO_URL}")
    
    # Executa os testes
    tester = AuthTester()
    success = tester.run_all_tests()
    
    if success:
        print("\n🎯 PRÓXIMOS PASSOS:")
        print("1. Inicie o Streamlit: streamlit run extract/dashboard.py")
        print("2. Acesse: http://localhost:8501")
        print("3. Faça login com suas credenciais Django")
        print("4. Use a aplicação normalmente!")
    
    sys.exit(0 if success else 1)
