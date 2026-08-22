from django.urls import path
from rest_framework_simplejwt.views import TokenObtainPairView, TokenRefreshView
from .views import MinhaContaView, RegisterView, RotinaEstudoView, TrocarSenhaView

urlpatterns = [
    path('register/', RegisterView.as_view(), name='auth_register'),
    path('login/', TokenObtainPairView.as_view(), name='token_obtain_pair'),
    path('token/refresh/', TokenRefreshView.as_view(), name='token_refresh'),
    path('rotina/', RotinaEstudoView.as_view(), name='rotina_estudo'),
    path('minha-conta/', MinhaContaView.as_view(), name='minha_conta'),
    path('trocar-senha/', TrocarSenhaView.as_view(), name='trocar_senha'),
]