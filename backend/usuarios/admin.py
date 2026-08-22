from django.contrib import admin

from .models import Disponibilidade, Perfil, Preparacao


@admin.register(Perfil)
class PerfilAdmin(admin.ModelAdmin):
    list_display = ('usuario', 'telefone')
    search_fields = ('usuario__username', 'usuario__email', 'telefone')
    autocomplete_fields = ('usuario',)
    list_select_related = ('usuario',)


class DisponibilidadeInline(admin.TabularInline):
    model = Disponibilidade
    extra = 0
    fields = ('dia_semana', 'horas_disponiveis')


@admin.register(Preparacao)
class PreparacaoAdmin(admin.ModelAdmin):
    list_display = ('usuario', 'cargo', 'data_inicio', 'meta_horas_semanais')
    search_fields = ('usuario__username', 'usuario__email', 'cargo__nome')
    autocomplete_fields = ('usuario', 'cargo')
    list_select_related = ('usuario', 'cargo')
    inlines = (DisponibilidadeInline,)


@admin.register(Disponibilidade)
class DisponibilidadeAdmin(admin.ModelAdmin):
    list_display = ('preparacao', 'dia_semana', 'horas_disponiveis')
    list_filter = ('dia_semana',)
    search_fields = ('preparacao__usuario__username',)
    list_select_related = ('preparacao__usuario',)
