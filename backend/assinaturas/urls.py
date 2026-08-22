from django.urls import path

from .views import CheckoutView, ListarPlanosView, MinhaAssinaturaView, StripeWebhookView

urlpatterns = [
    path('planos/', ListarPlanosView.as_view(), name='listar_planos'),
    path('minha/', MinhaAssinaturaView.as_view(), name='minha_assinatura'),
    path('checkout/', CheckoutView.as_view(), name='checkout'),
    path('webhook/', StripeWebhookView.as_view(), name='stripe_webhook'),
]
