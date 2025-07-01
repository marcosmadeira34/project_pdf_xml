from django.http import JsonResponse
from django.utils.deprecation import MiddlewareMixin
from .jwt_auth import JWTAuthenticationService, extract_token_from_header
import logging

logger = logging.getLogger(__name__)


class JWTAuthenticationMiddleware(MiddlewareMixin):
    """
    Middleware para autenticação JWT em rotas protegidas
    """
    
    # Rotas que requerem autenticação JWT
    PROTECTED_PATHS = [
        '/extract/upload-e-processar-pdf/',
        '/extract/merge_pdfs/',
        '/extract/task-status/',
        '/extract/download-zip/',
        '/extract/send-xml-to-external-api/',
        '/extract/auth/user-info/',
    ]
    
    # Rotas que não requerem autenticação
    EXEMPT_PATHS = [
        '/',  # Login page
        '/auth/login/',
        '/auth/refresh/',
        'auth/verify/',
        '/auth/logout/',
        '/admin/',
        '/static/',
        '/media/',
    ]
    
    def process_request(self, request):
        """
        Processa a requisição e verifica autenticação JWT se necessário
        """
        path = request.path
        
        # Verifica se a rota está isenta de autenticação
        for exempt_path in self.EXEMPT_PATHS:
            if path.startswith(exempt_path):
                return None
        
        # Verifica se a rota requer autenticação
        for protected_path in self.PROTECTED_PATHS:
            if path.startswith(protected_path):
                return self._authenticate_request(request)
        
        # Se não é protegido nem isento, deixa passar
        return None
    
    def _authenticate_request(self, request):
        """
        Autentica a requisição usando JWT
        """
        try:
            # Extrai o token do header Authorization
            auth_header = request.headers.get('Authorization')
            token = extract_token_from_header(auth_header)
            
            if not token:
                return JsonResponse({
                    'error': 'Authentication required. Please provide a valid access token.',
                    'code': 'MISSING_TOKEN'
                }, status=401)
            
            # Verifica o token
            user = JWTAuthenticationService.get_user_from_token(token)
            
            if not user:
                return JsonResponse({
                    'error': 'Invalid or expired access token.',
                    'code': 'INVALID_TOKEN'
                }, status=401)
            
            if not user.is_active:
                return JsonResponse({
                    'error': 'User account is disabled.',
                    'code': 'DISABLED_USER'
                }, status=401)
            
            # Adiciona o usuário autenticado ao request
            request.jwt_user = user
            request.jwt_authenticated = True
            
            return None
            
        except Exception as e:
            logger.error(f"Error in JWT authentication middleware: {e}")
            return JsonResponse({
                'error': 'Authentication error.',
                'code': 'AUTH_ERROR'
            }, status=500)


class CORSMiddleware(MiddlewareMixin):
    """
    Middleware customizado para CORS específico para Streamlit
    """
    
    def process_response(self, request, response):
        """
        Adiciona headers CORS à resposta
        """
        # Headers básicos de CORS
        response['Access-Control-Allow-Origin'] = '*'  # Em produção, especifique domínios específicos
        response['Access-Control-Allow-Methods'] = 'GET, POST, PUT, DELETE, OPTIONS'
        response['Access-Control-Allow-Headers'] = (
            'Accept, Accept-Language, Content-Language, Content-Type, '
            'Authorization, X-Requested-With, X-CSRFToken'
        )
        response['Access-Control-Allow-Credentials'] = 'true'
        response['Access-Control-Max-Age'] = '86400'
        
        return response
    
    def process_request(self, request):
        """
        Processa requisições OPTIONS para CORS preflight
        """
        if request.method == 'OPTIONS':
            response = JsonResponse({'message': 'CORS preflight'})
            response['Access-Control-Allow-Origin'] = '*'
            response['Access-Control-Allow-Methods'] = 'GET, POST, PUT, DELETE, OPTIONS'
            response['Access-Control-Allow-Headers'] = (
                'Accept, Accept-Language, Content-Language, Content-Type, '
                'Authorization, X-Requested-With, X-CSRFToken'
            )
            response['Access-Control-Allow-Credentials'] = 'true'
            response['Access-Control-Max-Age'] = '86400'
            return response
        
        return None
