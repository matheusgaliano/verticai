from django.db import models

from verticai.models_base import TimestampedModel


class Concurso(TimestampedModel):
    nome = models.CharField(max_length=200)
    orgao = models.CharField(max_length=100)
    banca = models.CharField(max_length=100, blank=True, null=True)

    class Meta:
        verbose_name = 'Concurso'
        verbose_name_plural = 'Concursos'
        ordering = ('orgao', 'nome')
        constraints = [
            models.UniqueConstraint(fields=('orgao', 'nome'), name='unico_concurso_por_orgao'),
        ]

    def __str__(self):
        return f"{self.orgao} - {self.nome}"


class Edital(TimestampedModel):
    concurso = models.ForeignKey(Concurso, on_delete=models.CASCADE, related_name='editais')
    ano = models.PositiveIntegerField()
    data_prova = models.DateField(null=True, blank=True)
    arquivo_pdf = models.FileField(upload_to='editais_pdfs/%Y/%m/', null=True, blank=True)

    class Meta:
        verbose_name = 'Edital'
        verbose_name_plural = 'Editais'
        ordering = ('-ano',)
        constraints = [
            models.UniqueConstraint(fields=('concurso', 'ano'), name='unico_edital_por_ano'),
        ]

    def __str__(self):
        return f"Edital {self.ano} - {self.concurso.orgao}"


class Cargo(TimestampedModel):
    edital = models.ForeignKey(Edital, on_delete=models.CASCADE, related_name='cargos')
    nome = models.CharField(max_length=150)
    vagas = models.PositiveIntegerField(default=1)

    class Meta:
        verbose_name = 'Cargo'
        verbose_name_plural = 'Cargos'
        ordering = ('nome',)
        constraints = [
            models.UniqueConstraint(fields=('edital', 'nome'), name='unico_cargo_por_edital'),
        ]

    def __str__(self):
        return f"{self.nome} ({self.edital})"


class Disciplina(TimestampedModel):
    cargo = models.ForeignKey(Cargo, on_delete=models.CASCADE, related_name='disciplinas')
    nome = models.CharField(max_length=150)
    peso = models.DecimalField(max_digits=4, decimal_places=2, default=1.0)

    class Meta:
        verbose_name = 'Disciplina'
        verbose_name_plural = 'Disciplinas'
        ordering = ('nome',)
        constraints = [
            models.UniqueConstraint(fields=('cargo', 'nome'), name='unica_disciplina_por_cargo'),
        ]

    def __str__(self):
        return f"{self.nome} - {self.cargo.nome}"


class Topico(TimestampedModel):
    disciplina = models.ForeignKey(Disciplina, on_delete=models.CASCADE, related_name='topicos')
    nome = models.CharField(max_length=255)
    ordem = models.PositiveIntegerField(default=1)

    class Meta:
        verbose_name = 'Tópico'
        verbose_name_plural = 'Tópicos'
        ordering = ('disciplina', 'ordem')
        indexes = [
            models.Index(fields=('disciplina', 'ordem'), name='idx_topico_disciplina_ordem'),
        ]
        constraints = [
            models.UniqueConstraint(fields=('disciplina', 'nome'), name='unico_topico_por_disciplina'),
        ]

    def __str__(self):
        return f"{self.ordem}. {self.nome}"
