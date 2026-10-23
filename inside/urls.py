#inside/urls.py
"""
URL configuration for inside project.

The `urlpatterns` list routes URLs to views. For more information please see:
    https://docs.djangoproject.com/en/5.1/topics/http/urls/
Examples:
Function views
    1. Add an import:  from my_app import views
    2. Add a URL to urlpatterns:  path('', views.home, name='home')
Class-based views
    1. Add an import:  from other_app.views import Home
    2. Add a URL to urlpatterns:  path('', Home.as_view(), name='home')
Including another URLconf
    1. Import the include() function: from django.urls import include, path
    2. Add a URL to urlpatterns:  path('blog/', include('blog.urls'))
"""
from django.contrib import admin
from django.shortcuts import redirect
from django.urls import path, include
from django.conf import settings
from django.conf.urls.static import static
from asset.admin import admin_site
from django.conf.urls.static import static # Diperlukan untuk static files di development
from django.contrib.auth import views as auth_views # Import views yang diperlukan
from django.http import HttpResponse
from accounts.views import render_custom_dashboard,render_superuser_dashboard
from asset.views import custom_admin_index
from asset import views as asset_views

def home(request):
    return HttpResponse("Hello, Saneditech! Aplikasi Django sudah jalan 🚀")

urlpatterns = [
    # Taruh URL AJAX ini tepat di sini agar langsung dikenali oleh sistem
    path(
        'admin/asset/get-capex-form/',
        asset_views.load_capex_form,
        name='get_capex_form',
    ),
    path('', lambda request: redirect('accounts/login/')),  # redirect root ke login
    path('admin/logout/', auth_views.LogoutView.as_view(next_page='/accounts/login/'), name='logout'),

    path('admin/global-monitoring/', render_superuser_dashboard, name='global_monitoring_dashboard'),
    path('admin/dashboard/group_a/', render_custom_dashboard, name='dashboard_group_a'),
    path('admin/dashboard/group_b/', render_custom_dashboard, name='dashboard_group_b'),
    path('admin/dashboard/group_c/', render_custom_dashboard, name='dashboard_group_c'),

    path('admin/', admin_site.urls),  
    path('admin/', custom_admin_index, name='index'),
    path('accounts/', include('accounts.urls')),    
    path('data/', include('data.urls')), 
    path('form/', include('form.urls', namespace='form')),
    path('asset/', include('asset.urls')),  

    # --------------------------------------------------------------------------
    # 🔐 URL ROUTING UNTUK RESET PASSWORD (EMAIL)
    # --------------------------------------------------------------------------
    # 1. Halaman minta reset (input email user)
    path('password_reset/', auth_views.PasswordResetView.as_view(), name='password_reset'),
    
    # 2. Halaman konfirmasi bahwa email link reset sukses dikirim
    path('password_reset/done/', auth_views.PasswordResetDoneView.as_view(), name='password_reset_done'),
    
    # 3. Link rahasia yang diklik user dari email mereka (berisi token unik b64)
    path('reset/<uidb64>/<token>/', auth_views.PasswordResetConfirmView.as_view(), name='password_reset_confirm'),
    
    # 4. Halaman sukses yang menyatakan password baru telah tersimpan
    path('reset/done/', auth_views.PasswordResetCompleteView.as_view(), name='password_reset_complete'),
    
    # Path admin atau path INSIDE lainnya yang sudah ada di bawahnya...
    # path('admin/', admin_site.urls),
       
 ] 

if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
