from django.conf import settings
from django.db import models
from django.utils import timezone

from verticai.models_base import TimestampedModel


class Plano(TimestampedModel):
    nome = models.CharField(max_length=50)
    preco = models.DecimalField(max_digits=8, decimal_places=2)
    stripe_price_id = models.CharField(max_length=100, blank=True, null=True, unique=True)
    ativo = models.BooleanField(default=True)

    class Meta:
        verbose_name = 'Plano'
        verbose_name_plural = 'Planos'
        ordering = ('preco',)

    def __str__(self):
        return f"{self.nome} - R$ {self.preco}"


class Assinatura(TimestampedModel):
    class Status(models.TextChoices):
        INATIVA = 'INATIVA', 'Inativa'
        ATIVA = 'ATIVA', 'Ativa'
        CANCELADA = 'CANCELADA', 'Cancelada'

    usuario = models.OneToOneField(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='assinatura',
    )
    plano = models.ForeignKey(
        Plano,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='assinaturas',
    )
    status = models.CharField(max_length=20, choices=Status.choices, default=Status.INATIVA)

    # Separados: o customer é permanente, a subscription muda a cada ciclo/replano.
    stripe_customer_id = models.CharField(max_length=100, blank=True, null=True, db_index=True)
    stripe_subscription_id = models.CharField(
        max_length=100, blank=True, null=True, unique=True
    )

    # Até quando o acesso é válido. Preenchida a partir do current_period_end do Stripe.
    data_expiracao = models.DateTimeField(null=True, blank=True)

    class Meta:
        verbose_name = 'Assinatura'
        verbose_name_plural = 'Assinaturas'
        ordering = ('-criado_em',)
        indexes = [
            models.Index(fields=('status', 'data_expiracao'), name='idx_assinatura_status_exp'),
        ]

    def __str__(self):
        return f"{self.usuario.username} - {self.status}"

    @property
    def esta_ativa(self):
        """Assinatura vigente: status ATIVA e ainda dentro do período pago."""
        if self.status != self.Status.ATIVA:
            return False
        if self.data_expiracao is None:
            # Sem data de expiração conhecida não há como afirmar vigência.
            return False
        return self.data_expiracao > timezone.now()


class EventoStripeProcessado(models.Model):
    """Registro de idempotência: o Stripe reentrega o mesmo evento várias vezes."""

    evento_id = models.CharField(max_length=100, primary_key=True)
    tipo = models.CharField(max_length=100)
    processado_em = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = 'Evento Stripe processado'
        verbose_name_plural = 'Eventos Stripe processados'
        ordering = ('-processado_em',)

    def __str__(self):
        return f"{self.evento_id} ({self.tipo})"
