from django.contrib import admin

from .models import ProgressoTopico, SessaoDeEstudo


@admin.register(ProgressoTopico)
class ProgressoTopicoAdmin(admin.ModelAdmin):
    list_display = ('usuario', 'topico', 'status', 'nivel_dominio', 'data_proxima_revisao')
    list_filter = ('status', 'nivel_dominio')
    search_fields = ('usuario__username', 'topico__nome')
    autocomplete_fields = ('usuario', 'topico')
    list_select_related = ('usuario', 'topico')
    date_hierarchy = 'data_proxima_revisao'


@admin.register(SessaoDeEstudo)
class SessaoDeEstudoAdmin(admin.ModelAdmin):
    list_display = (
        'usuario', 'topico', 'tempo_minutos',
        'questoes_feitas', 'questoes_acertadas', 'data_sessao',
    )
    search_fields = ('usuario__username', 'topico__nome')
    autocomplete_fields = ('usuario', 'topico')
    list_select_related = ('usuario', 'topico')
    date_hierarchy = 'data_sessao'
