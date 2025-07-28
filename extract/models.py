from django.db import models
from django.contrib.auth.models import User
from django.utils import timezone
import uuid
from django.core.mail import send_mail
from django.conf import settings



class UserCredits(models.Model):
    """Modelo para gerenciar créditos dos usuários"""
    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name='credits')
    balance = models.IntegerField(default=0, help_text="Saldo atual de créditos")
    total_purchased = models.IntegerField(default=0, help_text="Total de créditos comprados")
    total_used = models.IntegerField(default=0, help_text="Total de créditos utilizados")
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        verbose_name = "Créditos do Usuário"
        verbose_name_plural = "Créditos dos Usuários"
    
    def __str__(self):
        return f"{self.user.username} - {self.balance} créditos"
    
    def add_credits(self, amount, reason="Compra"):
        """Adiciona créditos ao usuário"""
        self.balance += amount
        self.total_purchased += amount
        self.save()
        
        # Registra a transação
        CreditTransaction.objects.create(
            user=self.user,
            transaction_type='PURCHASE',
            amount=amount,
            balance_after=self.balance,
            description=reason
        )
    
    def use_credits(self, amount, reason="Conversão PDF"):
        """Usa créditos do usuário"""
        if self.balance >= amount:
            self.balance -= amount
            self.total_used += amount
            self.save()
            
            # Registra a transação
            CreditTransaction.objects.create(
                user=self.user,
                transaction_type='USAGE',
                amount=-amount,
                balance_after=self.balance,
                description=reason
            )
            return True
        return False
    
    def has_credits(self, amount=1):
        """Verifica se o usuário tem créditos suficientes"""
        return self.balance >= amount


class PaymentOrder(models.Model):
    """Modelo para pedidos de pagamento PIX"""
    STATUS_CHOICES = [
        ('PENDING', 'Pendente'),
        ('PAID', 'Pago'),
        ('CANCELLED', 'Cancelado'),
        ('EXPIRED', 'Expirado'),
    ]
    
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='payment_orders')
    credits_amount = models.IntegerField(help_text="Quantidade de créditos a serem adicionados")
    price = models.DecimalField(max_digits=10, decimal_places=2, help_text="Valor em reais")
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='PENDING')
    
    # Dados do PIX
    pix_code = models.TextField(blank=True, null=True, help_text="Código PIX para pagamento")
    pix_qr_code = models.TextField(blank=True, null=True, help_text="QR Code PIX em base64")
    pix_expires_at = models.DateTimeField(blank=True, null=True)
    
    # Dados de confirmação
    payment_proof = models.TextField(blank=True, null=True, help_text="Comprovante de pagamento")
    paid_at = models.DateTimeField(blank=True, null=True)
    confirmed_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True, related_name='confirmed_payments')
    
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        verbose_name = "Pedido de Pagamento"
        verbose_name_plural = "Pedidos de Pagamento"
        ordering = ['-created_at']
    
    def __str__(self):
        return f"{self.user.username} - {self.credits_amount} créditos - R$ {self.price}"
    
    def mark_as_paid(self, confirmed_by_user=None):
        """Marca o pedido como pago e adiciona créditos"""
        if self.status == 'PENDING':
            self.status = 'PAID'
            self.paid_at = timezone.now()
            self.confirmed_by = confirmed_by_user
            self.save()
            
            # Adiciona créditos ao usuário
            user_credits, created = UserCredits.objects.get_or_create(user=self.user)
            user_credits.add_credits(
                self.credits_amount, 
                f"Compra #{self.id} - PIX"
            )
            
            return True
        return False
    
    def is_expired(self):
        """Verifica se o PIX expirou"""
        if self.pix_expires_at and timezone.now() > self.pix_expires_at:
            return True
        return False


class CreditTransaction(models.Model):
    """Histórico de transações de créditos"""
    TRANSACTION_TYPES = [
        ('PURCHASE', 'Compra'),
        ('USAGE', 'Uso'),
        ('REFUND', 'Reembolso'),
        ('BONUS', 'Bônus'),
    ]
    
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='credit_transactions')
    transaction_type = models.CharField(max_length=20, choices=TRANSACTION_TYPES)
    amount = models.IntegerField(help_text="Quantidade de créditos (positivo para compra, negativo para uso)")
    balance_after = models.IntegerField(help_text="Saldo após a transação")
    description = models.CharField(max_length=255)
    
    # Referências opcionais
    payment_order = models.ForeignKey(PaymentOrder, on_delete=models.SET_NULL, null=True, blank=True)
    
    created_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        verbose_name = "Transação de Crédito"
        verbose_name_plural = "Transações de Créditos"
        ordering = ['-created_at']
    
    def __str__(self):
        sign = "+" if self.amount >= 0 else ""
        return f"{self.user.username} - {sign}{self.amount} créditos - {self.description}"


class CreditPackage(models.Model):
    """Pacotes de créditos disponíveis para compra"""
    name = models.CharField(max_length=100, help_text="Nome do pacote")
    credits = models.IntegerField(help_text="Quantidade de créditos")
    price = models.DecimalField(max_digits=10, decimal_places=2, help_text="Preço em reais")
    bonus_credits = models.IntegerField(default=0, help_text="Créditos bônus")
    is_active = models.BooleanField(default=True)
    is_popular = models.BooleanField(default=False, help_text="Marcar como mais popular")
    
    created_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        verbose_name = "Pacote de Créditos"
        verbose_name_plural = "Pacotes de Créditos"
        ordering = ['price']
    
    def __str__(self):
        total_credits = self.credits + self.bonus_credits
        return f"{self.name} - {total_credits} créditos - R$ {self.price}"
    
    @property
    def total_credits(self):
        return self.credits + self.bonus_credits
    
    @property
    def price_per_credit(self):
        return float(self.price) / self.total_credits


# extract/models.py
from django.db import models
import uuid

class ArquivoZip(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    zip_bytes = models.BinaryField(null=True, blank=True)  # campo binário no PostgreSQL
    nome_arquivo = models.CharField(max_length=255, blank=True, null=True, help_text="Nome do arquivo ZIP")  # NOVO CAMPO
    criado_em = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        verbose_name = "Arquivo ZIP"
        verbose_name_plural = "Arquivos ZIP"
    
    def __str__(self):
        return f"{self.nome_arquivo or 'ZIP'} - {self.criado_em.strftime('%d/%m/%Y %H:%M')}"
    

# Modelo para tickets de suporte
class SupportTicket(models.Model):
    STATUS_CHOICES = [
        ('aberto', 'Aberto'),
        ('em_andamento', 'Em Andamento'),
        ('respondido', 'Respondido'),
        ('fechado', 'Fechado'),
    ]

    PRIORITY_CHOICES = [
        ('baixa', 'Baixa'),
        ('media', 'Média'),
        ('alta', 'Alta'),
        ('urgente', 'Urgente'),
    ]

    
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='support_tickets')
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='aberto', help_text="Status do ticket")
    created_at = models.DateTimeField(auto_now_add=True, help_text="Data de criação do ticket")
    updated_at = models.DateTimeField(auto_now=True, help_text="Data da última atualização do ticket")
    priority = models.CharField(max_length=20, choices=PRIORITY_CHOICES, default='media', help_text="Prioridade do ticket")
    subject = models.CharField(max_length=200, help_text="Assunto do ticket")
    description = models.TextField(help_text="Descrição do problema")
    response = models.TextField(blank=True, null=True, help_text="Resposta do suporte")

    # Método para enviar e-mail de notificação ao usuário quando o ticket é respondido
    def save(self, *args, **kwargs):
        # Verifica se o status foi alterado para "respondido"
        if self.pk:
            original = SupportTicket.objects.get(pk=self.pk)
            if original.status != 'respondido' and self.status == 'respondido':
                try:
                    send_mail(
                        subject=f"Seu ticket #{self.id} foi respondido!",
                        message=self.response or "Sua solicitação foi respondida pela equipe de suporte.",
                        from_email=settings.DEFAULT_FROM_EMAIL,
                        recipient_list=[self.user.email],  # OU email do usuário, se tiver
                        fail_silently=True
                    )
                except Exception as e:
                    print("Erro ao enviar e-mail de resposta:", e)
        super().save(*args, **kwargs)

    def __str__(self):
        return f"#{self.id} - {self.subject}"
    



class SupportTicketAttachment(models.Model):
    ticket = models.ForeignKey(SupportTicket, on_delete=models.CASCADE, related_name="attachments")
    file = models.FileField(upload_to="support_attachments/")
    uploaded_at = models.DateTimeField(auto_now_add=True)