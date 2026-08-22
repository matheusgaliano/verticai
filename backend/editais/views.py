import json
import logging

from rest_framework import generics, permissions, status
from rest_framework.parsers import FormParser, MultiPartParser
from rest_framework.response import Response
from rest_framework.views import APIView

from assinaturas.permissions import IsSubscriber

from .models import Cargo
from .serializers import (
    CargoSerializer,
    ConfirmarEditalSerializer,
    DetalharCargoSerializer,
    IdentificarEditalSerializer,
)
from .services import (
    ProcessamentoEditalError,
    detalhar_disciplinas_do_cargo,
    extrair_texto_pdf,
    identificar_concurso_e_cargos,
    persistir_edital_processado,
)

logger = logging.getLogger(__name__)


class ListarCargosView(generics.ListAPIView):
    """Catálogo de cargos já cadastrados (alimenta um <select>, não uma tabela)."""

    serializer_class = CargoSerializer
    permission_classes = (permissions.IsAuthenticated,)
    pagination_class = None

    def get_queryset(self):
        queryset = Cargo.objects.select_related('edital__concurso')

        busca = self.request.query_params.get('busca')
        if busca:
            queryset = queryset.filter(nome__icontains=busca)

        return queryset


def _resposta_erro_processamento(exc, contexto):
    logger.info('Falha esperada ao processar edital (%s): %s', contexto, exc)
    return Response({'detail': str(exc)}, status=status.HTTP_422_UNPROCESSABLE_ENTITY)


def _resposta_erro_inesperado(contexto):
    logger.exception('Erro inesperado ao processar edital (%s)', contexto)
    return Response(
        {'detail': 'Falha interna ao processar o edital.'},
        status=status.HTTP_500_INTERNAL_SERVER_ERROR,
    )


class IdentificarEditalView(APIView):
    """Etapa 1: recebe o PDF e identifica o concurso e os cargos nele descritos.

    Não grava nada no banco — o Cargo só passa a existir depois que o
    usuário escolhe qual dos cargos identificados quer prestar (ver
    DetalharCargoEditalView e ConfirmarEditalView).
    """

    parser_classes = (MultiPartParser, FormParser)
    permission_classes = (permissions.IsAuthenticated, IsSubscriber)
    throttle_scope = 'processar_edital'

    def post(self, request, *args, **kwargs):
        serializer = IdentificarEditalSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        pdf_file = serializer.validated_data['file']

        try:
            texto = extrair_texto_pdf(pdf_file)
            dados = identificar_concurso_e_cargos(texto)
        except ProcessamentoEditalError as exc:
            return _resposta_erro_processamento(exc, 'identificar')
        except Exception:
            return _resposta_erro_inesperado('identificar')

        return Response(dados, status=status.HTTP_200_OK)


class DetalharCargoEditalView(APIView):
    """Etapa 2: recebe o mesmo PDF + o cargo escolhido, extrai disciplinas/tópicos.

    Ainda não grava nada — o resultado é devolvido para revisão do usuário.
    """

    parser_classes = (MultiPartParser, FormParser)
    permission_classes = (permissions.IsAuthenticated, IsSubscriber)
    throttle_scope = 'processar_edital'

    def post(self, request, *args, **kwargs):
        serializer = DetalharCargoSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        pdf_file = serializer.validated_data['file']
        cargo_nome = serializer.validated_data['cargo_nome']

        try:
            texto = extrair_texto_pdf(pdf_file)
            dados = detalhar_disciplinas_do_cargo(texto, cargo_nome)
        except ProcessamentoEditalError as exc:
            return _resposta_erro_processamento(exc, 'detalhar')
        except Exception:
            return _resposta_erro_inesperado('detalhar')

        return Response(dados, status=status.HTTP_200_OK)


class ConfirmarEditalView(APIView):
    """Etapa 3: persiste o que já foi mostrado ao usuário nas etapas 1 e 2.

    Não chama IA — só grava Concurso/Edital/Cargo/Disciplina/Tópico.
    Idempotente: confirmar o mesmo cargo de novo atualiza em vez de duplicar.

    Multipart não tem uma convenção nativa para campos aninhados (listas de
    disciplinas com tópicos dentro), então o `file` vem como upload normal e
    o restante (concurso, disciplinas etc.) vem como um único campo `dados`
    contendo JSON.
    """

    parser_classes = (MultiPartParser, FormParser)
    permission_classes = (permissions.IsAuthenticated, IsSubscriber)

    def post(self, request, *args, **kwargs):
        try:
            dados_brutos = json.loads(request.data.get('dados', ''))
        except (TypeError, ValueError):
            return Response(
                {'detail': 'Campo "dados" ausente ou em formato inválido.'},
                status=status.HTTP_400_BAD_REQUEST,
            )

        if not isinstance(dados_brutos, dict):
            return Response(
                {'detail': 'Campo "dados" em formato inválido.'},
                status=status.HTTP_400_BAD_REQUEST,
            )

        dados_brutos['file'] = request.data.get('file')

        serializer = ConfirmarEditalSerializer(data=dados_brutos)
        serializer.is_valid(raise_exception=True)
        dados = serializer.validated_data

        try:
            resultado = persistir_edital_processado(
                concurso_dados=dados['concurso'],
                ano=dados['ano'],
                data_prova=dados.get('data_prova'),
                cargo_nome=dados['cargo_nome'],
                vagas=dados.get('vagas'),
                disciplinas=dados['disciplinas'],
                pdf_file=dados.get('file'),
            )
        except Exception:
            logger.exception('Erro inesperado ao confirmar edital')
            return Response(
                {'detail': 'Falha interna ao salvar o edital.'},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR,
            )

        return Response(
            {
                'detail': 'Edital confirmado e cadastrado com sucesso.',
                'cargo_id': resultado['cargo'].pk,
                'disciplinas': resultado['disciplinas'],
            },
            status=status.HTTP_201_CREATED,
        )
