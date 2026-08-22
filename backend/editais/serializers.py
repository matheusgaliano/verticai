from django.conf import settings
from rest_framework import serializers

from .models import Cargo, Concurso, Disciplina, Edital, Topico

# Assinatura binária obrigatória de um arquivo PDF.
ASSINATURA_PDF = b'%PDF-'


class ArquivoPDFField(serializers.FileField):
    """Campo de upload de PDF com validação de tamanho/tipo/assinatura binária.

    Reaproveitado pelas três etapas do processamento — o mesmo arquivo é
    reenviado a cada etapa, então a validação vive num único lugar.
    """

    def to_internal_value(self, arquivo):
        arquivo = super().to_internal_value(arquivo)

        limite = settings.MAX_UPLOAD_PDF_SIZE
        if arquivo.size > limite:
            raise serializers.ValidationError(
                f'Arquivo maior que o limite de {limite // (1024 * 1024)} MB.'
            )
        if arquivo.size == 0:
            raise serializers.ValidationError('Arquivo vazio.')

        if not arquivo.name.lower().endswith('.pdf'):
            raise serializers.ValidationError('Somente arquivos .pdf são aceitos.')

        # Não confia no nome nem no Content-Type informado pelo cliente:
        # confere a assinatura binária do arquivo.
        cabecalho = arquivo.read(len(ASSINATURA_PDF))
        arquivo.seek(0)
        if cabecalho != ASSINATURA_PDF:
            raise serializers.ValidationError('O arquivo enviado não é um PDF válido.')

        return arquivo


class ConcursoSerializer(serializers.ModelSerializer):
    class Meta:
        model = Concurso
        fields = ('id', 'nome', 'orgao', 'banca')


class EditalSerializer(serializers.ModelSerializer):
    concurso = ConcursoSerializer(read_only=True)

    class Meta:
        model = Edital
        fields = ('id', 'concurso', 'ano', 'data_prova')


class TopicoSerializer(serializers.ModelSerializer):
    class Meta:
        model = Topico
        fields = ('id', 'nome', 'ordem')


class DisciplinaSerializer(serializers.ModelSerializer):
    topicos = TopicoSerializer(many=True, read_only=True)

    class Meta:
        model = Disciplina
        fields = ('id', 'nome', 'peso', 'topicos')


class CargoSerializer(serializers.ModelSerializer):
    """Usado no catálogo geral de cargos (não mais no upload de edital)."""

    edital_ano = serializers.IntegerField(source='edital.ano', read_only=True)
    orgao = serializers.CharField(source='edital.concurso.orgao', read_only=True)
    concurso = serializers.CharField(source='edital.concurso.nome', read_only=True)

    class Meta:
        model = Cargo
        fields = ('id', 'nome', 'vagas', 'orgao', 'concurso', 'edital_ano')


# ---------------------------------------------------------------------------
# Fluxo de processamento de edital, em três etapas
# ---------------------------------------------------------------------------


class IdentificarEditalSerializer(serializers.Serializer):
    """Etapa 1: só o PDF — a IA identifica concurso e cargos mencionados."""

    file = ArquivoPDFField()


class DetalharCargoSerializer(serializers.Serializer):
    """Etapa 2: o mesmo PDF + o cargo escolhido dentre os identificados na etapa 1."""

    file = ArquivoPDFField()
    cargo_nome = serializers.CharField(max_length=150, trim_whitespace=True)


class ConcursoIdentificadoSerializer(serializers.Serializer):
    nome = serializers.CharField(max_length=200)
    orgao = serializers.CharField(max_length=100)
    banca = serializers.CharField(max_length=100, required=False, allow_null=True)


class DisciplinaExtraidaSerializer(serializers.Serializer):
    nome = serializers.CharField(max_length=150)
    peso = serializers.FloatField(default=1.0, min_value=0.1, max_value=10.0)
    topicos = serializers.ListField(
        child=serializers.CharField(max_length=255, allow_blank=False),
        allow_empty=False,
        max_length=300,
    )


class ConfirmarEditalSerializer(serializers.Serializer):
    """Etapa 3: confirma os dados já mostrados ao usuário nas etapas 1 e 2.

    Não chama a IA de novo — só persiste. O PDF é reenviado apenas para ser
    anexado ao Edital criado/reaproveitado.
    """

    file = ArquivoPDFField(required=False)
    concurso = ConcursoIdentificadoSerializer()
    ano = serializers.IntegerField(min_value=1900, max_value=2100)
    data_prova = serializers.DateField(required=False, allow_null=True)
    cargo_nome = serializers.CharField(max_length=150, trim_whitespace=True)
    vagas = serializers.IntegerField(required=False, min_value=1, default=1)
    disciplinas = DisciplinaExtraidaSerializer(many=True, allow_empty=False, max_length=60)
