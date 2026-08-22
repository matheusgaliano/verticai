"""Bases de model compartilhadas entre os apps."""

from django.db import models


class TimestampedModel(models.Model):
    """Adiciona carimbos de criação e atualização a um model."""

    criado_em = models.DateTimeField(auto_now_add=True)
    atualizado_em = models.DateTimeField(auto_now=True)

    class Meta:
        abstract = True
