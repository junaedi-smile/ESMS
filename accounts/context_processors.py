# accounts/context_processors.py
def user_context(request):
    """
    Menambahkan data UserProfile ke konteks template jika pengguna diautentikasi.
    """
    user_profile = None
    if request.user.is_authenticated:
        try:
            user_profile = request.user.userprofile
        except UserProfile.DoesNotExist:
            user_profile = None
    
    return {
        'user_profile': user_profile,
    }

