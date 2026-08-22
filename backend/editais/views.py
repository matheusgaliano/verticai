import logging

from rest_framework import generics, permissions, status
from rest_framework.parsers import FormParser, MultiPartParser
from rest_framework.response import Response
from rest_framework.views import APIView

from assinaturas.permissions import IsSubscriber

from .models import Cargo
from .serializers import CargoSerializer, ProcessarEditalSerializer
from .services import (
    ProcessamentoEditalError,
    extrair_texto_pdf,
    processar_edital_com_ia,
    salvar_disciplinas_e_topicos,
)

logger = logging.getLogger(__name__)


class ListarCargosView(generics.ListAPIView):
    """Catálogo de cargos disponíveis para seleção. Paginado e pesquisável."""

    serializer_class = CargoSerializer
    permission_classes = (permissions.IsAuthenticated,)

    def get_queryset(self):
        queryset = Cargo.objects.select_related('edital__concurso')

        busca = self.request.query_params.get('busca')
        if busca:
            queryset = queryset.filter(nome__icontains=busca)

        return queryset


class ProcessarEditalPDFView(APIView):
    """Extrai o conteúdo programático de um edital em PDF usando IA.

    Operação cara (chamada paga ao Gemini): exige assinatura ativa e é limitada
    por throttling. A gravação é idempotente — reprocessar não duplica dados.
    """

    parser_classes = (MultiPartParser, FormParser)
    permission_classes = (permissions.IsAuthenticated, IsSubscriber)
    throttle_scope = 'processar_edital'

    def post(self, request, *args, **kwargs):
        serializer = ProcessarEditalSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        pdf_file = serializer.validated_data['file']
        cargo = serializer.validated_data['cargo']

        try:
            texto = extrair_texto_pdf(pdf_file)
            dados_estruturados = processar_edital_com_ia(texto)
            resumo = salvar_disciplinas_e_topicos(cargo, dados_estruturados)
        except ProcessamentoEditalError as exc:
            # Mensagem de domínio: segura para exibir ao usuário.
            return Response({'detail': str(exc)}, status=status.HTTP_422_UNPROCESSABLE_ENTITY)
        except Exception:
            # Falha inesperada: registra o traceback no servidor e devolve uma
            # mensagem genérica, sem vazar internals.
            logger.exception('Erro inesperado ao processar edital do cargo %s', cargo.pk)
            return Response(
                {'detail': 'Falha interna ao processar o edital.'},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR,
            )

        # Guarda o PDF de origem no edital, para auditoria e reprocessamento.
        edital = cargo.edital
        if not edital.arquivo_pdf:
            pdf_file.seek(0)
            edital.arquivo_pdf.save(pdf_file.name, pdf_file, save=True)

        return Response(
            {
                'detail': 'Edital processado com sucesso.',
                'cargo_id': cargo.pk,
                'disciplinas': resumo,
            },
            status=status.HTTP_201_CREATED,
        )
