# accounts/urls.py
from django.urls import path
from django.contrib.auth import views as auth_views  
from . import views



urlpatterns = [
    # URL untuk Login, Logout dan redirect
    path('login/', views.user_login, name='login'),       
    path('logout/', auth_views.LogoutView.as_view(next_page='accounts:login'), name='logout'),
    path('redirect/', views.login_redirect_view, name='login_redirect'),

    # URL untuk masuk ke dashboard user 
    path("test-session/", views.test_session, name="test_session"),
    path("test-message/", views.test_message, name="test_message"),

    
    # URL untuk Reset Password    
    path('reset-password/', auth_views.PasswordResetView.as_view(template_name='auth/password_reset_form.html'), name='password_reset'),
    path('reset-password/done/', auth_views.PasswordResetDoneView.as_view(template_name='auth/password_reset_done.html'), name='password_reset_done'),
    path('reset-password/confirm/<uidb64>/<token>/', auth_views.PasswordResetConfirmView.as_view(template_name='auth/password_reset_confirm.html'), name='password_reset_confirm'),
    path('reset-password/complete/', auth_views.PasswordResetCompleteView.as_view(template_name='auth/password_reset_complete.html'), name='password_reset_complete'),
    
    # URL Kustom untuk Profil Pengguna dan Ubah Kata Sandi
    path('profile/', views.user_profile, name='user_profile'),
    path('password-change/', views.password_change_view, name='password_change'),
]