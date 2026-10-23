# accounts/middleware.py
from django.shortcuts import redirect
from django.urls import reverse, NoReverseMatch


class GroupRedirectMiddleware:
    """
    Middleware untuk memastikan user diarahkan ke halaman yang sesuai dengan hak aksesnya
    dan mengantisipasi error NoReverseMatch pada URL kustom yang belum terdefinisi.
    """

    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        user = request.user

        # Hanya jalankan jika user sudah login
        if user.is_authenticated:
            path = request.path

            # 1. Jika Superuser (Admin Utama), biarkan lewat bebas ke mana saja
            if user.is_superuser:
                return self.get_response(request)

            # Ambil semua daftar nama grup milik user
            user_groups = [g.name for g in user.groups.all()]

            # 2. Amankan jalur redirect URL khusus jika memang polanya diakses
            try:
                if "dashboard_group_a" in path and "group_a" not in user_groups:
                    return redirect(reverse("admin:index"))

                if "dashboard_group_b" in path and "group_b" not in user_groups:
                    return redirect(reverse("admin:index"))

                if "dashboard_group_c" in path and "group_c" not in user_groups:
                    return redirect(reverse("admin:index"))
                
            except NoReverseMatch:
                # Jika url di atas tidak ditemukan, arahkan paksa ke halaman utama admin
                return redirect(reverse("admin:index"))

            # 3. INTERVENSI REDIRECT: Jika user diarahkan ke /accounts/redirect/ atau url kosong
            # Alihkan mereka langsung ke Dashboard Utama Admin Site (Jazzmin)
            if path == "/accounts/redirect/" or path == "/accounts/profile/":
                return redirect(reverse("admin:index"))

        return self.get_response(request)