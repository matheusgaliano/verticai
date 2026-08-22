from django.urls import path

from .views import (
    PlanoDiarioView,
    ProgressoTopicoListView,
    ProgressoTopicoUpdateView,
    SessaoDeEstudoListCreateView,
)

urlpatterns = [
    path('plano-diario/', PlanoDiarioView.as_view(), name='plano_diario'),
    path('sessoes/', SessaoDeEstudoListCreateView.as_view(), name='sessoes'),
    path('progresso/', ProgressoTopicoListView.as_view(), name='progresso_lista'),
    path(
        'progresso/<int:topico_id>/',
        ProgressoTopicoUpdateView.as_view(),
        name='progresso_detalhe',
    ),
]
