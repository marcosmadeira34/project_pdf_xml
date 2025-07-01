from django.contrib.auth import authenticate
from django.http import JsonResponse
from django.views import View
from django.views.decorators.csrf import csrf_exempt
from django.utils.decorators import method_decorator
from django.contrib.auth.models import User
from .jwt_auth import JWTAuthenticationService, extract_token_from_header
import json
import logging

logger = logging.getLogger(__name__)


@method_decorator(csrf_exempt, name='dispatch')
class AuthLoginView(View):
    """
    Endpoint para login e geração de tokens JWT
    """
    
    def get(self, request):
        """Retorna informações sobre o endpoint de login"""
        return JsonResponse({
            'endpoint': '/auth/login/',
            'method': 'POST',
            'description': 'Endpoint para autenticação JWT',
            'required_fields': ['username', 'password'],
            'example': {
                'username': 'seu_usuario',
                'password': 'sua_senha'
            },
            'response': {
                'success': {
                    'user': '{ dados do usuário }',
                    'tokens': {
                        'access_token': 'JWT access token',
                        'refresh_token': 'JWT refresh token',
                        'token_type': 'Bearer',
                        'expires_in': 'segundos até expiração'
                    }
                },
                'error': 'Mensagem de erro em caso de falha'
            }
        })
    
    def post(self, request):
        try:
            data = json.loads(request.body)
            username = data.get('username')
            password = data.get('password')
            
            if not username or not password:
                return JsonResponse({
                    'error': 'Username and password are required'
                }, status=400)
            
            # Autentica o usuário
            user = authenticate(username=username, password=password)
            
            if user is None:
                return JsonResponse({
                    'error': 'Invalid credentials'
                }, status=401)
            
            if not user.is_active:
                return JsonResponse({
                    'error': 'User account is disabled'
                }, status=401)
            
            # Gera tokens JWT
            tokens = JWTAuthenticationService.generate_tokens(user)
            
            # Log do login bem-sucedido
            logger.info(f"User {username} logged in successfully")
            
            return JsonResponse({
                'message': 'Login successful',
                'user': {
                    'id': user.id,
                    'username': user.username,
                    'email': user.email,
                    'first_name': user.first_name,
                    'last_name': user.last_name,
                    'is_staff': user.is_staff,
                },
                'tokens': tokens
            })
            
        except json.JSONDecodeError:
            return JsonResponse({
                'error': 'Invalid JSON data'
            }, status=400)
        except Exception as e:
            logger.error(f"Error in login: {e}")
            return JsonResponse({
                'error': 'Internal server error'
            }, status=500)


@method_decorator(csrf_exempt, name='dispatch')
class AuthRefreshView(View):
    """
    Endpoint para renovar access token usando refresh token
    """
    
    def post(self, request):
        try:
            data = json.loads(request.body)
            refresh_token = data.get('refresh_token')
            
            if not refresh_token:
                return JsonResponse({
                    'error': 'Refresh token is required'
                }, status=400)
            
            # Renova o access token
            new_tokens = JWTAuthenticationService.refresh_access_token(refresh_token)
            
            if not new_tokens:
                return JsonResponse({
                    'error': 'Invalid or expired refresh token'
                }, status=401)
            
            return JsonResponse({
                'message': 'Token refreshed successfully',
                'tokens': new_tokens
            })
            
        except json.JSONDecodeError:
            return JsonResponse({
                'error': 'Invalid JSON data'
            }, status=400)
        except Exception as e:
            logger.error(f"Error in token refresh: {e}")
            return JsonResponse({
                'error': 'Internal server error'
            }, status=500)


@method_decorator(csrf_exempt, name='dispatch')
class AuthVerifyView(View):
    """
    Endpoint para verificar se um token JWT é válido
    """
    
    def post(self, request):
        try:
            # Verifica o token do header Authorization
            auth_header = request.headers.get('Authorization')
            token = extract_token_from_header(auth_header)
            
            if not token:
                # Tenta obter do body também
                data = json.loads(request.body) if request.body else {}
                token = data.get('access_token')
            
            if not token:
                return JsonResponse({
                    'error': 'Access token is required'
                }, status=400)
            
            # Verifica o token
            payload = JWTAuthenticationService.verify_token(token)
            
            if not payload:
                return JsonResponse({
                    'error': 'Invalid or expired token'
                }, status=401)
            
            # Busca dados atualizados do usuário
            try:
                user = User.objects.get(id=payload['user_id'])
                return JsonResponse({
                    'valid': True,
                    'user': {
                        'id': user.id,
                        'username': user.username,
                        'email': user.email,
                        'first_name': user.first_name,
                        'last_name': user.last_name,
                        'is_staff': user.is_staff,
                    },
                    'token_payload': payload
                })
            except User.DoesNotExist:
                return JsonResponse({
                    'error': 'User not found'
                }, status=404)
            
        except json.JSONDecodeError:
            return JsonResponse({
                'error': 'Invalid JSON data'
            }, status=400)
        except Exception as e:
            logger.error(f"Error in token verification: {e}")
            return JsonResponse({
                'error': 'Internal server error'
            }, status=500)


@method_decorator(csrf_exempt, name='dispatch')
class AuthLogoutView(View):
    """
    Endpoint para logout (invalidação de token)
    Nota: Como JWT é stateless, apenas retornamos sucesso.
    Em um cenário real, você poderia manter uma blacklist de tokens.
    """
    
    def post(self, request):
        try:
            # Verifica se o token é válido antes de fazer logout
            auth_header = request.headers.get('Authorization')
            token = extract_token_from_header(auth_header)
            
            if token:
                payload = JWTAuthenticationService.verify_token(token)
                if payload:
                    logger.info(f"User {payload.get('username')} logged out")
            
            return JsonResponse({
                'message': 'Logout successful'
            })
            
        except Exception as e:
            logger.error(f"Error in logout: {e}")
            return JsonResponse({
                'error': 'Internal server error'
            }, status=500)


@method_decorator(csrf_exempt, name='dispatch')
class AuthUserInfoView(View):
    """
    Endpoint para obter informações do usuário autenticado
    """
    
    def get(self, request):
        try:
            # Verifica o token
            auth_header = request.headers.get('Authorization')
            token = extract_token_from_header(auth_header)
            
            if not token:
                return JsonResponse({
                    'error': 'Access token is required'
                }, status=401)
            
            user = JWTAuthenticationService.get_user_from_token(token)
            
            if not user:
                return JsonResponse({
                    'error': 'Invalid or expired token'
                }, status=401)
            
            return JsonResponse({
                'user': {
                    'id': user.id,
                    'username': user.username,
                    'email': user.email,
                    'first_name': user.first_name,
                    'last_name': user.last_name,
                    'is_staff': user.is_staff,
                    'is_superuser': user.is_superuser,
                    'date_joined': user.date_joined.isoformat(),
                    'last_login': user.last_login.isoformat() if user.last_login else None,
                }
            })
            
        except Exception as e:
            logger.error(f"Error getting user info: {e}")
            return JsonResponse({
                'error': 'Internal server error'
            }, status=500)
