from django.conf import settings
from rest_framework import serializers

from .models import Cargo, Concurso, Disciplina, Edital, Topico

# Assinatura binária obrigatória de um arquivo PDF.
ASSINATURA_PDF = b'%PDF-'


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
    """Usado no seletor de cargo do frontend."""

    edital_ano = serializers.IntegerField(source='edital.ano', read_only=True)
    orgao = serializers.CharField(source='edital.concurso.orgao', read_only=True)
    concurso = serializers.CharField(source='edital.concurso.nome', read_only=True)

    class Meta:
        model = Cargo
        fields = ('id', 'nome', 'vagas', 'orgao', 'concurso', 'edital_ano')


class ProcessarEditalSerializer(serializers.Serializer):
    """Valida a entrada do upload antes de qualquer chamada paga à IA."""

    file = serializers.FileField()
    cargo_id = serializers.PrimaryKeyRelatedField(
        queryset=Cargo.objects.select_related('edital__concurso'),
        source='cargo',
    )

    def validate_file(self, arquivo):
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
