from django.contrib import admin

from .models import Assinatura, EventoStripeProcessado, Plano


@admin.register(Plano)
class PlanoAdmin(admin.ModelAdmin):
    list_display = ('nome', 'preco', 'ativo', 'stripe_price_id')
    list_filter = ('ativo',)
    search_fields = ('nome', 'stripe_price_id')


@admin.register(Assinatura)
class AssinaturaAdmin(admin.ModelAdmin):
    list_display = ('usuario', 'plano', 'status', 'data_expiracao', 'esta_ativa')
    list_filter = ('status', 'plano')
    search_fields = ('usuario__username', 'usuario__email', 'stripe_subscription_id')
    autocomplete_fields = ('usuario',)
    list_select_related = ('usuario', 'plano')

    @admin.display(boolean=True, description='Vigente')
    def esta_ativa(self, obj):
        return obj.esta_ativa


@admin.register(EventoStripeProcessado)
class EventoStripeProcessadoAdmin(admin.ModelAdmin):
    list_display = ('evento_id', 'tipo', 'processado_em')
    list_filter = ('tipo',)
    search_fields = ('evento_id',)
    readonly_fields = ('evento_id', 'tipo', 'processado_em')
