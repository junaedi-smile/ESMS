# asset/urls.py
from django.urls import path
from asset import views as asset_views
from . import views
from .views import (
    asset_equipment_list, 
    asset_equipment_create, 
    asset_equipment_update, 
    asset_equipment_delete,
    import_asset_equipment_excel,
    export_asset_equipment_excel,
    assetequipment_list_view,     
    custom_admin_index,
    dashboard_filter_data, 
    prepare_for_disposed_list_view,   
)
from django.contrib.auth import views as auth_views 

app_name = 'asset'

urlpatterns = [ 
    # Path untuk password reset
    path('reset-password/', auth_views.PasswordResetView.as_view(template_name='inventory/auth/password_reset_form.html'), name='password_reset'),
    path('reset-password/done/', auth_views.PasswordResetDoneView.as_view(template_name='inventory/auth/password_reset_done.html'), name='password_reset_done'),
    path('reset-password/confirm/<uidb64>/<token>/', auth_views.PasswordResetConfirmView.as_view(template_name='inventory/auth/password_reset_confirm.html'), name='password_reset_confirm'),
    path('reset-password/complete/', auth_views.PasswordResetCompleteView.as_view(template_name='inventory/auth/password_reset_complete.html'), name='password_reset_complete'),

    # ── Dashboard ────────────────────────────────────────────────
    path('admin-dashboard/', custom_admin_index, name='custom_admin_dashboard'),
    path('dashboard/filter-data/', dashboard_filter_data, name='dashboard_filter_data'),

    # ── Asset Equipment ──────────────────────────────────────────
    path('', asset_equipment_list, name='asset_equipment_list'),
    path('create/', asset_equipment_create, name='asset_equipment_create'),
    path('update/<int:pk>/', asset_equipment_update, name='asset_equipment_update'),
    path('delete/<int:pk>/', asset_equipment_delete, name='asset_equipment_delete'),
    path('import/', import_asset_equipment_excel, name='import_asset_equipment_excel'),
    path('export/', export_asset_equipment_excel, name='export_asset_equipment_excel'), 
    path('equipments/', assetequipment_list_view, name='assetequipment_list'),     
    path('prepare-for-disposed/', prepare_for_disposed_list_view, name='prepare_for_disposed_list'),

    # ── BA Standby ────────────────────────────────────────────────  
    path('admin/asset/get-ba-standby-form/', asset_views.load_ba_standby_form, name='get_ba_standby_form'),

    # ── Document Tracking & Quick Disposed ─────────────────────────
    path('api/document-tracking-summary/', views.document_tracking_summary, name='api_document_tracking_summary'),
    path('upload-quick-disposed/', views.upload_quick_disposed, name='upload_quick_disposed'),
    path('delete-quick-disposed/', views.delete_quick_disposed, name='delete_quick_disposed'),

    # ── Foto 4 Sisi (Modul Independen & Penyelarasan JS) ───────────
    path('api/prepare-disposed/upload-foto-4-sisi/', views.upload_foto_4_sisi_disposed, name='upload_foto_4_sisi_disposed'),
    path('api/prepare-disposed/download-pdf/<str:cn_sap>/', views.download_pdf_foto_4_sisi, name='download_pdf_foto_4_sisi'),
    path('api/prepare-disposed/delete-foto/<str:cn_sap>/', views.api_delete_foto_4_sisi, name='api_delete_foto_4_sisi'),
    path('api/prepare-disposed/detail/<str:cn_sap>/', views.detail_foto_disposed_api, name='detail_foto_disposed_api'),
    
    # 🚀 Endpoint Workflow Foto 4 Sisi (Menyesuaikan pemanggilan AJAX di JavaScript)
    path('api/prepare-disposed/foto-4-sisi/<str:cn_sap>/submit/', views.submit_approval_disposed, name='submit_approval_disposed'),
    path('api/prepare-disposed/foto-4-sisi/<str:cn_sap>/approve/', views.submit_approval_disposed, name='approve_foto_4_sisi'),
    path('api/prepare-disposed/foto-4-sisi/<str:cn_sap>/reject/', views.reject_approval_disposed, name='reject_approval_disposed'),

    # ── Inspeksi Unit (Modul Independen Lainnya) ────────────────────
    path('api/prepare-disposed/inspection-items/<str:cn_sap>/', views.api_get_inspection_items, name='api_get_inspection_items'),
    path('api/prepare-disposed/inspection-items/<str:cn_sap>/save/', views.api_save_inspection_items, name='api_save_inspection_items'),
    path('api/prepare-disposed/inspection-items/<str:cn_sap>/delete/', views.api_delete_inspection_items, name='api_delete_inspection_items'),
    path('prepare-disposed/inspection-pdf/<str:cn_sap>/', views.download_pdf_inspeksi_unit, name='download_pdf_inspeksi_unit'),

    # 🚀 Aksi Workflow Inspeksi Unit
    path('api/prepare-disposed/inspeksi/<str:cn_sap>/submit/', views.submit_inspeksi_unit, name='submit_inspeksi_unit'),
    path('api/prepare-disposed/inspeksi/<str:cn_sap>/approve/', views.approve_inspeksi_unit, name='approve_inspeksi_unit'),
    path('api/prepare-disposed/inspeksi/<str:cn_sap>/reject/', views.reject_inspeksi_unit, name='reject_inspeksi_unit'),

    # aksi untuk approval by email
    path('api/email-action/<str:cn_sap>/<str:action>/', views.email_approval_action, name='email_approval_action'),

    # aksi untuk AJAX Rolling di halaman utama
    path('api/check-status/<str:cn_sap>/', views.check_approval_status, name='check_approval_status'),
]