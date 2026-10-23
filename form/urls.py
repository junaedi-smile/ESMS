# inside/form/urls.py (atau bagian dari main urls.py)

from django.urls import path
from .views import (
    SelectAssetView, 
    CreateChecksheetView, 
    ChecksheetDetailView, 
    ProcessApprovalView, 
    ResubmitChecksheetView,
    UpdateChecksheetView,
    )
from .admin import admin_site # Jika menggunakan admin_site kustom
from . import views

app_name = 'form'

urlpatterns = [   
    path('select-asset/', SelectAssetView.as_view(), name='select_asset'),
    path('checksheet-create/', CreateChecksheetView.as_view(), name='create_checksheet'),
    path('checksheet-detail/<int:pk>/', ChecksheetDetailView.as_view(), name='checksheet_detail'),
    path('process-approval/<str:document_type>/<int:pk>/', ProcessApprovalView.as_view(), name='process_approval'),
    path('checksheet-edit/<int:pk>/', UpdateChecksheetView.as_view(), name='edit_checksheet'),
    path('checksheet-resubmit/<int:pk>/', ResubmitChecksheetView.as_view(), name='resubmit_checksheet'),

    # ── Lampiran Capex ──────────────────────────────────────────────
    path(
        'lampiran-capex/create/',
        views.lampiran_capex_create,
        name='lampiran_capex_create',
    ),
    path(
        'lampiran-capex/<int:pk>/',
        views.lampiran_capex_detail,
        name='lampiran_capex_detail',
    ),

    path(
    'lampiran-capex/',
    views.daftar_lampiran_capex,
    name='daftar_lampiran_capex',
    ),

    # ── AJAX lookup ─────────────────────────────────────────────────
    path(
        'ajax/asset-lookup/',
        views.ajax_asset_lookup,
        name='ajax_asset_lookup',
    ),

    path(
    'lampiran-capex/create-ajax/',
    views.lampiran_capex_create_ajax,
    name='lampiran_capex_create_ajax',    
    ),
 
    # ------------path untuk download dan export pdf------

    path(
    'lampiran-capex/preview/',
    views.lampiran_capex_preview,
    name='lampiran_capex_preview',
    ),

    #============path untuk AJAX BA Standby==============
    path(
        'ba-standby/create-ajax/',
        views.ba_standby_create_ajax,
        name='ba_standby_create_ajax',
    ),

    path(
        'ba-standby/<int:pk>/',
        views.ba_standby_detail,
        name='ba_standby_detail',
    ),

    path(
        'ba-standby/preview',
        views.ba_standby_preview,
        name='ba_standby_preview'
    ),

]


# Dan di main urls.py (jika app Anda bernama 'form'):
# path('form/', include(('form.urls', 'form'), namespace='form')), 
# Namespace 'form' di sini memungkinkan pemanggilan 'form:select_asset'