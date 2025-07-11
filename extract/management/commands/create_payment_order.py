from django.core.management.base import BaseCommand, CommandError
from django.contrib.auth.models import User
from extract.models import CreditPackage, PaymentOrder
from django.utils import timezone
from datetime import timedelta

class Command(BaseCommand):
    help = 'Cria uma ordem de pagamento de créditos para um usuário'

    def add_arguments(self, parser):
        parser.add_argument('user_id', type=int, help='ID do usuário')
        parser.add_argument('package_id', type=int, help='ID do pacote de créditos')

    def handle(self, *args, **options):
        user_id = options['user_id']
        package_id = options['package_id']

        try:
            user = User.objects.get(id=user_id)
            package = CreditPackage.objects.get(id=package_id, is_active=True)
        except User.DoesNotExist:
            raise CommandError(f'Usuário com ID {user_id} não encontrado.')
        except CreditPackage.DoesNotExist:
            raise CommandError(f'Pacote de créditos com ID {package_id} não encontrado ou inativo.')

        payment_order = PaymentOrder.objects.create(
            user=user,
            credits_amount=package.total_credits,
            price=package.price,
            pix_expires_at=timezone.now() + timedelta(minutes=30),
            pix_code='Simulated PIX Code (via comando)',
            pix_qr_code='Simulated QR (via comando)',
        )

        self.stdout.write(self.style.SUCCESS(
            f'Ordem de pagamento criada com ID {payment_order.id} para o usuário {user.username}.'
        ))