from django.core.management.base import BaseCommand
from extract.models import PaymentOrder  # ajuste se o app for outro
from django.contrib.auth.models import User

class Command(BaseCommand):
    help = 'Lista as ordens de pagamento de um usuário'

    def add_arguments(self, parser):
        parser.add_argument('--user_id', type=int, help='ID do usuário (opcional)')

    def handle(self, *args, **options):
        user_id = options.get('user_id')

        if user_id:
            try:
                user = User.objects.get(id=user_id)
            except User.DoesNotExist:
                self.stdout.write(self.style.ERROR(f'Usuário com ID {user_id} não encontrado.'))
                return
            orders = PaymentOrder.objects.filter(user=user).order_by('-created_at')
        else:
            orders = PaymentOrder.objects.all().order_by('-created_at')

        if not orders.exists():
            self.stdout.write("Nenhuma ordem de pagamento encontrada.")
            return

        for o in orders:
            self.stdout.write(
                f"ID: {o.id} | User: {o.user.username} | R$ {o.price} | Créditos: {o.credits_amount} | Status: {o.status} | Criado em: {o.created_at.strftime('%d/%m/%Y %H:%M')}"
            )
# Comando para listar ordens de pagamento:
# python manage.py list_payment_orders --user_id <user_id>