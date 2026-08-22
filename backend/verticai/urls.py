"""Roteamento raiz do projeto VerticAI."""

from django.conf import settings
from django.conf.urls.static import static
from django.contrib import admin
from django.urls import include, path

urlpatterns = [
    path('admin/', admin.site.urls),
    path('api/editais/', include('editais.urls')),
    path('api/usuarios/', include('usuarios.urls')),
    path('api/estudos/', include('estudos.urls')),
    path('api/assinaturas/', include('assinaturas.urls')),
]

if settings.DEBUG:
    # Em produção os uploads são servidos pelo servidor web / storage, não pelo Django.
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
