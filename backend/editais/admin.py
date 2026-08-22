from django.contrib import admin

from .models import Cargo, Concurso, Disciplina, Edital, Topico


class EditalInline(admin.TabularInline):
    model = Edital
    extra = 0
    fields = ('ano', 'data_prova', 'arquivo_pdf')


class CargoInline(admin.TabularInline):
    model = Cargo
    extra = 0
    fields = ('nome', 'vagas')


class TopicoInline(admin.TabularInline):
    model = Topico
    extra = 0
    fields = ('ordem', 'nome')
    ordering = ('ordem',)


@admin.register(Concurso)
class ConcursoAdmin(admin.ModelAdmin):
    list_display = ('orgao', 'nome', 'banca')
    list_filter = ('banca',)
    search_fields = ('nome', 'orgao', 'banca')
    inlines = (EditalInline,)


@admin.register(Edital)
class EditalAdmin(admin.ModelAdmin):
    list_display = ('concurso', 'ano', 'data_prova', 'arquivo_pdf')
    list_filter = ('ano',)
    search_fields = ('concurso__nome', 'concurso__orgao')
    autocomplete_fields = ('concurso',)
    list_select_related = ('concurso',)
    inlines = (CargoInline,)


@admin.register(Cargo)
class CargoAdmin(admin.ModelAdmin):
    list_display = ('nome', 'edital', 'vagas', 'total_disciplinas')
    search_fields = ('nome', 'edital__concurso__nome', 'edital__concurso__orgao')
    autocomplete_fields = ('edital',)
    list_select_related = ('edital__concurso',)

    @admin.display(description='Disciplinas')
    def total_disciplinas(self, obj):
        return obj.disciplinas.count()


@admin.register(Disciplina)
class DisciplinaAdmin(admin.ModelAdmin):
    list_display = ('nome', 'cargo', 'peso', 'total_topicos')
    search_fields = ('nome', 'cargo__nome')
    autocomplete_fields = ('cargo',)
    list_select_related = ('cargo',)
    inlines = (TopicoInline,)

    @admin.display(description='Tópicos')
    def total_topicos(self, obj):
        return obj.topicos.count()


@admin.register(Topico)
class TopicoAdmin(admin.ModelAdmin):
    list_display = ('ordem', 'nome', 'disciplina')
    search_fields = ('nome', 'disciplina__nome')
    autocomplete_fields = ('disciplina',)
    list_select_related = ('disciplina',)
    ordering = ('disciplina', 'ordem')
