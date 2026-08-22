from django.contrib.auth import get_user_model
from rest_framework import generics, permissions, status
from rest_framework.parsers import FormParser, JSONParser, MultiPartParser
from rest_framework.response import Response
from rest_framework.views import APIView

from .models import Perfil, Preparacao
from .serializers import (
    MinhaContaSerializer,
    PreparacaoSerializer,
    TrocarSenhaSerializer,
    UserRegisterSerializer,
)

User = get_user_model()


class RegisterView(generics.CreateAPIView):
    queryset = User.objects.all()
    serializer_class = UserRegisterSerializer
    permission_classes = (permissions.AllowAny,)
    throttle_scope = 'registro'


class RotinaEstudoView(generics.RetrieveUpdateAPIView):
    """Rotina de estudos do usuário logado.

    É um recurso singleton por usuário: GET devolve (criando se necessário) e
    PUT/PATCH atualiza. Não há POST — criar é responsabilidade do get_or_create.
    """

    serializer_class = PreparacaoSerializer
    permission_classes = (permissions.IsAuthenticated,)

    def get_object(self):
        preparacao, _ = Preparacao.objects.select_related('cargo__edital__concurso') \
            .get_or_create(usuario=self.request.user)
        return preparacao


class MinhaContaView(generics.RetrieveUpdateAPIView):
    """Dados da conta do usuário logado (username, e-mail, telefone, foto)."""

    serializer_class = MinhaContaSerializer
    permission_classes = (permissions.IsAuthenticated,)
    parser_classes = (JSONParser, MultiPartParser, FormParser)

    def get_object(self):
        # Garante que o Perfil exista antes de serializar (o serializer lê
        # `instance.perfil` via source pontilhado).
        Perfil.objects.get_or_create(usuario=self.request.user)
        return self.request.user


class TrocarSenhaView(APIView):
    permission_classes = (permissions.IsAuthenticated,)
    throttle_scope = 'trocar_senha'

    def post(self, request, *args, **kwargs):
        serializer = TrocarSenhaSerializer(data=request.data, context={'request': request})
        serializer.is_valid(raise_exception=True)
        serializer.save()
        return Response({'detail': 'Senha alterada com sucesso.'}, status=status.HTTP_200_OK)
