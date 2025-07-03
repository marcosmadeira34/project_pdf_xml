from django.http import JsonResponse
from django.views import View
from django.contrib.auth.decorators import login_required
from django.utils.decorators import method_decorator
from django.views.decorators.csrf import csrf_exempt
from django.utils import timezone
from django.db import transaction
from decimal import Decimal
import json
import uuid
import qrcode
import io
import base64
from datetime import timedelta

from .models import UserCredits, PaymentOrder, CreditTransaction, CreditPackage
from .jwt_auth import JWTAuthenticationService

@method_decorator(csrf_exempt, name='dispatch')
class CreditsInfoView(View):
    """Retorna informações dos créditos do usuário"""
    
    def post(self, request):
        # Verifica token JWT
        token = request.headers.get('Authorization', '').replace('Bearer ', '')
        if not token:
            return JsonResponse({'error': 'Token não fornecido'}, status=401)
        
        user_data = JWTAuthenticationService.verify_token(token)
        if not user_data:
            return JsonResponse({'error': 'Token inválido'}, status=401)
        
        try:
            # Busca o usuário baseado no token
            from django.contrib.auth.models import User
            user = User.objects.get(id=user_data['user_id'])
            
            # Busca ou cria os créditos do usuário
            user_credits, created = UserCredits.objects.get_or_create(user=user)
            
            # Últimas transações
            recent_transactions = CreditTransaction.objects.filter(
                user=user
            ).order_by('-created_at')[:10]
            
            transactions_data = []
            for trans in recent_transactions:
                transactions_data.append({
                    'type': trans.get_transaction_type_display(),
                    'amount': trans.amount,
                    'balance_after': trans.balance_after,
                    'description': trans.description,
                    'date': trans.created_at.strftime('%d/%m/%Y %H:%M')
                })
            
            return JsonResponse({
                'success': True,
                'credits': {
                    'balance': user_credits.balance,
                    'total_purchased': user_credits.total_purchased,
                    'total_used': user_credits.total_used,
                },
                'recent_transactions': transactions_data
            })
            
        except User.DoesNotExist:
            return JsonResponse({'error': 'Usuário não encontrado'}, status=404)
        except Exception as e:
            # Log do erro para debug
            import logging
            logger = logging.getLogger(__name__)
            logger.error(f'Erro em CreditsInfoView: {str(e)}', exc_info=True)
            
            return JsonResponse({'error': f'Erro interno: {str(e)}'}, status=500)


class CreditPackagesView(View):
    """Lista os pacotes de créditos disponíveis"""
    
    def get(self, request):
        try:
            packages = CreditPackage.objects.filter(is_active=True).order_by('price')
            
            packages_data = []
            for package in packages:
                packages_data.append({
                    'id': package.id,
                    'name': package.name,
                    'credits': package.credits,
                    'bonus_credits': package.bonus_credits,
                    'total_credits': package.total_credits,
                    'price': float(package.price),
                    'price_per_credit': round(package.price_per_credit, 2),
                    'is_popular': package.is_popular,
                })
            
            return JsonResponse({
                'success': True,
                'packages': packages_data
            })
            
        except Exception as e:
            import logging
            logger = logging.getLogger(__name__)
            logger.error(f'Erro em CreditPackagesView: {str(e)}', exc_info=True)
            
            return JsonResponse({'error': f'Erro interno: {str(e)}'}, status=500)


@method_decorator(csrf_exempt, name='dispatch')
class CreatePaymentOrderView(View):
    """Cria uma ordem de pagamento PIX"""
    
    def post(self, request):
        # Verifica token JWT
        token = request.headers.get('Authorization', '').replace('Bearer ', '')
        if not token:
            return JsonResponse({'error': 'Token não fornecido'}, status=401)
        
        user_data = JWTAuthenticationService.verify_token(token)
        if not user_data:
            return JsonResponse({'error': 'Token inválido'}, status=401)
        
        try:
            data = json.loads(request.body)
            package_id = data.get('package_id')
            
            if not package_id:
                return JsonResponse({'error': 'ID do pacote é obrigatório'}, status=400)
            
            # Busca o pacote
            try:
                package = CreditPackage.objects.get(id=package_id, is_active=True)
            except CreditPackage.DoesNotExist:
                return JsonResponse({'error': 'Pacote não encontrado'}, status=404)
            
            # Busca o usuário
            from django.contrib.auth.models import User
            user = User.objects.get(id=user_data['user_id'])
            
            # Cria a ordem de pagamento
            with transaction.atomic():
                payment_order = PaymentOrder.objects.create(
                    user=user,
                    credits_amount=package.total_credits,
                    price=package.price,
                    pix_expires_at=timezone.now() + timedelta(minutes=30)  # PIX expira em 30 min
                )
                
                # Gera PIX (simulado - você deve integrar com um gateway real)
                pix_data = self.generate_pix_payment(payment_order, package)
                
                payment_order.pix_code = pix_data['pix_code']
                payment_order.pix_qr_code = pix_data['qr_code_base64']
                payment_order.save()
            
            return JsonResponse({
                'success': True,
                'payment_order': {
                    'id': str(payment_order.id),
                    'credits_amount': payment_order.credits_amount,
                    'price': float(payment_order.price),
                    'pix_code': payment_order.pix_code,
                    'qr_code': payment_order.pix_qr_code,
                    'expires_at': payment_order.pix_expires_at.isoformat(),
                    'expires_in_minutes': 30
                }
            })
            
        except json.JSONDecodeError:
            return JsonResponse({'error': 'JSON inválido'}, status=400)
        except User.DoesNotExist:
            return JsonResponse({'error': 'Usuário não encontrado'}, status=404)
        except Exception as e:
            import logging
            logger = logging.getLogger(__name__)
            logger.error(f'Erro em CreatePaymentOrderView: {str(e)}', exc_info=True)
            
            return JsonResponse({'error': f'Erro interno: {str(e)}'}, status=500)
    
    def generate_pix_payment(self, payment_order, package):
        """Gera dados do PIX (simulado - integre com gateway real)"""
        
        # PIX Code simulado
        pix_code = f"00020126580014BR.GOV.BCB.PIX013636123456-7890-1234-abcd-{str(payment_order.id)[:12]}5204000053039865802BR5925LOVENFSE AUTOMACAO LTDA6009SAO PAULO61080123456762070503***6304"
        
        # Gera QR Code
        qr = qrcode.QRCode(version=1, box_size=10, border=5)
        qr.add_data(pix_code)
        qr.make(fit=True)
        
        # Converte QR Code para base64
        img = qr.make_image(fill_color="black", back_color="white")
        buffer = io.BytesIO()
        img.save(buffer, format='PNG')
        qr_code_base64 = base64.b64encode(buffer.getvalue()).decode()
        
        return {
            'pix_code': pix_code,
            'qr_code_base64': qr_code_base64
        }


@method_decorator(csrf_exempt, name='dispatch')
class ConfirmPaymentView(View):
    """Confirma pagamento manual pelo usuário"""
    
    def post(self, request):
        # Verifica token JWT
        token = request.headers.get('Authorization', '').replace('Bearer ', '')
        if not token:
            return JsonResponse({'error': 'Token não fornecido'}, status=401)
        
        user_data = JWTAuthenticationService.verify_token(token)
        if not user_data:
            return JsonResponse({'error': 'Token inválido'}, status=401)
        
        try:
            data = json.loads(request.body)
            payment_order_id = data.get('payment_order_id')
            payment_proof = data.get('payment_proof', 'Confirmação manual pelo usuário')
            
            if not payment_order_id:
                return JsonResponse({'error': 'ID da ordem de pagamento é obrigatório'}, status=400)
            
            # Busca o usuário
            from django.contrib.auth.models import User
            user = User.objects.get(id=user_data['user_id'])
            
            # Busca a ordem de pagamento
            try:
                payment_order = PaymentOrder.objects.get(
                    id=payment_order_id,
                    user=user,
                    status='PENDING'
                )
            except PaymentOrder.DoesNotExist:
                return JsonResponse({'error': 'Ordem de pagamento não encontrada ou já processada'}, status=404)
            
            # Verifica se não expirou
            if payment_order.is_expired():
                payment_order.status = 'EXPIRED'
                payment_order.save()
                return JsonResponse({'error': 'Ordem de pagamento expirada'}, status=400)
            
            # Marca como pago e adiciona créditos
            success = payment_order.mark_as_paid(confirmed_by_user=user)
            
            if success:
                # Atualiza informações do usuário
                user_credits = UserCredits.objects.get(user=user)
                
                return JsonResponse({
                    'success': True,
                    'message': 'Pagamento confirmado e créditos adicionados!',
                    'credits_added': payment_order.credits_amount,
                    'new_balance': user_credits.balance
                })
            else:
                return JsonResponse({'error': 'Erro ao processar pagamento'}, status=500)
                
        except json.JSONDecodeError:
            return JsonResponse({'error': 'JSON inválido'}, status=400)
        except User.DoesNotExist:
            return JsonResponse({'error': 'Usuário não encontrado'}, status=404)
        except Exception as e:
            import logging
            logger = logging.getLogger(__name__)
            logger.error(f'Erro em ConfirmPaymentView: {str(e)}', exc_info=True)
            
            return JsonResponse({'error': f'Erro interno: {str(e)}'}, status=500)


class PaymentOrderStatusView(View):
    """Verifica status de uma ordem de pagamento"""
    
    def get(self, request, order_id):
        # Verifica token JWT
        token = request.headers.get('Authorization', '').replace('Bearer ', '')
        if not token:
            return JsonResponse({'error': 'Token não fornecido'}, status=401)
        
        user_data = JWTAuthenticationService.verify_token(token)
        if not user_data:
            return JsonResponse({'error': 'Token inválido'}, status=401)
        
        try:
            # Busca o usuário
            from django.contrib.auth.models import User
            user = User.objects.get(id=user_data['user_id'])
            
            try:
                payment_order = PaymentOrder.objects.get(id=order_id, user=user)
            except PaymentOrder.DoesNotExist:
                return JsonResponse({'error': 'Ordem de pagamento não encontrada'}, status=404)
            
            # Verifica se expirou
            if payment_order.status == 'PENDING' and payment_order.is_expired():
                payment_order.status = 'EXPIRED'
                payment_order.save()
            
            return JsonResponse({
                'success': True,
                'payment_order': {
                    'id': str(payment_order.id),
                    'status': payment_order.status,
                    'credits_amount': payment_order.credits_amount,
                    'price': float(payment_order.price),
                    'created_at': payment_order.created_at.isoformat(),
                    'paid_at': payment_order.paid_at.isoformat() if payment_order.paid_at else None,
                    'is_expired': payment_order.is_expired()
                }
            })
            
        except User.DoesNotExist:
            return JsonResponse({'error': 'Usuário não encontrado'}, status=404)
        except Exception as e:
            import logging
            logger = logging.getLogger(__name__)
            logger.error(f'Erro em PaymentOrderStatusView: {str(e)}', exc_info=True)
            
            return JsonResponse({'error': f'Erro interno: {str(e)}'}, status=500)