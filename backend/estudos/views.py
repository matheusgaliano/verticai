from rest_framework import generics, permissions, status
from rest_framework.response import Response
from rest_framework.views import APIView

from assinaturas.permissions import IsSubscriber

from .models import ProgressoTopico, SessaoDeEstudo
from .serializers import (
    ItemPlanoEstudoSerializer,
    ProgressoTopicoSerializer,
    RegistrarSessaoSerializer,
)
from .services import PreparacaoNaoConfiguradaError, montar_plano_diario


class PlanoDiarioView(APIView):
    """Plano de estudos do dia. Recurso premium."""

    permission_classes = (permissions.IsAuthenticated, IsSubscriber)

    def get(self, request):
        try:
            resultado = montar_plano_diario(request.user)
        except PreparacaoNaoConfiguradaError as exc:
            return Response({'detail': str(exc)}, status=status.HTTP_409_CONFLICT)

        return Response({
            'data': resultado['data'],
            'minutos_disponiveis': resultado['minutos_disponiveis'],
            'minutos_alocados': resultado['minutos_alocados'],
            'plano': ItemPlanoEstudoSerializer(resultado['plano'], many=True).data,
        })


class SessaoDeEstudoListCreateView(generics.ListCreateAPIView):
    """Registra e lista as sessões de estudo do próprio usuário."""

    serializer_class = RegistrarSessaoSerializer
    permission_classes = (permissions.IsAuthenticated, IsSubscriber)

    def get_queryset(self):
        return (
            SessaoDeEstudo.objects
            .filter(usuario=self.request.user)
            .select_related('topico__disciplina')
        )


class ProgressoTopicoListView(generics.ListAPIView):
    """Progresso do usuário, opcionalmente filtrado por status."""

    serializer_class = ProgressoTopicoSerializer
    permission_classes = (permissions.IsAuthenticated, IsSubscriber)

    def get_queryset(self):
        queryset = (
            ProgressoTopico.objects
            .filter(usuario=self.request.user)
            .select_related('topico__disciplina')
        )

        filtro_status = self.request.query_params.get('status')
        if filtro_status:
            queryset = queryset.filter(status=filtro_status)

        return queryset


class ProgressoTopicoUpdateView(generics.UpdateAPIView):
    """Permite marcar um tópico como concluído (ou voltar atrás), sem sessão."""

    serializer_class = ProgressoTopicoSerializer
    permission_classes = (permissions.IsAuthenticated, IsSubscriber)
    lookup_field = 'topico_id'
    lookup_url_kwarg = 'topico_id'

    def get_queryset(self):
        return ProgressoTopico.objects.filter(usuario=self.request.user)

    def get_object(self):
        progresso, _ = ProgressoTopico.objects.get_or_create(
            usuario=self.request.user,
            topico_id=self.kwargs['topico_id'],
        )
        return progresso
