from django.core.management.base import BaseCommand, CommandError
from django.contrib.auth.models import User
from extract.models import PaymentOrder, UserCredits  # ajuste o nome do app se necessário

class Command(BaseCommand):
    help = 'Confirma uma ordem de pagamento manualmente e adiciona créditos ao usuário'

    def add_arguments(self, parser):
        parser.add_argument('payment_order_id', type=str, help='ID da ordem de pagamento (UUID)')

    def handle(self, *args, **options):
        payment_order_id = options['payment_order_id']

        try:
            payment_order = PaymentOrder.objects.get(id=payment_order_id)
        except PaymentOrder.DoesNotExist:
            raise CommandError(f'Ordem de pagamento com ID {payment_order_id} não encontrada.')

        if payment_order.status != 'PENDING':
            self.stdout.write(self.style.WARNING(f'A ordem já está com status: {payment_order.status}'))
            return

        # Marca como paga e adiciona créditos
        success = payment_order.mark_as_paid(confirmed_by_user=payment_order.user)

        if success:
            user_credits = UserCredits.objects.get(user=payment_order.user)
            self.stdout.write(self.style.SUCCESS(
                f"Pagamento confirmado! {payment_order.credits_amount} créditos adicionados para {payment_order.user.username}."
            ))
            self.stdout.write(f"Novo saldo: {user_credits.balance}")
        else:
            self.stdout.write(self.style.ERROR("Erro ao processar pagamento."))


# Comando para confirmar uma ordem de pagamento:
# python manage.py confirm_payment <payment_order_id>
