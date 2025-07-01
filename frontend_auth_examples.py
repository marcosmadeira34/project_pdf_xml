"""
Exemplo de como usar a autenticação JWT no frontend (JavaScript/React/Angular)
"""

# Exemplo em JavaScript puro para demonstração
js_example = """
// auth.js - Sistema de Autenticação Frontend

class AuthService {
    constructor(baseURL = 'http://127.0.0.1:8001') {
        this.baseURL = baseURL;
        this.accessToken = localStorage.getItem('access_token');
        this.refreshToken = localStorage.getItem('refresh_token');
    }

    // Login do usuário
    async login(username, password) {
        try {
            const response = await fetch(`${this.baseURL}/extract/auth/login/`, {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                },
                body: JSON.stringify({ username, password })
            });

            const data = await response.json();

            if (response.ok) {
                this.accessToken = data.tokens.access_token;
                this.refreshToken = data.tokens.refresh_token;
                
                // Armazena tokens no localStorage
                localStorage.setItem('access_token', this.accessToken);
                localStorage.setItem('refresh_token', this.refreshToken);
                localStorage.setItem('user_info', JSON.stringify(data.user));

                return { success: true, user: data.user };
            } else {
                return { success: false, error: data.error };
            }
        } catch (error) {
            return { success: false, error: 'Erro de conexão' };
        }
    }

    // Logout do usuário
    async logout() {
        try {
            if (this.accessToken) {
                await fetch(`${this.baseURL}/extract/auth/logout/`, {
                    method: 'POST',
                    headers: {
                        'Authorization': `Bearer ${this.accessToken}`,
                        'Content-Type': 'application/json',
                    }
                });
            }
        } catch (error) {
            console.error('Erro no logout:', error);
        } finally {
            // Limpa dados locais sempre
            this.accessToken = null;
            this.refreshToken = null;
            localStorage.removeItem('access_token');
            localStorage.removeItem('refresh_token');
            localStorage.removeItem('user_info');
        }
    }

    // Verifica se o token é válido
    async verifyToken() {
        if (!this.accessToken) return false;

        try {
            const response = await fetch(`${this.baseURL}/extract/auth/verify/`, {
                method: 'POST',
                headers: {
                    'Authorization': `Bearer ${this.accessToken}`,
                    'Content-Type': 'application/json',
                }
            });

            return response.ok;
        } catch (error) {
            return false;
        }
    }

    // Renova o access token
    async refreshAccessToken() {
        if (!this.refreshToken) return false;

        try {
            const response = await fetch(`${this.baseURL}/extract/auth/refresh/`, {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                },
                body: JSON.stringify({ refresh_token: this.refreshToken })
            });

            if (response.ok) {
                const data = await response.json();
                this.accessToken = data.tokens.access_token;
                localStorage.setItem('access_token', this.accessToken);
                return true;
            }

            return false;
        } catch (error) {
            return false;
        }
    }

    // Faz requisições autenticadas
    async authenticatedRequest(url, options = {}) {
        // Garante que o token está válido
        if (!await this.ensureValidToken()) {
            throw new Error('Token inválido ou expirado');
        }

        // Adiciona headers de autenticação
        const headers = {
            'Authorization': `Bearer ${this.accessToken}`,
            'Content-Type': 'application/json',
            ...options.headers
        };

        return fetch(url, { ...options, headers });
    }

    // Garante que o token é válido, renovando se necessário
    async ensureValidToken() {
        if (!this.accessToken) return false;

        // Verifica se o token atual é válido
        if (await this.verifyToken()) {
            return true;
        }

        // Tenta renovar o token
        return await this.refreshAccessToken();
    }

    // Verifica se o usuário está logado
    isAuthenticated() {
        return !!this.accessToken;
    }

    // Obtém informações do usuário
    getUserInfo() {
        const userInfo = localStorage.getItem('user_info');
        return userInfo ? JSON.parse(userInfo) : null;
    }
}

// Exemplo de uso
const auth = new AuthService();

// Login
document.getElementById('loginForm').addEventListener('submit', async (e) => {
    e.preventDefault();
    
    const username = document.getElementById('username').value;
    const password = document.getElementById('password').value;
    
    const result = await auth.login(username, password);
    
    if (result.success) {
        console.log('Login realizado com sucesso!', result.user);
        // Redirecionar para o dashboard ou Streamlit
        window.location.href = '/streamlit-dashboard/';
    } else {
        console.error('Erro no login:', result.error);
        alert('Erro no login: ' + result.error);
    }
});

// Exemplo de requisição autenticada para upload de PDFs
async function uploadPDFs(files) {
    try {
        const formData = new FormData();
        files.forEach(file => {
            formData.append('files', file);
        });

        const response = await auth.authenticatedRequest('/extract/upload-e-processar-pdf/', {
            method: 'POST',
            body: formData,
            headers: {} // Não incluir Content-Type para FormData
        });

        if (response.ok) {
            const data = await response.json();
            console.log('Upload realizado com sucesso:', data);
            return data;
        } else {
            const error = await response.json();
            throw new Error(error.error || 'Erro no upload');
        }
    } catch (error) {
        console.error('Erro no upload:', error);
        throw error;
    }
}

// Verificação de autenticação ao carregar a página
document.addEventListener('DOMContentLoaded', async () => {
    if (auth.isAuthenticated()) {
        if (await auth.ensureValidToken()) {
            console.log('Usuário autenticado:', auth.getUserInfo());
            // Mostrar conteúdo autenticado
        } else {
            console.log('Token inválido, redirecionando para login');
            // Redirecionar para login
            window.location.href = '/login';
        }
    } else {
        console.log('Usuário não autenticado');
        // Mostrar página de login
    }
});

// Logout
document.getElementById('logoutBtn')?.addEventListener('click', async () => {
    await auth.logout();
    window.location.href = '/login';
});
"""

# Exemplo em Python para requisições autenticadas
python_example = """
# client.py - Cliente Python para comunicação com a API

import requests
import json
from typing import Optional, Dict, Any

class NFSeAPIClient:
    def __init__(self, base_url: str = "http://127.0.0.1:8001"):
        self.base_url = base_url
        self.access_token: Optional[str] = None
        self.refresh_token: Optional[str] = None
    
    def login(self, username: str, password: str) -> Dict[str, Any]:
        \"\"\"Realiza login e armazena tokens\"\"\"
        try:
            response = requests.post(
                f"{self.base_url}/extract/auth/login/",
                json={"username": username, "password": password},
                timeout=30
            )
            
            if response.status_code == 200:
                data = response.json()
                self.access_token = data['tokens']['access_token']
                self.refresh_token = data['tokens']['refresh_token']
                return {"success": True, "user": data['user']}
            else:
                error_data = response.json()
                return {"success": False, "error": error_data.get('error', 'Erro desconhecido')}
                
        except requests.exceptions.RequestException as e:
            return {"success": False, "error": f"Erro de conexão: {str(e)}"}
    
    def logout(self) -> None:
        \"\"\"Realiza logout\"\"\"
        try:
            if self.access_token:
                requests.post(
                    f"{self.base_url}/extract/auth/logout/",
                    headers={"Authorization": f"Bearer {self.access_token}"},
                    timeout=10
                )
        except:
            pass
        finally:
            self.access_token = None
            self.refresh_token = None
    
    def refresh_access_token(self) -> bool:
        \"\"\"Renova o access token\"\"\"
        if not self.refresh_token:
            return False
        
        try:
            response = requests.post(
                f"{self.base_url}/extract/auth/refresh/",
                json={"refresh_token": self.refresh_token},
                timeout=30
            )
            
            if response.status_code == 200:
                data = response.json()
                self.access_token = data['tokens']['access_token']
                return True
            
            return False
        except:
            return False
    
    def authenticated_request(self, method: str, endpoint: str, **kwargs) -> requests.Response:
        \"\"\"Faz requisição autenticada\"\"\"
        if not self.access_token:
            raise Exception("Não autenticado")
        
        headers = kwargs.get('headers', {})
        headers['Authorization'] = f"Bearer {self.access_token}"
        kwargs['headers'] = headers
        
        url = f"{self.base_url}{endpoint}"
        response = getattr(requests, method.lower())(url, **kwargs)
        
        # Se token expirou, tenta renovar
        if response.status_code == 401:
            if self.refresh_access_token():
                headers['Authorization'] = f"Bearer {self.access_token}"
                response = getattr(requests, method.lower())(url, **kwargs)
        
        return response
    
    def upload_pdfs(self, files: Dict[str, bytes]) -> Dict[str, Any]:
        \"\"\"Upload de PDFs para processamento\"\"\"
        files_payload = [
            ("files", (name, content, "application/pdf")) 
            for name, content in files.items()
        ]
        
        response = self.authenticated_request(
            "POST", 
            "/extract/upload-e-processar-pdf/",
            files=files_payload,
            timeout=120
        )
        
        return response.json() if response.status_code == 200 else {"error": response.text}

# Exemplo de uso
if __name__ == "__main__":
    client = NFSeAPIClient()
    
    # Login
    result = client.login("seu_usuario", "sua_senha")
    if result["success"]:
        print("Login realizado com sucesso!")
        print(f"Usuário: {result['user']['username']}")
        
        # Exemplo de upload
        with open("nota_fiscal.pdf", "rb") as f:
            files = {"nota_fiscal.pdf": f.read()}
        
        upload_result = client.upload_pdfs(files)
        print("Resultado do upload:", upload_result)
        
        # Logout
        client.logout()
    else:
        print(f"Erro no login: {result['error']}")
"""

print("Exemplos de código para integração com a API de autenticação:")
print("\n" + "="*50)
print("JAVASCRIPT/FRONTEND:")
print("="*50)
print(js_example)
print("\n" + "="*50)
print("PYTHON CLIENT:")
print("="*50)
print(python_example)
