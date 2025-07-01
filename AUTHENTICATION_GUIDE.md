# Sistema de Autenticação JWT - NFS-e Control

## Visão Geral

Este sistema implementa autenticação JWT (JSON Web Tokens) para proteger a comunicação entre o frontend e a interface Streamlit, garantindo que apenas usuários autenticados possam acessar a solução.

## Arquitetura Implementada

```
Frontend/Cliente → Django Backend (JWT Auth) → Streamlit Dashboard
```

### Componentes Criados:

1. **Backend Django (API de Autenticação)**

   - `extract/jwt_auth.py` - Serviço de autenticação JWT
   - `extract/auth_views.py` - Endpoints de autenticação
   - `extract/middleware.py` - Middleware de autenticação e CORS
   - URLs de autenticação em `extract/urls.py`

2. **Frontend Streamlit (Cliente Autenticado)**

   - `extract/streamlit_auth.py` - Gerenciador de autenticação
   - `extract/dashboard.py` - Dashboard protegido

3. **Exemplos de Integração**
   - `frontend_auth_examples.py` - Exemplos para JavaScript e Python

## Endpoints de Autenticação

### 1. Login

```
POST /extract/auth/login/
Content-Type: application/json

{
    "username": "seu_usuario",
    "password": "sua_senha"
}
```

**Resposta de Sucesso:**

```json
{
  "message": "Login successful",
  "user": {
    "id": 1,
    "username": "usuario",
    "email": "usuario@email.com",
    "first_name": "Nome",
    "last_name": "Sobrenome",
    "is_staff": false
  },
  "tokens": {
    "access_token": "eyJ0eXAiOiJKV1QiLCJhbGciOiJIUzI1NiJ9...",
    "refresh_token": "eyJ0eXAiOiJKV1QiLCJhbGciOiJIUzI1NiJ9...",
    "token_type": "Bearer",
    "expires_in": 86400
  }
}
```

### 2. Renovação de Token

```
POST /extract/auth/refresh/
Content-Type: application/json

{
    "refresh_token": "eyJ0eXAiOiJKV1QiLCJhbGciOiJIUzI1NiJ9..."
}
```

### 3. Verificação de Token

```
POST /extract/auth/verify/
Authorization: Bearer <access_token>
```

### 4. Logout

```
POST /extract/auth/logout/
Authorization: Bearer <access_token>
```

### 5. Informações do Usuário

```
GET /extract/auth/user-info/
Authorization: Bearer <access_token>
```

## Configuração do Sistema

### 1. Variáveis de Ambiente

Adicione ao seu arquivo `.env`:

```env
# Chave secreta específica para JWT (opcional, usa DJANGO_SECRET_KEY por padrão)
JWT_SECRET_KEY=sua_chave_secreta_jwt_aqui

# URL do backend Django para o Streamlit
DJANGO_BACKEND_URL=http://127.0.0.1:8001
```

### 2. Settings Django

As seguintes configurações foram adicionadas ao `settings.py`:

```python
MIDDLEWARE = [
    'django.middleware.security.SecurityMiddleware',
    'extract.middleware.CORSMiddleware',  # CORS customizado
    'django.contrib.sessions.middleware.SessionMiddleware',
    'django.middleware.common.CommonMiddleware',
    'django.middleware.csrf.CsrfViewMiddleware',
    'django.contrib.auth.middleware.AuthenticationMiddleware',
    'extract.middleware.JWTAuthenticationMiddleware',  # JWT Auth
    'django.contrib.messages.middleware.MessageMiddleware',
    'django.middleware.clickjacking.XFrameOptionsMiddleware',
    "whitenoise.middleware.WhiteNoiseMiddleware",
]
```

## Como Usar

### 1. Iniciando os Serviços

```bash
# Terminal 1 - Django Backend
cd /home/marcosmadeira/nfse-abrasf-project
python manage.py runserver 8001

# Terminal 2 - Streamlit Dashboard
cd /home/marcosmadeira/nfse-abrasf-project
streamlit run extract/dashboard.py --server.port=8501
```

### 2. Acesso ao Sistema

1. **Acesse o Streamlit**: http://localhost:8501
2. **Tela de Login**: Se não autenticado, será apresentada a tela de login
3. **Credenciais**: Use as credenciais de usuário Django existentes
4. **Dashboard**: Após login, acesso completo ao sistema

### 3. Fluxo de Autenticação

```
1. Usuário acessa Streamlit
2. Sistema verifica autenticação
3. Se não autenticado → Tela de Login
4. Login → Django Backend valida credenciais
5. Backend retorna JWT tokens
6. Streamlit armazena tokens na sessão
7. Todas as requisições usam tokens JWT
8. Renovação automática quando necessário
```

## Segurança Implementada

### 1. Tokens JWT

- **Access Token**: Válido por 24 horas
- **Refresh Token**: Válido por 7 dias
- **Renovação Automática**: Sistema renova automaticamente tokens expirados

### 2. Middleware de Proteção

- **Rotas Protegidas**: Upload, processamento, downloads
- **Headers CORS**: Configuração específica para Streamlit
- **Validação de Token**: Verificação automática em todas as requisições

### 3. Tratamento de Erros

- **Token Expirado**: Logout automático e redirecionamento
- **Conexão Perdida**: Tentativas de reconexão
- **Sessão Inválida**: Limpeza automática de dados

## Rotas Protegidas

As seguintes rotas requerem autenticação JWT:

- `/extract/upload-e-processar-pdf/` - Upload de PDFs
- `/extract/merge_pdfs/` - Merge de PDFs
- `/extract/task-status/` - Status de tarefas
- `/extract/download-zip/` - Download de arquivos
- `/extract/send-xml-to-external-api/` - Envio para API externa
- `/extract/auth/user-info/` - Informações do usuário

## Rotas Isentas de Autenticação

- `/extract/` - Página de login Django
- `/extract/auth/login/` - Endpoint de login
- `/extract/auth/refresh/` - Renovação de token
- `/extract/auth/verify/` - Verificação de token
- `/extract/auth/logout/` - Logout
- `/admin/` - Django Admin
- `/static/` - Arquivos estáticos
- `/media/` - Arquivos de mídia

## Integração com Frontend

### JavaScript/React/Angular

Veja o arquivo `frontend_auth_examples.py` para exemplos completos de:

- Sistema de login
- Gerenciamento de tokens
- Requisições autenticadas
- Renovação automática de tokens

### Python Client

Para integração com outras aplicações Python:

```python
from frontend_auth_examples import NFSeAPIClient

client = NFSeAPIClient("http://localhost:8001")
result = client.login("usuario", "senha")

if result["success"]:
    # Fazer requisições autenticadas
    upload_result = client.upload_pdfs({"arquivo.pdf": conteudo_bytes})
```

## Monitoramento e Logs

O sistema registra os seguintes eventos:

- **Logins bem-sucedidos**: Username e timestamp
- **Tokens expirados**: Tentativas de renovação
- **Erros de autenticação**: Tokens inválidos ou usuários inexistentes
- **Requisições protegidas**: Acesso a endpoints sensíveis

## Troubleshooting

### 1. Erro "Token inválido"

- Verifique se JWT_SECRET_KEY está configurada
- Confirme que o usuário existe no Django
- Verifique logs do servidor Django

### 2. CORS Issues

- Confirme que o middleware CORSMiddleware está ativo
- Verifique ALLOWED_HOSTS no settings.py

### 3. Streamlit não carrega

- Confirme que DJANGO_BACKEND_URL está correto
- Verifique se o Django está rodando na porta 8001
- Teste endpoints diretamente via curl/Postman

## Exemplo de Teste Manual

```bash
# 1. Login
curl -X POST http://localhost:8001/extract/auth/login/ \
  -H "Content-Type: application/json" \
  -d '{"username": "admin", "password": "admin123"}'

# 2. Usar token retornado para requisição autenticada
curl -X GET http://localhost:8001/extract/auth/user-info/ \
  -H "Authorization: Bearer SEU_ACCESS_TOKEN_AQUI"
```

## Próximos Passos

Para produção, considere:

1. **HTTPS Obrigatório**: Configure SSL/TLS
2. **Rate Limiting**: Limite tentativas de login
3. **Blacklist de Tokens**: Sistema de invalidação
4. **Logs Avançados**: Auditoria completa
5. **Domínios Específicos**: CORS mais restritivo
