"""
Django settings for verticai project.

Toda configuração sensível ou dependente de ambiente vem de variáveis de
ambiente (carregadas de um arquivo .env em desenvolvimento). Veja .env.example
para a lista completa de variáveis suportadas.
"""

import os
from datetime import timedelta
from pathlib import Path

from dotenv import load_dotenv

BASE_DIR = Path(__file__).resolve().parent.parent

# Carrega o .env local. Em produção as variáveis vêm do próprio ambiente e o
# arquivo simplesmente não existe (load_dotenv é no-op nesse caso).
# override=True: o .env é a fonte da verdade em dev — sem isso, uma variável
# já presente no ambiente do processo (ex.: sobrevivendo a um autoreload)
# vence o arquivo, e editar o .env parece não fazer efeito até matar o
# processo inteiro.
load_dotenv(BASE_DIR / '.env', override=True)


def env_bool(nome, padrao=False):
    valor = os.environ.get(nome)
    if valor is None:
        return padrao
    return valor.strip().lower() in ('1', 'true', 'yes', 'on', 'sim')


def env_list(nome, padrao=()):
    valor = os.environ.get(nome)
    if not valor:
        return list(padrao)
    return [item.strip() for item in valor.split(',') if item.strip()]


# ---------------------------------------------------------------------------
# Segurança
# ---------------------------------------------------------------------------

SECRET_KEY = os.environ.get('DJANGO_SECRET_KEY')
if not SECRET_KEY:
    raise RuntimeError(
        'DJANGO_SECRET_KEY não definida. Copie backend/.env.example para '
        'backend/.env e preencha a variável (veja o README para gerar uma chave).'
    )

# Padrão seguro: produção. Desenvolvimento precisa optar por DEBUG explicitamente.
DEBUG = env_bool('DJANGO_DEBUG', False)

ALLOWED_HOSTS = env_list('DJANGO_ALLOWED_HOSTS', ['localhost', '127.0.0.1'] if DEBUG else [])

if not DEBUG and not ALLOWED_HOSTS:
    raise RuntimeError('DJANGO_ALLOWED_HOSTS é obrigatória quando DJANGO_DEBUG=False.')


# ---------------------------------------------------------------------------
# Aplicações
# ---------------------------------------------------------------------------

INSTALLED_APPS = [
    'django.contrib.admin',
    'django.contrib.auth',
    'django.contrib.contenttypes',
    'django.contrib.sessions',
    'django.contrib.messages',
    'django.contrib.staticfiles',

    'rest_framework',
    'corsheaders',

    'editais.apps.EditaisConfig',
    'usuarios.apps.UsuariosConfig',
    'estudos.apps.EstudosConfig',
    'assinaturas.apps.AssinaturasConfig',
]

MIDDLEWARE = [
    'corsheaders.middleware.CorsMiddleware',
    'django.middleware.security.SecurityMiddleware',
    'django.contrib.sessions.middleware.SessionMiddleware',
    'django.middleware.common.CommonMiddleware',
    'django.middleware.csrf.CsrfViewMiddleware',
    'django.contrib.auth.middleware.AuthenticationMiddleware',
    'django.contrib.messages.middleware.MessageMiddleware',
    'django.middleware.clickjacking.XFrameOptionsMiddleware',
]

ROOT_URLCONF = 'verticai.urls'

TEMPLATES = [
    {
        'BACKEND': 'django.template.backends.django.DjangoTemplates',
        'DIRS': [],
        'APP_DIRS': True,
        'OPTIONS': {
            'context_processors': [
                'django.template.context_processors.request',
                'django.contrib.auth.context_processors.auth',
                'django.contrib.messages.context_processors.messages',
            ],
        },
    },
]

WSGI_APPLICATION = 'verticai.wsgi.application'
ASGI_APPLICATION = 'verticai.asgi.application'


# ---------------------------------------------------------------------------
# Banco de dados
# ---------------------------------------------------------------------------
# Padrão: SQLite (desenvolvimento). Defina DB_ENGINE=postgresql e as demais
# variáveis DB_* para apontar para um Postgres (requer o pacote psycopg).

if os.environ.get('DB_ENGINE', 'sqlite3') == 'postgresql':
    DATABASES = {
        'default': {
            'ENGINE': 'django.db.backends.postgresql',
            'NAME': os.environ['DB_NAME'],
            'USER': os.environ['DB_USER'],
            'PASSWORD': os.environ['DB_PASSWORD'],
            'HOST': os.environ.get('DB_HOST', 'localhost'),
            'PORT': os.environ.get('DB_PORT', '5432'),
            'CONN_MAX_AGE': 60,
        }
    }
else:
    DATABASES = {
        'default': {
            'ENGINE': 'django.db.backends.sqlite3',
            'NAME': BASE_DIR / 'db.sqlite3',
        }
    }


# ---------------------------------------------------------------------------
# Autenticação
# ---------------------------------------------------------------------------

AUTH_PASSWORD_VALIDATORS = [
    {'NAME': 'django.contrib.auth.password_validation.UserAttributeSimilarityValidator'},
    {'NAME': 'django.contrib.auth.password_validation.MinimumLengthValidator'},
    {'NAME': 'django.contrib.auth.password_validation.CommonPasswordValidator'},
    {'NAME': 'django.contrib.auth.password_validation.NumericPasswordValidator'},
]


# ---------------------------------------------------------------------------
# Internacionalização
# ---------------------------------------------------------------------------

LANGUAGE_CODE = 'pt-br'
TIME_ZONE = 'America/Sao_Paulo'
USE_I18N = True
USE_TZ = True


# ---------------------------------------------------------------------------
# Arquivos estáticos e de mídia
# ---------------------------------------------------------------------------

STATIC_URL = 'static/'
STATIC_ROOT = BASE_DIR / 'staticfiles'

MEDIA_URL = 'media/'
MEDIA_ROOT = BASE_DIR / 'media'

DEFAULT_AUTO_FIELD = 'django.db.models.BigAutoField'


# ---------------------------------------------------------------------------
# Upload
# ---------------------------------------------------------------------------

# Teto do próprio Django para o corpo da requisição (2,5 MB é o padrão dele).
FILE_UPLOAD_MAX_MEMORY_SIZE = 5 * 1024 * 1024
DATA_UPLOAD_MAX_MEMORY_SIZE = 20 * 1024 * 1024

# Teto de negócio, validado explicitamente na view de processamento de edital.
MAX_UPLOAD_PDF_SIZE = int(os.environ.get('MAX_UPLOAD_PDF_SIZE', 15 * 1024 * 1024))

# Teto de negócio para a foto de perfil, validado no serializer de conta.
# Generoso o bastante pra não incomodar com fotos de celular (que já chegam
# em 5-8 MB fácil), mas ainda limitado — upload sem teto é disco livre pra
# qualquer usuário autenticado encher.
MAX_UPLOAD_AVATAR_SIZE = int(os.environ.get('MAX_UPLOAD_AVATAR_SIZE', 10 * 1024 * 1024))


# ---------------------------------------------------------------------------
# E-mail
# ---------------------------------------------------------------------------

EMAIL_BACKEND = os.environ.get(
    'DJANGO_EMAIL_BACKEND',
    'django.core.mail.backends.console.EmailBackend',
)
DEFAULT_FROM_EMAIL = os.environ.get('DEFAULT_FROM_EMAIL', 'nao-responda@verticai.local')


# ---------------------------------------------------------------------------
# CORS
# ---------------------------------------------------------------------------

CORS_ALLOWED_ORIGINS = env_list(
    'CORS_ALLOWED_ORIGINS',
    ['http://localhost:5173', 'http://127.0.0.1:5173'] if DEBUG else [],
)
CORS_ALLOW_CREDENTIALS = False

CSRF_TRUSTED_ORIGINS = env_list('CSRF_TRUSTED_ORIGINS', CORS_ALLOWED_ORIGINS)


# ---------------------------------------------------------------------------
# Django REST Framework
# ---------------------------------------------------------------------------

REST_FRAMEWORK = {
    'DEFAULT_AUTHENTICATION_CLASSES': (
        'rest_framework_simplejwt.authentication.JWTAuthentication',
    ),
    # Padrão seguro: tudo exige autenticação. Endpoints públicos (registro,
    # login, webhook) declaram AllowAny explicitamente.
    'DEFAULT_PERMISSION_CLASSES': (
        'rest_framework.permissions.IsAuthenticated',
    ),
    'DEFAULT_PAGINATION_CLASS': 'rest_framework.pagination.PageNumberPagination',
    'PAGE_SIZE': 50,
    'DEFAULT_THROTTLE_CLASSES': (
        'rest_framework.throttling.ScopedRateThrottle',
    ),
    'DEFAULT_THROTTLE_RATES': {
        # Processar edital dispara chamada paga ao Gemini: limite agressivo.
        'processar_edital': os.environ.get('THROTTLE_PROCESSAR_EDITAL', '10/hour'),
        'registro': os.environ.get('THROTTLE_REGISTRO', '20/hour'),
        # Evita força-bruta contra a senha atual de quem já tem sessão válida.
        'trocar_senha': os.environ.get('THROTTLE_TROCAR_SENHA', '10/hour'),
    },
}

SIMPLE_JWT = {
    'ACCESS_TOKEN_LIFETIME': timedelta(minutes=int(os.environ.get('JWT_ACCESS_MINUTES', 30))),
    'REFRESH_TOKEN_LIFETIME': timedelta(days=int(os.environ.get('JWT_REFRESH_DAYS', 7))),
    'ROTATE_REFRESH_TOKENS': True,
    'BLACKLIST_AFTER_ROTATION': False,
    'UPDATE_LAST_LOGIN': True,
}


# ---------------------------------------------------------------------------
# Integrações externas
# ---------------------------------------------------------------------------

GEMINI_API_KEY = os.environ.get('GEMINI_API_KEY', '')
GEMINI_MODEL = os.environ.get('GEMINI_MODEL', 'gemini-3.6-flash')

STRIPE_SECRET_KEY = os.environ.get('STRIPE_SECRET_KEY', '')
STRIPE_WEBHOOK_SECRET = os.environ.get('STRIPE_WEBHOOK_SECRET', '')

FRONTEND_URL = os.environ.get('FRONTEND_URL', 'http://localhost:5173')
STRIPE_SUCCESS_URL = os.environ.get('STRIPE_SUCCESS_URL', f'{FRONTEND_URL}/assinatura/sucesso')
STRIPE_CANCEL_URL = os.environ.get('STRIPE_CANCEL_URL', f'{FRONTEND_URL}/assinatura/cancelado')


# ---------------------------------------------------------------------------
# Endurecimento para produção
# ---------------------------------------------------------------------------

if not DEBUG:
    SECURE_SSL_REDIRECT = env_bool('SECURE_SSL_REDIRECT', True)
    SECURE_PROXY_SSL_HEADER = ('HTTP_X_FORWARDED_PROTO', 'https')
    SESSION_COOKIE_SECURE = True
    CSRF_COOKIE_SECURE = True
    SECURE_HSTS_SECONDS = int(os.environ.get('SECURE_HSTS_SECONDS', 60 * 60 * 24 * 30))
    SECURE_HSTS_INCLUDE_SUBDOMAINS = True
    SECURE_HSTS_PRELOAD = True
    SECURE_CONTENT_TYPE_NOSNIFF = True
    SECURE_REFERRER_POLICY = 'same-origin'
    X_FRAME_OPTIONS = 'DENY'


# ---------------------------------------------------------------------------
# Logging
# ---------------------------------------------------------------------------

LOGGING = {
    'version': 1,
    'disable_existing_loggers': False,
    'formatters': {
        'padrao': {
            'format': '[{asctime}] {levelname} {name}: {message}',
            'style': '{',
        },
    },
    'handlers': {
        'console': {
            'class': 'logging.StreamHandler',
            'formatter': 'padrao',
        },
    },
    'root': {
        'handlers': ['console'],
        'level': os.environ.get('LOG_LEVEL', 'INFO'),
    },
    'loggers': {
        'django.request': {
            'handlers': ['console'],
            'level': 'ERROR',
            'propagate': False,
        },
    },
}
