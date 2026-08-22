from django.urls import path
from .views import ProcessarEditalPDFView, ListarCargosView

urlpatterns = [
    path('cargos/', ListarCargosView.as_view(), name='listar_cargos'),
    path('processar-pdf/', ProcessarEditalPDFView.as_view(), name='processar_edital_pdf'),
]