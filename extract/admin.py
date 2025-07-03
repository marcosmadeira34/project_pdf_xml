from django.contrib import admin
from .models import UserCredits, PaymentOrder, CreditTransaction, CreditPackage

@admin.register(UserCredits)
class UserCreditsAdmin(admin.ModelAdmin):
    list_display = ['user', 'balance', 'total_purchased', 'total_used', 'updated_at']
    list_filter = ['created_at', 'updated_at']
    search_fields = ['user__username', 'user__email']
    readonly_fields = ['created_at', 'updated_at']
    
    fieldsets = (
        ('Usuário', {
            'fields': ('user',)
        }),
        ('Créditos', {
            'fields': ('balance', 'total_purchased', 'total_used')
        }),
        ('Datas', {
            'fields': ('created_at', 'updated_at'),
            'classes': ('collapse',)
        })
    )

@admin.register(PaymentOrder)
class PaymentOrderAdmin(admin.ModelAdmin):
    list_display = ['user', 'credits_amount', 'price', 'status', 'created_at', 'paid_at']
    list_filter = ['status', 'created_at', 'paid_at']
    search_fields = ['user__username', 'user__email']
    readonly_fields = ['id', 'created_at', 'updated_at', 'pix_code', 'pix_qr_code']
    
    fieldsets = (
        ('Pedido', {
            'fields': ('id', 'user', 'credits_amount', 'price', 'status')
        }),
        ('PIX', {
            'fields': ('pix_code', 'pix_qr_code', 'pix_expires_at')
        }),
        ('Confirmação', {
            'fields': ('payment_proof', 'paid_at', 'confirmed_by')
        }),
        ('Datas', {
            'fields': ('created_at', 'updated_at'),
            'classes': ('collapse',)
        })
    )
    
    actions = ['mark_as_paid']
    
    def mark_as_paid(self, request, queryset):
        for order in queryset.filter(status='PENDING'):
            order.mark_as_paid(confirmed_by_user=request.user)
        self.message_user(request, f"{queryset.count()} pedidos marcados como pagos")
    mark_as_paid.short_description = "Marcar como pago"

@admin.register(CreditTransaction)
class CreditTransactionAdmin(admin.ModelAdmin):
    list_display = ['user', 'transaction_type', 'amount', 'balance_after', 'description', 'created_at']
    list_filter = ['transaction_type', 'created_at']
    search_fields = ['user__username', 'description']
    readonly_fields = ['created_at']

@admin.register(CreditPackage)
class CreditPackageAdmin(admin.ModelAdmin):
    list_display = ['name', 'total_credits', 'price', 'price_per_credit', 'is_active', 'is_popular']
    list_filter = ['is_active', 'is_popular']
    search_fields = ['name']
    
    fieldsets = (
        ('Pacote', {
            'fields': ('name', 'credits', 'bonus_credits', 'price')
        }),
        ('Configurações', {
            'fields': ('is_active', 'is_popular')
        })
    )