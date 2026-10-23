# PRIMA/inside/settings.py
# inside/settings.py — tambahkan setelah import os

import warnings
warnings.filterwarnings("ignore", category=UserWarning)
warnings.filterwarnings("ignore", category=DeprecationWarning)
warnings.filterwarnings("ignore", category=FutureWarning)

# Suppress PyTorch warning khusus
warnings.filterwarnings(
    "ignore",
    message=".*torch.quantize_per_tensor.*",
    category=UserWarning
)
warnings.filterwarnings(
    "ignore",
    message=".*fitz.*deprecated.*"
)


import os
import cloudinary
from pathlib import Path
from django.contrib.messages import constants as messages

# ✅ Load .env — tidak error jika file tidak ada
try:
    from dotenv import load_dotenv
    load_dotenv(dotenv_path=Path(__file__).resolve().parent.parent / '.env')
except ImportError:
    pass

# ✅ decouple config dengan fallback aman
try:
    from decouple import config
except ImportError:
    def config(key, default=''):
        return os.getenv(key, default)

try:
    import dj_database_url
except ImportError:
    dj_database_url = None

# Build paths
BASE_DIR = Path(__file__).resolve().parent.parent

# ==============================================================================
# 1. KEAMANAN & KONFIGURASI LINGKUNGAN KRITIS
# ==============================================================================

# ✅ SECRET_KEY dengan fallback — tidak pernah None
SECRET_KEY = os.getenv(
    'SECRET_KEY',
    'django-insecure-prima-local-fallback-key-2024-ganti-di-production'
)
if not SECRET_KEY:
    SECRET_KEY = 'django-insecure-prima-emergency-key-2024'

# ✅ DEBUG dari env variable, default True untuk lokal
DEBUG = os.getenv('DJANGO_DEBUG', 'True').lower() in ('true', '1', 't', 'yes')

# ✅ ALLOWED_HOSTS — selalu ada isi
ALLOWED_HOSTS = [
    'localhost',
    '127.0.0.1',
    '0.0.0.0',
    '[::1]',
    'saneditech.com',
    'www.saneditech.com',
    '.up.railway.app',
    '.railway.app',
]

extra_hosts = os.getenv('EXTRA_HOSTS', '')
if extra_hosts:
    ALLOWED_HOSTS.extend([h.strip() for h in extra_hosts.split(',') if h.strip()])

# ✅ Cookie & SSL sesuai mode
if DEBUG:
    SESSION_COOKIE_SECURE = False
    CSRF_COOKIE_SECURE    = False
    SECURE_SSL_REDIRECT   = False
else:
    SESSION_COOKIE_SECURE          = True
    CSRF_COOKIE_SECURE             = True
    SECURE_SSL_REDIRECT            = True
    SECURE_HSTS_SECONDS            = 31536000
    SECURE_HSTS_INCLUDE_SUBDOMAINS = True
    SECURE_HSTS_PRELOAD            = True
    SECURE_CONTENT_TYPE_NOSNIFF    = True

SECURE_PROXY_SSL_HEADER = ('HTTP_X_FORWARDED_PROTO', 'https')

# ✅ CSRF TRUSTED ORIGINS
CSRF_TRUSTED_ORIGINS = [
    'http://localhost',
    'http://localhost:8000',
    'http://localhost:8001',
    'http://127.0.0.1',
    'http://127.0.0.1:8000',
    'http://127.0.0.1:8001',
    'https://saneditech.com',
    'https://www.saneditech.com',
    'https://*.up.railway.app',
    'https://*.railway.app',
]

ASGI_APPLICATION = 'inside.asgi.application'
WSGI_APPLICATION = 'inside.wsgi.application'

# ==============================================================================
# 2. DATABASE
# ==============================================================================
DATABASES = {
    'default': {
        'ENGINE':   'django.db.backends.postgresql',
        'NAME':     os.getenv('DB_NAME',     'prima_db'),
        'USER':     os.getenv('DB_USER',     'postgres'),
        'PASSWORD': os.getenv('DB_PASSWORD', 'Semangat123'),
        'HOST':     os.getenv('DB_HOST',     'localhost'),
        'PORT':     os.getenv('DB_PORT',     '5432'),
    }
}

# Override dengan DATABASE_URL jika ada (Railway)
if dj_database_url and os.getenv('DATABASE_URL'):
    DATABASES['default'] = dj_database_url.config(
        default=os.getenv('DATABASE_URL'),
        conn_max_age=600
    )

# ==============================================================================
# 3. INSTALLED APPS & MIDDLEWARE
# ==============================================================================
INSTALLED_APPS = [
    'channels',
    'cloudinary_storage',
    'jazzmin',
    'django.contrib.admin',
    'django.contrib.auth',
    'django.contrib.contenttypes',
    'django.contrib.sessions',
    'django.contrib.messages',
    'django.contrib.staticfiles',
    'cloudinary',
    'import_export',
    'django_extensions',
    'accounts',
    'asset.apps.AssetConfig',        
    'data',
    'form',
    'inside',
]

CHANNEL_LAYERS = {
    'default': {
        'BACKEND': 'channels.layers.InMemoryChannelLayer',
    },
}

MIDDLEWARE = [
    'django.middleware.security.SecurityMiddleware',
    'whitenoise.middleware.WhiteNoiseMiddleware',
    'django.contrib.sessions.middleware.SessionMiddleware',
    'django.middleware.common.CommonMiddleware',
    'django.middleware.csrf.CsrfViewMiddleware',
    'django.contrib.auth.middleware.AuthenticationMiddleware',
    'django.contrib.messages.middleware.MessageMiddleware',
    'django.middleware.clickjacking.XFrameOptionsMiddleware',
    'accounts.middleware.GroupRedirectMiddleware',
]

# ==============================================================================
# 4. TEMPLATES
# ==============================================================================
ROOT_URLCONF = 'inside.urls'

TEMPLATES = [
    {
        'BACKEND': 'django.template.backends.django.DjangoTemplates',
        'DIRS': [BASE_DIR / 'templates'],
        'APP_DIRS': True,
        'OPTIONS': {
            'context_processors': [
                'django.template.context_processors.debug',
                'django.template.context_processors.request',
                'django.contrib.auth.context_processors.auth',
                'django.contrib.messages.context_processors.messages',
                'accounts.context_processors.user_context',
            ],
        },
    },
]

# ==============================================================================
# 5. PASSWORD VALIDATION & INTERNATIONALIZATION
# ==============================================================================
AUTH_PASSWORD_VALIDATORS = [
    {'NAME': 'django.contrib.auth.password_validation.UserAttributeSimilarityValidator'},
    {'NAME': 'django.contrib.auth.password_validation.MinimumLengthValidator'},
    {'NAME': 'django.contrib.auth.password_validation.CommonPasswordValidator'},
    {'NAME': 'django.contrib.auth.password_validation.NumericPasswordValidator'},
]

LANGUAGE_CODE = 'en-us'
TIME_ZONE     = 'Asia/Jakarta'
USE_I18N      = True
USE_TZ        = True

# ==============================================================================
# 6. STATIC & MEDIA FILES
# ==============================================================================

# ✅ STATIC_ROOT harus didefinisikan SEBELUM dipakai di blok Cloudinary
STATIC_URL  = '/static/'
STATIC_ROOT = BASE_DIR / 'staticfiles'

STATICFILES_DIRS = [BASE_DIR / 'static']

MEDIA_URL  = '/media/'
MEDIA_ROOT = BASE_DIR / 'media'

STATICFILES_FINDERS = [
    'django.contrib.staticfiles.finders.FileSystemFinder',
    'django.contrib.staticfiles.finders.AppDirectoriesFinder',
]

# ==============================================================================
# 7. EMAIL
# ==============================================================================
EMAIL_BACKEND       = 'django.core.mail.backends.smtp.EmailBackend'
EMAIL_HOST          = 'smtp.gmail.com'
EMAIL_PORT          = 587
EMAIL_USE_TLS       = True
EMAIL_HOST_USER     = os.getenv('EMAIL_HOST_USER', 'junsmile1986@gmail.com')
EMAIL_HOST_PASSWORD = os.getenv('EMAIL_HOST_PASSWORD', '')
DEFAULT_FROM_EMAIL  = f"PRIMA System <{EMAIL_HOST_USER}>"

DOMAIN  = os.getenv('DOMAIN', '127.0.0.1:8000')
SITE_ID = 1

# ==============================================================================
# 8. MESSAGE & AUTHENTICATION
# ==============================================================================
MESSAGE_STORAGE = 'django.contrib.messages.storage.session.SessionStorage'
MESSAGE_TAGS = {
    messages.DEBUG:   'alert-info',
    messages.INFO:    'alert-info',
    messages.SUCCESS: 'alert-success',
    messages.WARNING: 'alert-warning',
    messages.ERROR:   'alert-danger',
}

LOGIN_URL             = '/login/'
LOGIN_REDIRECT_URL    = '/accounts/redirect/'
LOGOUT_REDIRECT_URL   = '/accounts/login/'
SESSION_COOKIE_NAME   = 'inside_admin_sessionid'

# ==============================================================================
# 9. LOGGING & DEFAULT AUTO FIELD
# ==============================================================================
DEFAULT_AUTO_FIELD = 'django.db.models.BigAutoField'

LOGGING = {
    'version': 1,
    'disable_existing_loggers': False,
    'formatters': {
        'verbose': {
            'format': '{levelname} {asctime} {module} {process:d} {thread:d} {message}',
            'style': '{',
        },
        'simple': {'format': '{levelname} {message}', 'style': '{'},
    },
    'handlers': {
        'console': {'class': 'logging.StreamHandler', 'formatter': 'simple'},
        'file': {
            'class':       'logging.handlers.RotatingFileHandler',
            'filename':    os.path.join(BASE_DIR, 'django_debug.log'),
            'maxBytes':    1024 * 1024 * 5,
            'backupCount': 5,
            'formatter':   'verbose',
        },
    },
    'loggers': {
        'django': {'handlers': ['console'], 'level': 'INFO', 'propagate': True},
        'asset':  {'handlers': ['console', 'file'], 'level': 'DEBUG', 'propagate': False},
    },
    'root': {'handlers': ['console'], 'level': 'WARNING'},
}

# ==============================================================================
# 10. CLOUDINARY & STORAGE
# ==============================================================================
CLOUDINARY_CLOUD_NAME = config('CLOUDINARY_CLOUD_NAME', default='')
CLOUDINARY_API_KEY    = config('CLOUDINARY_API_KEY',    default='')
CLOUDINARY_API_SECRET = config('CLOUDINARY_API_SECRET', default='')

if CLOUDINARY_CLOUD_NAME and CLOUDINARY_API_KEY and CLOUDINARY_API_SECRET:
    cloudinary.config(
        cloud_name = CLOUDINARY_CLOUD_NAME,
        api_key    = CLOUDINARY_API_KEY,
        api_secret = CLOUDINARY_API_SECRET,
        secure     = True,
    )
    CLOUDINARY_STORAGE = {
        'CLOUD_NAME': CLOUDINARY_CLOUD_NAME,
        'API_KEY':    CLOUDINARY_API_KEY,
        'API_SECRET': CLOUDINARY_API_SECRET,
        'SECURE':     True,
    }
    STATICFILES_STORAGE  = 'cloudinary_storage.storage.StaticHashedCloudinaryStorage'
    DEFAULT_FILE_STORAGE = 'cloudinary_storage.storage.MediaCloudinaryStorage'

    # ✅ FIX: STATIC_ROOT sudah didefinisikan di atas, tidak akan NameError lagi
    CLOUDINARY_STATIC_ROOT = STATIC_ROOT

    print("DEBUG: STORAGE SET TO CLOUDINARY")
else:
    STATICFILES_STORAGE  = 'whitenoise.storage.CompressedManifestStaticFilesStorage'
    DEFAULT_FILE_STORAGE = 'django.core.files.storage.FileSystemStorage'
    print("DEBUG: STORAGE SET TO WHITENOISE/LOCAL FALLBACK")

# ==============================================================================
# 11. JAZZMIN SETTINGS
# Tanda perbaikan di file ini: cari "PERBAIKAN SETTINGS"
# ==============================================================================
JAZZMIN_SETTINGS = {
    "site_title": "PRIMA Admin",
    "site_header": "PRIMA (Inventory Disposed Equipments)",
    "site_brand": "ASSETPRIMA",
    "welcome_sign": "Selamat datang di ASSETPRIMA Admin",
    "copyright": "Junaedi/6032232064 © 2025",

    # Tetap True: sidebar dirender sebagai daftar main menu (nav-header) yang dibaca custom_admin.js.
    "navigation_expanded": True,

    # ✅ [PERBAIKAN SETTINGS 1] Blok "side_menu" DIHAPUS.
    # "side_menu" bukan setting Jazzmin, jadi selama ini diabaikan sepenuhnya.
    # Sidebar dibuat otomatis dari app dan model yang terdaftar di admin_site.
    # - Teks main menu  -> verbose_name di apps.py masing-masing app
    # - Sub menu & sub-sub menu -> MENU_TREE di custom_admin.js

    # ✅ [PERBAIKAN SETTINGS 2] "asset_tracking" ditulis eksplisit di akhir,
    # supaya urutannya tidak bergantung pada perilaku bawaan Jazzmin.
    # Pakai LABEL app (nama app di INSTALLED_APPS), bukan verbose_name.
    "order_with_respect_to": [
        "data", "asset", "form", "accounts", "auth", "asset_tracking",
    ],

    "icons": {
        # Ikon level app
        "asset": "fas fa-box-open",
        "data": "fas fa-database",        
        "form": "fas fa-file-alt",
        "accounts": "fas fa-users",

        # Ikon level model: app asset
        "asset.AssetEquipment": "fas fa-layer-group",
        "asset.AssetMonthlyStatus": "fas fa-calendar-alt",
        "asset.AssetEquipmentDisposed": "fas fa-truck-pickup",
        "asset.AssetEquipmentPrepareDisposed": "fas fa-truck-loading",
        "asset.AssetMasterMonthlyStatus": "fas fa-database",
        "asset.AssetFinalMonthlyStatus": "fas fa-file-invoice",
        "asset.EquipmentMonthlyStatus": "fas fa-calendar-check",
        "asset.AssetEquipmentStandby": "fas fa-pause-circle",
        "asset.AssetEquipmentBreakdown": "fas fa-truck-monster",
        "asset.AssetEquipmentOperate": "fas fa-truck",

        # Ikon level model: app accounts dan auth
        "accounts.UserProfile": "fas fa-user-tag",
        "auth.User": "fas fa-user",
        "auth.Group": "fas fa-users-cog",

        # Ikon level model: app form
        "form.FormPengajuanEquipmentDisposed": "fas fa-file-signature",
        "form.FormLampiranCapex": "fas fa-paperclip",
        "form.FormPengajuanDisposedSite": "fas fa-map-marker-alt",
        "form.FormRepairCostAnalisis": "fas fa-tools",
        "form.FormFotoKonditionUnit": "fas fa-camera",
        # ✅ [PERBAIKAN SETTINGS 3] Model yang benar-benar terdaftar di form/admin.py
        # adalah ChecksheetPI. "form.FormPeriodicalInspection" dihapus karena
        # tidak ada di admin.
        "form.ChecksheetPI": "fas fa-clipboard-check",
    },

    "custom_css": "css/custom_admin.css",
    "custom_js": "js/custom_admin.js",
}

