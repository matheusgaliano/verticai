from django.urls import path

from .views import (
    ConfirmarEditalView,
    DetalharCargoEditalView,
    IdentificarEditalView,
    ListarCargosView,
)

urlpatterns = [
    path('cargos/', ListarCargosView.as_view(), name='listar_cargos'),
    path('identificar-cargos/', IdentificarEditalView.as_view(), name='identificar_edital'),
    path('detalhar-cargo/', DetalharCargoEditalView.as_view(), name='detalhar_cargo_edital'),
    path('confirmar/', ConfirmarEditalView.as_view(), name='confirmar_edital'),
]
