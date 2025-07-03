from django.http import JsonResponse
from django.urls import resolve
from django.contrib.auth.models import AnonymousUser
import json
from .jwt_auth import JWTAuthenticationService

class JWTAuthenticationMiddleware:
    def __init__(self, get_response):
        self.get_response = get_response
        
        # URLs que não precisam de autenticação
        self.exempt_paths = [
            '/admin/',
            '/auth/login/',
            '/auth/refresh/',
            '/credits/packages/',  # Permitir ver pacotes sem login
        ]

    def __call__(self, request):
        path = request.path_info
        
        # Verifica se a URL precisa de autenticação
        needs_auth = not any(path.startswith(exempt) for exempt in self.exempt_paths)
        
        if needs_auth:
            # Extrai token do header Authorization
            auth_header = request.META.get('HTTP_AUTHORIZATION', '')
            
            if auth_header.startswith('Bearer '):
                token = auth_header[7:]  # Remove 'Bearer '
                user_data = JWTAuthenticationService.verify_token(token)
                
                if user_data:
                    # Define o usuário na request
                    from django.contrib.auth.models import User
                    try:
                        user = User.objects.get(id=user_data['user_id'])
                        request.user = user
                        
                        # Debug log
                        import logging
                        logger = logging.getLogger(__name__)
                        logger.info(f"User authenticated: {user.username} (ID: {user.id})")
                        
                    except User.DoesNotExist:
                        request.user = AnonymousUser()
                        return JsonResponse({'error': 'Usuário não encontrado'}, status=401)
                else:
                    request.user = AnonymousUser()
                    return JsonResponse({'error': 'Token inválido ou expirado'}, status=401)
            else:
                request.user = AnonymousUser()
                return JsonResponse({'error': 'Token de autenticação necessário'}, status=401)
        else:
            # Para URLs que não precisam de auth, define AnonymousUser
            request.user = AnonymousUser()

        response = self.get_response(request)
        return response


class CORSMiddleware:
    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        response = self.get_response(request)
        
        # Headers CORS para Streamlit
        response["Access-Control-Allow-Origin"] = "*"
        response["Access-Control-Allow-Methods"] = "GET, POST, PUT, DELETE, OPTIONS"
        response["Access-Control-Allow-Headers"] = "Content-Type, Authorization, X-Requested-With"
        response["Access-Control-Allow-Credentials"] = "true"
        
        return response

    def process_request(self, request):
        if request.method == "OPTIONS":
            from django.http import HttpResponse
            response = HttpResponse()
            response["Access-Control-Allow-Origin"] = "*"
            response["Access-Control-Allow-Methods"] = "GET, POST, PUT, DELETE, OPTIONS"
            response["Access-Control-Allow-Headers"] = "Content-Type, Authorization, X-Requested-With"
            return response
