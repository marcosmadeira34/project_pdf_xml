from django.core.management.base import BaseCommand, CommandError
from django.contrib.auth.models import User
from extract.models import UserCredits  # Ajuste se o modelo estiver em outro app

class Command(BaseCommand):
    help = 'Consulta o saldo de créditos de um usuário'

    def add_arguments(self, parser):
        parser.add_argument('user_id', type=int, help='ID do usuário')

    def handle(self, *args, **options):
        user_id = options['user_id']

        try:
            user = User.objects.get(id=user_id)
        except User.DoesNotExist:
            raise CommandError(f'Usuário com ID {user_id} não encontrado.')

        try:
            user_credits = UserCredits.objects.get(user=user)
        except UserCredits.DoesNotExist:
            self.stdout.write(self.style.WARNING('O usuário ainda não possui créditos.'))
            return

        self.stdout.write(self.style.SUCCESS(f"Saldo de {user.username}:"))
        self.stdout.write(f" - Saldo atual: {user_credits.balance}")
        self.stdout.write(f" - Total comprado: {user_credits.total_purchased}")
        self.stdout.write(f" - Total usado: {user_credits.total_used}")


# Commando para verificar o saldo de um usuário específico:
# python manage.py check_user_balance 1
