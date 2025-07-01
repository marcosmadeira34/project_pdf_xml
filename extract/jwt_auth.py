import jwt
import datetime
from django.conf import settings
from django.contrib.auth.models import User
import os
from typing import Optional, Dict, Any
import logging

logger = logging.getLogger(__name__)

# Chave secreta para JWT - deve ser a mesma que o Django SECRET_KEY ou uma específica
JWT_SECRET_KEY = os.getenv('JWT_SECRET_KEY', settings.SECRET_KEY)
JWT_ALGORITHM = 'HS256'
JWT_ACCESS_TOKEN_LIFETIME = datetime.timedelta(hours=24)  # Token válido por 24 horas
JWT_REFRESH_TOKEN_LIFETIME = datetime.timedelta(days=7)   # Refresh token válido por 7 dias


class JWTAuthenticationService:
    """Serviço para autenticação JWT"""
    
    @staticmethod
    def generate_tokens(user: User) -> Dict[str, str]:
        """
        Gera tokens de acesso e refresh para um usuário
        
        Args:
            user: Instância do usuário Django
            
        Returns:
            Dict contendo access_token e refresh_token
        """
        now = datetime.datetime.utcnow()
        
        # Payload base do token
        base_payload = {
            'user_id': user.id,
            'username': user.username,
            'email': user.email,
            'is_staff': user.is_staff,
            'is_superuser': user.is_superuser,
        }
        
        # Access Token
        access_payload = {
            **base_payload,
            'exp': now + JWT_ACCESS_TOKEN_LIFETIME,
            'iat': now,
            'type': 'access'
        }
        
        # Refresh Token
        refresh_payload = {
            **base_payload,
            'exp': now + JWT_REFRESH_TOKEN_LIFETIME,
            'iat': now,
            'type': 'refresh'
        }
        
        access_token = jwt.encode(access_payload, JWT_SECRET_KEY, algorithm=JWT_ALGORITHM)
        refresh_token = jwt.encode(refresh_payload, JWT_SECRET_KEY, algorithm=JWT_ALGORITHM)
        
        return {
            'access_token': access_token,
            'refresh_token': refresh_token,
            'token_type': 'Bearer',
            'expires_in': int(JWT_ACCESS_TOKEN_LIFETIME.total_seconds()),
        }
    
    @staticmethod
    def verify_token(token: str) -> Optional[Dict[str, Any]]:
        """
        Verifica e decodifica um token JWT
        
        Args:
            token: Token JWT para verificar
            
        Returns:
            Dict com dados do usuário se válido, None se inválido
        """
        try:
            payload = jwt.decode(token, JWT_SECRET_KEY, algorithms=[JWT_ALGORITHM])
            
            # Verifica se o token não expirou
            if datetime.datetime.utcnow().timestamp() > payload.get('exp', 0):
                logger.warning(f"Token expirado para usuário {payload.get('username', 'unknown')}")
                return None
                
            return payload
            
        except jwt.ExpiredSignatureError:
            logger.warning("Token JWT expirado")
            return None
        except jwt.InvalidTokenError as e:
            logger.warning(f"Token JWT inválido: {e}")
            return None
        except Exception as e:
            logger.error(f"Erro ao verificar token JWT: {e}")
            return None
    
    @staticmethod
    def refresh_access_token(refresh_token: str) -> Optional[Dict[str, str]]:
        """
        Gera um novo access token usando um refresh token
        
        Args:
            refresh_token: Refresh token válido
            
        Returns:
            Dict com novo access_token ou None se inválido
        """
        try:
            payload = jwt.decode(refresh_token, JWT_SECRET_KEY, algorithms=[JWT_ALGORITHM])
            
            # Verifica se é um refresh token
            if payload.get('type') != 'refresh':
                logger.warning("Token fornecido não é um refresh token")
                return None
            
            # Verifica se não expirou
            if datetime.datetime.utcnow().timestamp() > payload.get('exp', 0):
                logger.warning("Refresh token expirado")
                return None
            
            # Busca o usuário
            try:
                user = User.objects.get(id=payload['user_id'])
            except User.DoesNotExist:
                logger.warning(f"Usuário ID {payload['user_id']} não encontrado")
                return None
            
            # Gera novo access token
            now = datetime.datetime.utcnow()
            access_payload = {
                'user_id': user.id,
                'username': user.username,
                'email': user.email,
                'is_staff': user.is_staff,
                'is_superuser': user.is_superuser,
                'exp': now + JWT_ACCESS_TOKEN_LIFETIME,
                'iat': now,
                'type': 'access'
            }
            
            access_token = jwt.encode(access_payload, JWT_SECRET_KEY, algorithm=JWT_ALGORITHM)
            
            return {
                'access_token': access_token,
                'token_type': 'Bearer',
                'expires_in': int(JWT_ACCESS_TOKEN_LIFETIME.total_seconds()),
            }
            
        except jwt.ExpiredSignatureError:
            logger.warning("Refresh token expirado")
            return None
        except jwt.InvalidTokenError as e:
            logger.warning(f"Refresh token inválido: {e}")
            return None
        except Exception as e:
            logger.error(f"Erro ao renovar token: {e}")
            return None
    
    @staticmethod
    def get_user_from_token(token: str) -> Optional[User]:
        """
        Obtém o usuário a partir de um token JWT válido
        
        Args:
            token: Token JWT
            
        Returns:
            Instância do usuário ou None se token inválido
        """
        payload = JWTAuthenticationService.verify_token(token)
        if not payload:
            return None
        
        try:
            user = User.objects.get(id=payload['user_id'])
            return user
        except User.DoesNotExist:
            logger.warning(f"Usuário ID {payload['user_id']} não encontrado")
            return None


def extract_token_from_header(authorization_header: str) -> Optional[str]:
    """
    Extrai o token do header Authorization
    
    Args:
        authorization_header: Header no formato "Bearer <token>"
        
    Returns:
        Token extraído ou None se formato inválido
    """
    if not authorization_header:
        return None
    
    parts = authorization_header.split()
    if len(parts) != 2 or parts[0].lower() != 'bearer':
        return None
    
    return parts[1]
