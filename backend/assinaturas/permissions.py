from rest_framework import permissions

from .models import Assinatura


class IsSubscriber(permissions.BasePermission):
    """Permite acesso apenas a usuários com assinatura ativa e dentro do prazo."""

    message = 'É necessário ter uma assinatura ativa para acessar este recurso.'

    def has_permission(self, request, view):
        usuario = request.user
        if not usuario or not usuario.is_authenticated:
            return False

        # Staff sempre tem acesso — evita travar operação e suporte.
        if usuario.is_staff:
            return True

        try:
            assinatura = usuario.assinatura
        except Assinatura.DoesNotExist:
            return False

        return assinatura.esta_ativa
