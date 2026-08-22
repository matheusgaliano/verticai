from rest_framework import serializers

from editais.models import Topico
from usuarios.models import Preparacao

from .models import ProgressoTopico, SessaoDeEstudo
from .services import registrar_sessao


class ItemPlanoEstudoSerializer(serializers.Serializer):
    """Contrato de um item do plano diário (dados montados em memória, não um model)."""

    topico_id = serializers.IntegerField(read_only=True)
    topico_nome = serializers.CharField(read_only=True)
    disciplina_nome = serializers.CharField(read_only=True)
    tipo_tarefa = serializers.CharField(read_only=True)
    prioridade = serializers.FloatField(read_only=True)
    tempo_sugerido_minutos = serializers.IntegerField(read_only=True)


class ProgressoTopicoSerializer(serializers.ModelSerializer):
    topico_nome = serializers.CharField(source='topico.nome', read_only=True)

    class Meta:
        model = ProgressoTopico
        fields = (
            'id', 'topico', 'topico_nome', 'status', 'nivel_dominio',
            'data_ultima_revisao', 'data_proxima_revisao',
        )
        read_only_fields = ('id', 'topico', 'data_ultima_revisao', 'data_proxima_revisao')


class RegistrarSessaoSerializer(serializers.ModelSerializer):
    """Registra uma sessão de estudo e, com `nivel_dominio`, reagenda a revisão."""

    nivel_dominio = serializers.ChoiceField(
        choices=ProgressoTopico.Dominio.choices,
        write_only=True,
        required=False,
        allow_null=True,
        help_text='Autoavaliação do domínio (1 difícil, 2 médio, 3 fácil). '
                  'Quando informado, agenda a próxima revisão.',
    )
    data_proxima_revisao = serializers.SerializerMethodField()

    class Meta:
        model = SessaoDeEstudo
        fields = (
            'id', 'topico', 'tempo_minutos', 'questoes_feitas',
            'questoes_acertadas', 'data_sessao', 'nivel_dominio',
            'data_proxima_revisao',
        )
        read_only_fields = ('id', 'data_sessao')

    def get_data_proxima_revisao(self, sessao):
        progresso = ProgressoTopico.objects.filter(
            usuario=sessao.usuario, topico=sessao.topico
        ).only('data_proxima_revisao').first()
        return progresso.data_proxima_revisao if progresso else None

    def validate_topico(self, topico):
        """Impede registrar sessão em tópico fora do cargo em preparação do usuário."""
        usuario = self.context['request'].user

        preparacao = Preparacao.objects.filter(usuario=usuario).only('cargo_id').first()
        if preparacao is None or preparacao.cargo_id is None:
            raise serializers.ValidationError(
                'Selecione um cargo na sua rotina de estudos antes de registrar sessões.'
            )

        pertence = Topico.objects.filter(
            pk=topico.pk, disciplina__cargo_id=preparacao.cargo_id
        ).exists()
        if not pertence:
            raise serializers.ValidationError(
                'Este tópico não pertence ao cargo em preparação.'
            )

        return topico

    def validate(self, attrs):
        feitas = attrs.get('questoes_feitas', 0)
        acertadas = attrs.get('questoes_acertadas', 0)
        if acertadas > feitas:
            raise serializers.ValidationError(
                {'questoes_acertadas': 'Não pode ser maior que o total de questões feitas.'}
            )
        if attrs.get('tempo_minutos', 0) <= 0:
            raise serializers.ValidationError(
                {'tempo_minutos': 'A sessão precisa ter duração maior que zero.'}
            )
        return attrs

    def create(self, validated_data):
        nivel_dominio = validated_data.pop('nivel_dominio', None)
        return registrar_sessao(
            usuario=self.context['request'].user,
            nivel_dominio=nivel_dominio,
            **validated_data,
        )
