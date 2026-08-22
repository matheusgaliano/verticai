from datetime import timedelta

from django.conf import settings
from django.db import models
from django.utils import timezone

from editais.models import Topico
from verticai.models_base import TimestampedModel

# Intervalos base de revisão espaçada, em dias, por nível de domínio.
INTERVALOS_BASE_DIAS = {1: 2, 2: 5, 3: 10}
INTERVALO_PADRAO_DIAS = 3

# A partir de quantos dias da prova o ciclo de revisões é encurtado, e por qual fator.
DIAS_PROVA_IMINENTE = 15
FATOR_PROVA_IMINENTE = 0.5


def calcular_intervalo_revisao(nivel_dominio, dias_ate_prova=None):
    """Retorna em quantos dias o tópico deve ser revisado novamente.

    Função pura: não toca no banco nem no relógio, para ser testável isoladamente.
    """
    dias = INTERVALOS_BASE_DIAS.get(nivel_dominio, INTERVALO_PADRAO_DIAS)

    if dias_ate_prova is not None and 0 < dias_ate_prova <= DIAS_PROVA_IMINENTE:
        dias = max(1, int(dias * FATOR_PROVA_IMINENTE))

    return dias


class ProgressoTopico(TimestampedModel):
    class Status(models.TextChoices):
        NAO_INICIADO = 'NAO_INICIADO', 'Não Iniciado'
        TEORIA = 'TEORIA', 'Teoria'
        REVISAO = 'REVISAO', 'Revisão'
        CONCLUIDO = 'CONCLUIDO', 'Concluído'

    class Dominio(models.IntegerChoices):
        DIFICIL = 1, 'Difícil'
        MEDIO = 2, 'Médio'
        FACIL = 3, 'Fácil'

    usuario = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='progressos',
    )
    topico = models.ForeignKey(Topico, on_delete=models.CASCADE, related_name='progressos')
    status = models.CharField(max_length=20, choices=Status.choices, default=Status.NAO_INICIADO)
    nivel_dominio = models.IntegerField(choices=Dominio.choices, null=True, blank=True)
    data_ultima_revisao = models.DateField(null=True, blank=True)
    data_proxima_revisao = models.DateField(null=True, blank=True)

    class Meta:
        verbose_name = 'Progresso de tópico'
        verbose_name_plural = 'Progressos de tópicos'
        ordering = ('data_proxima_revisao',)
        constraints = [
            models.UniqueConstraint(
                fields=('usuario', 'topico'),
                name='unico_progresso_por_usuario_topico',
            ),
        ]
        indexes = [
            # Consulta quente do plano diário: revisões vencidas do usuário.
            models.Index(
                fields=('usuario', 'data_proxima_revisao'),
                name='idx_progresso_usuario_revisao',
            ),
            models.Index(fields=('usuario', 'status'), name='idx_progresso_usuario_status'),
        ]

    def __str__(self):
        return f"{self.usuario.username} - {self.topico.nome} ({self.get_status_display()})"

    def agendar_revisao(self, nivel_dominio, hoje=None, data_prova=None):
        """Atualiza os campos de revisão espaçada in-place. NÃO persiste.

        A gravação fica a cargo de quem chama, para que possa acontecer dentro
        da mesma transação do registro da sessão de estudo.
        """
        hoje = hoje or timezone.localdate()
        dias_ate_prova = (data_prova - hoje).days if data_prova else None
        dias = calcular_intervalo_revisao(nivel_dominio, dias_ate_prova)

        self.nivel_dominio = nivel_dominio
        self.data_ultima_revisao = hoje
        self.data_proxima_revisao = hoje + timedelta(days=dias)

        # Um tópico já concluído continua entrando em revisão, mas não regride de status.
        if self.status != self.Status.CONCLUIDO:
            self.status = self.Status.REVISAO

        return self


class SessaoDeEstudo(TimestampedModel):
    usuario = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='sessoes',
    )
    topico = models.ForeignKey(Topico, on_delete=models.CASCADE, related_name='sessoes')
    tempo_minutos = models.PositiveIntegerField()
    questoes_feitas = models.PositiveIntegerField(default=0)
    questoes_acertadas = models.PositiveIntegerField(default=0)
    data_sessao = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = 'Sessão de estudo'
        verbose_name_plural = 'Sessões de estudo'
        ordering = ('-data_sessao',)
        constraints = [
            models.CheckConstraint(
                condition=models.Q(questoes_acertadas__lte=models.F('questoes_feitas')),
                name='acertos_nao_excedem_questoes',
            ),
            models.CheckConstraint(
                condition=models.Q(tempo_minutos__gt=0),
                name='tempo_sessao_positivo',
            ),
        ]
        indexes = [
            models.Index(fields=('usuario', '-data_sessao'), name='idx_sessao_usuario_data'),
        ]

    def __str__(self):
        return f"{self.usuario.username} - {self.topico.nome} ({self.tempo_minutos} min)"
