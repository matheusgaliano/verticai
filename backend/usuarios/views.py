from django.contrib.auth import get_user_model
from rest_framework import generics, permissions

from .models import Preparacao
from .serializers import PreparacaoSerializer, UserRegisterSerializer

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
