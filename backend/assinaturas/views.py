import logging
from datetime import datetime, timezone as dt_timezone

import stripe
from django.conf import settings
from django.db import IntegrityError, transaction
from rest_framework import generics, permissions, status
from rest_framework.response import Response
from rest_framework.views import APIView

from .models import Assinatura, EventoStripeProcessado, Plano
from .serializers import AssinaturaSerializer, CheckoutSerializer, PlanoSerializer

logger = logging.getLogger(__name__)


def _cliente_stripe():
    """Devolve o cliente Stripe configurado, ou None se a integração estiver off."""
    if not settings.STRIPE_SECRET_KEY:
        return None
    stripe.api_key = settings.STRIPE_SECRET_KEY
    return stripe


def _extrair_fim_periodo(subscription):
    """Lê o fim do período pago do objeto subscription do Stripe.

    O campo migrou de `current_period_end` (raiz) para os itens da assinatura
    em versões recentes da API; tratamos as duas formas.
    """
    timestamp = subscription.get('current_period_end')

    if timestamp is None:
        itens = (subscription.get('items') or {}).get('data') or []
        timestamps = [i.get('current_period_end') for i in itens if i.get('current_period_end')]
        timestamp = max(timestamps) if timestamps else None

    if timestamp is None:
        return None

    return datetime.fromtimestamp(timestamp, tz=dt_timezone.utc)


class ListarPlanosView(generics.ListAPIView):
    """Planos disponíveis para contratação. Público, para exibir a tabela de preços."""

    queryset = Plano.objects.filter(ativo=True)
    serializer_class = PlanoSerializer
    permission_classes = (permissions.AllowAny,)
    pagination_class = None


class MinhaAssinaturaView(APIView):
    """Status da assinatura do usuário logado, consumido pelo frontend."""

    permission_classes = (permissions.IsAuthenticated,)

    def get(self, request):
        assinatura = Assinatura.objects.filter(usuario=request.user).select_related('plano').first()

        if assinatura is None:
            return Response(
                {'status': Assinatura.Status.INATIVA, 'plano': None,
                 'data_expiracao': None, 'esta_ativa': False}
            )

        return Response(AssinaturaSerializer(assinatura).data)


class CheckoutView(APIView):
    permission_classes = (permissions.IsAuthenticated,)

    def post(self, request):
        cliente = _cliente_stripe()
        if cliente is None:
            return Response(
                {'detail': 'Pagamentos não estão configurados no servidor.'},
                status=status.HTTP_503_SERVICE_UNAVAILABLE,
            )

        serializer = CheckoutSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        plano = serializer.validated_data['plano']

        try:
            sessao = cliente.checkout.Session.create(
                mode='subscription',
                line_items=[{'price': plano.stripe_price_id, 'quantity': 1}],
                success_url=settings.STRIPE_SUCCESS_URL,
                cancel_url=settings.STRIPE_CANCEL_URL,
                client_reference_id=str(request.user.pk),
                customer_email=request.user.email or None,
                metadata={'usuario_id': str(request.user.pk), 'plano_id': str(plano.pk)},
            )
        except stripe.StripeError:
            # Mensagens do gateway podem conter detalhes internos: não repassar.
            logger.exception('Falha ao criar sessão de checkout para o usuário %s', request.user.pk)
            return Response(
                {'detail': 'Não foi possível iniciar o pagamento. Tente novamente.'},
                status=status.HTTP_502_BAD_GATEWAY,
            )

        return Response({'checkout_url': sessao.url})


class StripeWebhookView(APIView):
    """Recebe eventos do Stripe.

    Autenticado pela assinatura HMAC do próprio Stripe, não por JWT — por isso
    AllowAny e sem authentication_classes. DRF já aplica csrf_exempt em APIView.
    """

    authentication_classes = ()
    permission_classes = (permissions.AllowAny,)

    def post(self, request):
        if not settings.STRIPE_WEBHOOK_SECRET:
            logger.error('Webhook do Stripe recebido, mas STRIPE_WEBHOOK_SECRET não está definida.')
            return Response(status=status.HTTP_503_SERVICE_UNAVAILABLE)

        assinatura_header = request.META.get('HTTP_STRIPE_SIGNATURE')

        try:
            evento = stripe.Webhook.construct_event(
                request.body, assinatura_header, settings.STRIPE_WEBHOOK_SECRET
            )
        except (ValueError, stripe.SignatureVerificationError):
            logger.warning('Webhook do Stripe com assinatura inválida foi rejeitado.')
            return Response(status=status.HTTP_400_BAD_REQUEST)

        # Idempotência: o Stripe reentrega o mesmo evento. A criação do registro
        # é a trava — se já existe, o evento já foi tratado.
        try:
            with transaction.atomic():
                EventoStripeProcessado.objects.create(
                    evento_id=evento['id'], tipo=evento['type']
                )
        except IntegrityError:
            logger.info('Evento %s já processado; ignorando reentrega.', evento['id'])
            return Response(status=status.HTTP_200_OK)

        try:
            self._tratar_evento(evento)
        except Exception:
            # Devolve 500 para que o Stripe reentregue, mas libera a trava de
            # idempotência para que a reentrega possa de fato ser processada.
            EventoStripeProcessado.objects.filter(evento_id=evento['id']).delete()
            logger.exception('Erro ao tratar evento %s do Stripe', evento['id'])
            return Response(status=status.HTTP_500_INTERNAL_SERVER_ERROR)

        return Response(status=status.HTTP_200_OK)

    def _tratar_evento(self, evento):
        tipo = evento['type']
        objeto = evento['data']['object']

        if tipo == 'checkout.session.completed':
            self._ativar_assinatura(objeto)
        elif tipo in ('customer.subscription.updated', 'customer.subscription.created'):
            self._sincronizar_assinatura(objeto)
        elif tipo == 'customer.subscription.deleted':
            Assinatura.objects.filter(stripe_subscription_id=objeto.get('id')).update(
                status=Assinatura.Status.CANCELADA
            )
        else:
            logger.debug('Evento %s ignorado (sem tratamento definido).', tipo)

    def _ativar_assinatura(self, sessao):
        usuario_id = sessao.get('client_reference_id')
        subscription_id = sessao.get('subscription')

        if not usuario_id or not subscription_id:
            logger.warning('checkout.session.completed sem usuário ou assinatura; ignorado.')
            return

        # O usuário pode ter sido removido entre o checkout e o webhook.
        from django.contrib.auth import get_user_model

        if not get_user_model().objects.filter(pk=usuario_id).exists():
            logger.warning('Webhook referencia usuário inexistente %s; ignorado.', usuario_id)
            return

        subscription = stripe.Subscription.retrieve(subscription_id)
        self._sincronizar_assinatura(subscription, usuario_id=usuario_id, sessao=sessao)

    def _sincronizar_assinatura(self, subscription, usuario_id=None, sessao=None):
        subscription_id = subscription.get('id')

        assinatura = Assinatura.objects.filter(stripe_subscription_id=subscription_id).first()

        if assinatura is None:
            if usuario_id is None:
                usuario_id = (subscription.get('metadata') or {}).get('usuario_id')
            if usuario_id is None:
                logger.warning(
                    'Assinatura %s sem usuário identificável; ignorada.', subscription_id
                )
                return
            assinatura, _ = Assinatura.objects.get_or_create(usuario_id=usuario_id)

        assinatura.stripe_subscription_id = subscription_id
        assinatura.stripe_customer_id = subscription.get('customer') or (
            sessao.get('customer') if sessao else None
        )
        assinatura.data_expiracao = _extrair_fim_periodo(subscription)

        estado = subscription.get('status')
        if estado in ('active', 'trialing'):
            assinatura.status = Assinatura.Status.ATIVA
        elif estado in ('canceled', 'incomplete_expired'):
            assinatura.status = Assinatura.Status.CANCELADA
        else:
            # past_due, unpaid, incomplete: acesso suspenso até regularizar.
            assinatura.status = Assinatura.Status.INATIVA

        plano = self._resolver_plano(subscription)
        if plano is not None:
            assinatura.plano = plano

        assinatura.save()

    @staticmethod
    def _resolver_plano(subscription):
        itens = (subscription.get('items') or {}).get('data') or []
        for item in itens:
            price_id = (item.get('price') or {}).get('id')
            if price_id:
                plano = Plano.objects.filter(stripe_price_id=price_id).first()
                if plano is not None:
                    return plano
        return None
