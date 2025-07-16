from django.core.management.base import BaseCommand
from django.contrib.auth.models import User

class Command(BaseCommand):
    help = 'Lista todos os usuários com ID, username, nome e e-mail'

    def handle(self, *args, **options):
        users = User.objects.all().order_by('id')
        if not users.exists():
            self.stdout.write('Nenhum usuário encontrado.')
            return

        self.stdout.write('Usuários cadastrados:\n')
        for user in users:
            self.stdout.write(
                f"ID: {user.id} | Username: {user.username} | Nome: {user.get_full_name() or '---'} | Email: {user.email}"
            )


# Comando para listar todos os usuários:
# python manage.py list_users
