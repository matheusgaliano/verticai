from django.conf import settings
from django.core.validators import MaxValueValidator, MinValueValidator
from django.db import models

from editais.models import Cargo
from verticai.models_base import TimestampedModel


class Perfil(TimestampedModel):
    """Dados de conta que não pertencem ao User nativo do Django."""

    usuario = models.OneToOneField(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='perfil',
    )
    telefone = models.CharField(max_length=20, blank=True)
    foto_perfil = models.ImageField(upload_to='perfis/%Y/%m/', null=True, blank=True)

    class Meta:
        verbose_name = 'Perfil'
        verbose_name_plural = 'Perfis'

    def __str__(self):
        return f"Perfil de {self.usuario.username}"


class Preparacao(TimestampedModel):
    usuario = models.OneToOneField(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='preparacao',
    )
    cargo = models.ForeignKey(
        Cargo,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='preparacoes',
    )
    data_inicio = models.DateField(auto_now_add=True)
    meta_horas_semanais = models.PositiveIntegerField(
        default=20,
        validators=[MinValueValidator(1), MaxValueValidator(168)],
    )

    class Meta:
        verbose_name = 'Preparação'
        verbose_name_plural = 'Preparações'
        ordering = ('-criado_em',)

    def __str__(self):
        return f"Preparação de {self.usuario.username}"


class Disponibilidade(TimestampedModel):
    DIAS_SEMANA = [
        ('SEG', 'Segunda-feira'),
        ('TER', 'Terça-feira'),
        ('QUA', 'Quarta-feira'),
        ('QUI', 'Quinta-feira'),
        ('SEX', 'Sexta-feira'),
        ('SAB', 'Sábado'),
        ('DOM', 'Domingo'),
    ]

    # Ordem de exibição/consulta que respeita a semana, não o alfabeto.
    ORDEM_DIAS = {codigo: indice for indice, (codigo, _) in enumerate(DIAS_SEMANA)}

    preparacao = models.ForeignKey(
        Preparacao,
        on_delete=models.CASCADE,
        related_name='disponibilidades',
    )
    dia_semana = models.CharField(max_length=3, choices=DIAS_SEMANA)
    horas_disponiveis = models.DecimalField(
        max_digits=4,
        decimal_places=2,
        default=0,
        validators=[MinValueValidator(0), MaxValueValidator(24)],
    )

    class Meta:
        verbose_name = 'Disponibilidade'
        verbose_name_plural = 'Disponibilidades'
        constraints = [
            models.UniqueConstraint(
                fields=('preparacao', 'dia_semana'),
                name='unica_disponibilidade_por_dia',
            ),
        ]

    def __str__(self):
        return (
            f"{self.preparacao.usuario.username} - "
            f"{self.get_dia_semana_display()}: {self.horas_disponiveis}h"
        )
