from django.core.management.base import BaseCommand
from extract.models import CreditPackage

class Command(BaseCommand):
    help = 'Lista todos os pacotes de créditos disponíveis'

    def handle(self, *args, **kwargs):
        packages = CreditPackage.objects.all()

        if not packages:
            self.stdout.write(self.style.WARNING('Nenhum pacote de créditos cadastrado.'))
            return

        self.stdout.write(self.style.SUCCESS('Pacotes de créditos disponíveis:'))
        for package in packages:
            self.stdout.write(f'ID: {package.id} | Descrição: {package.name} | Créditos: {package.credits} | Valor: R$ {package.price}')
