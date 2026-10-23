#inside/accounts/views.py
from django.contrib.auth.decorators import login_required, user_passes_test
from django.contrib.admin.views.decorators import staff_member_required
from django.contrib.auth.decorators import login_required
from asset.admin import admin_site
from django.contrib.auth.models import Group
from django.contrib.admin import site as admin_site_default
from asset.admin import admin_site
from django.shortcuts import redirect, render
from django.urls import reverse
from django.contrib import messages
from django.contrib.auth.forms import PasswordChangeForm
from django.contrib.auth import update_session_auth_hash, authenticate, login, logout
from django.http import HttpResponse
from django.db.models import Q
from django.utils import timezone

# Model bawaan
from django.contrib.auth.models import Group

# Model aplikasi lain
from form.models import ChecksheetPI, ApprovalStep, ApprovalLog


# ------------------------------------------------------------------
# TEST SESSION / MESSAGE
# ------------------------------------------------------------------
def test_session(request):
    if "counter" not in request.session:
        request.session["counter"] = 1
    else:
        request.session["counter"] += 1
    return HttpResponse(f"Counter value: {request.session['counter']}")


def test_message(request):
    messages.error(request, "Ini pesan error test")
    return redirect('login')


# ------------------------------------------------------------------
# LOGIN / LOGOUT
# ------------------------------------------------------------------
def user_login(request):
    if request.user.is_authenticated:
        return redirect('login_redirect')

    if request.method == 'POST':
        username = request.POST.get('username')
        password = request.POST.get('password')

        user = authenticate(request, username=username, password=password)

        if user is not None:
            login(request, user)
            return redirect('login_redirect')
        else:
            messages.error(request, "❌ Username atau password salah.")
            return render(request, 'auth/login.html')

    return render(request, 'auth/login.html')


@login_required
def user_logout(request):
    logout(request)
    return redirect('login')


# ------------------------------------------------------------------
# CEK GROUP
# ------------------------------------------------------------------
def is_in_group_a(user):
    return user.groups.filter(name='group_a').exists()


def is_in_group_b(user):
    return user.groups.filter(name='group_b').exists()


def is_in_group_c(user):
    return user.groups.filter(name='group_c').exists()


# ------------------------------------------------------------------
# BOTTLENECK CALCULATION
# ------------------------------------------------------------------
def calculate_bottleneck_info(checksheet):
    STATUS_LIST_KEYS = ['DRAFT', 'SUB', 'APR1', 'APR2']
    logs = ApprovalLog.objects.filter(
        object_id=checksheet.pk,
        content_type__model=checksheet._meta.model_name.lower()
    ).filter(
        Q(action='APPROVED') | Q(action='SUBMIT')
    ).order_by('tanggal_persetujuan')

    last_known_time = checksheet.submitted_at or checksheet.created_at
    longest_duration = timezone.timedelta(seconds=0)
    bottleneck_step = "DRAFT (Menunggu data awal)"

    for log in logs:
        if last_known_time:
            duration = log.tanggal_persetujuan - last_known_time
            if duration > longest_duration:
                longest_duration = duration
                if log.action == 'SUBMIT':
                    bottleneck_step = "DRAFT (Menunggu Submit oleh Pembuat)"
                elif log.langkah:
                    bottleneck_step = f"Menunggu Persetujuan: {log.langkah.nama_langkah}"
                else:
                    bottleneck_step = "Langkah Tidak Teridentifikasi"
            last_known_time = log.tanggal_persetujuan

    if checksheet.status in STATUS_LIST_KEYS and checksheet.status != 'DRAFT':
        try:
            current_status_index = STATUS_LIST_KEYS.index(checksheet.status)
            if current_status_index > 0:
                approving_step = ApprovalStep.objects.get(urutan=current_status_index)
                current_bottleneck_step_name = f"Menunggu Persetujuan: {approving_step.nama_langkah}"
                current_duration = timezone.now() - last_known_time
                if current_duration > longest_duration:
                    longest_duration = current_duration
                    bottleneck_step = current_bottleneck_step_name
        except (ValueError, ApprovalStep.DoesNotExist):
            pass

    return {
        'longest_duration': str(longest_duration).split('.')[0],
        'bottleneck_step': bottleneck_step,
    }


# ------------------------------------------------------------------
# LOGIN REDIRECT VIEW
# ------------------------------------------------------------------
@login_required
def login_redirect_view(request):
    """Mengalihkan user setelah login ke custom dashboard yang sesuai."""
    user = request.user

    # Prioritas 1: Group A (Approval Level 1)
    if is_in_group_a(user):
        return redirect('dashboard_group_a') # Mengarah ke URL kustom yang baru

    # Prioritas 2: Group B (Approval Level 2)
    elif is_in_group_b(user):
        return redirect('dashboard_group_b')

    # Prioritas 3: Group C (Approval Level 3)
    elif is_in_group_c(user):
        return redirect('dashboard_group_c')
    
    # Prioritas 4: Superuser atau user staff non-grup (Default Admin Index)
    # Superuser (dan staff lain tanpa grup custom) diarahkan ke Admin Index bawaan
    # yang dihandle oleh admin_site.urls
    return redirect(reverse('admin:index'))

# inside/accounts/views.py

def get_current_approval_step_name(status_code):
    """Mendapatkan nama langkah persetujuan yang sedang ditunggu berdasarkan status."""
    if status_code == 'SUB':
        # Status SUB berarti menunggu Approval Level 1 (Urutan 1)
        target_urutan = 1 
    elif status_code == 'APR1':
        # Status APR1 berarti menunggu Approval Level 2 (Urutan 2)
        target_urutan = 2
    elif status_code == 'APR2':
        # Status APR2 berarti menunggu Approval Level 3 (Urutan 3/Final)
        target_urutan = 3
    elif status_code == 'FIN':
        return 'Selesai (Final Approved)'
    elif status_code == 'REJ':
        return 'Ditolak (Rejected)'
    else:
        return 'Draft / Tidak Teridentifikasi'
        
    try:
        # Asumsi model ApprovalStep memiliki field 'urutan'
        step = ApprovalStep.objects.get(urutan=target_urutan)
        return f"Menunggu: {step.nama_langkah}"
    except ApprovalStep.DoesNotExist:
        return f"Menunggu: Level {target_urutan} (Step Not Found)"
    
def get_next_approval_step_name(status_code):
    """
    Mendapatkan nama langkah persetujuan berikutnya.
    
    Logic: Jika status saat ini Selesai atau Ditolak, tidak ada langkah berikutnya.
    Jika status masih berjalan, langkah berikutnya adalah langkah setelah Current Approval Step.
    """
    # Tentukan Urutan Langkah Persetujuan yang AKAN datang.
    if status_code == 'SUB':
        # Setelah Level 1 selesai, langkah berikutnya adalah Level 2
        target_urutan = 2 
    elif status_code == 'APR1':
        # Setelah Level 2 selesai, langkah berikutnya adalah Final Level
        target_urutan = 3
    elif status_code == 'APR2':
        # Setelah Final Level selesai, status akan menjadi FIN
        return 'Finalisasi (Selesai)' # Tidak ada approver lagi, dokumen akan FIN.
    else:
        # Untuk DRAFT, FIN, atau REJ, tidak ada langkah persetujuan berikutnya.
        return '-'
        
    try:
        # Ambil nama langkah berikutnya berdasarkan urutan
        step = ApprovalStep.objects.get(urutan=target_urutan)
        return f"Level {target_urutan}: {step.nama_langkah}"
    except ApprovalStep.DoesNotExist:
        return f"Level {target_urutan}: (Step Not Found)"
# ------------------------------------------------------------------
# perhitungan lama waktu proses form
# ------------------------------------------------------------------    
    
def calculate_total_processing_time(checksheet):
    """
    Menghitung total durasi waktu yang telah berjalan (elapsed time)
    dari status SUBMIT hingga status saat ini (atau FINALIZED jika sudah FIN).
    """
    
    if not checksheet.submitted_at:
        return "Belum Diajukan (Draft)"

    # Jika sudah Finalized (FIN) atau Rejected (REJ), gunakan waktu final/reject
    if checksheet.status == 'FIN' and checksheet.finalized_at:
        end_time = checksheet.finalized_at
    elif checksheet.status == 'REJ':
        # Asumsi: Jika REJECTED, kita ambil waktu log REJECTED terakhir sebagai waktu akhir
        # (atau jika Anda punya field rejected_at, gunakan itu)
        # Untuk kasus ini, kita gunakan submitted_at hingga sekarang, atau tambahkan logika log.
        # Untuk tujuan ini, kita anggap waktu akhir adalah waktu saat ini.
        end_time = timezone.now() 
    else:
        # Jika statusnya masih berjalan (SUB, APR1, APR2, dll), waktu akhir adalah saat ini.
        end_time = timezone.now()
    
    # Hitung selisih waktu
    total_duration = end_time - checksheet.submitted_at
    
    # Format ke string yang mudah dibaca (misalnya "X days, H:MM:SS")
    return str(total_duration).split('.')[0]
# ------------------------------------------------------------------
# PROFIL & PASSWORD
# ------------------------------------------------------------------
@login_required
def user_profile(request):
    return render(request, "accounts/user_profile.html", {
        "user": request.user,
        "user_groups": request.user.groups.all(),
    })


@login_required
def password_change_view(request):
    if request.method == "POST":
        form = PasswordChangeForm(user=request.user, data=request.POST)
        if form.is_valid():
            user = form.save()
            update_session_auth_hash(request, user)
            messages.success(request, "✅ Password berhasil diperbarui.")
            return redirect("user_profile")
        else:
            messages.error(request, "❌ Terjadi kesalahan. Silakan cek kembali.")
    else:
        form = PasswordChangeForm(user=request.user)

    return render(request, "accounts/password_change.html", {"form": form})

# ------------------------------------------------------------------
# MASTER DASHBOARD VIEW BARU
# ------------------------------------------------------------------
@login_required
def render_custom_dashboard(request):
    user = request.user
    my_admin_site = admin_site # Menggunakan instance AdminSite Anda
    
    # --- 1. Ambil Konteks Admin (PENTING untuk Sidebar & Jazzmin) ---
    context = my_admin_site.each_context(request)
    # Ini secara otomatis memfilter sidebar berdasarkan izin user
    context['app_list'] = my_admin_site.get_app_list(request)

    # --- 2. Tentukan Template & Data Berdasarkan Grup ---
   
        
    if is_in_group_a(user):
        template_name = 'accounts/dashboard_user_a.html'
        context['group_name'] = "Group A (Approval Level 1)"
        # Isi data yang dibutuhkan dashboard A
        context['pending_docs'] = ChecksheetPI.objects.filter(status='SUB').order_by('-submitted_at')

        all_live_docs = ChecksheetPI.objects.exclude(status__in=['DRAFT']).order_by('-submitted_at')

        monitoring_data = []
        for doc in all_live_docs:
            # Hitung metrik yang dibutuhkan
            bottleneck_data = calculate_bottleneck_info(doc)
            elapsed_time = calculate_total_processing_time(doc)
            current_step = get_current_approval_step_name(doc.status)

            # Jika REJ atau FIN, 'current_approval_step' harus disesuaikan
            next_step = '-'
            if doc.status not in ['FIN', 'REJ']:
                next_step = get_next_approval_step_name(doc.status)
            if doc.status == 'FIN':
                current_step = 'Selesai (Finalized)'
            elif doc.status == 'REJ':
                current_step = 'Ditolak (Rejected)'

            # Siapkan data untuk dikirim ke template
            doc_data = {
                'pk': doc.pk,
                'cn_sap': doc.cn_sap,
                'status': doc.status,
                'current_approval_step': current_step,
                'next_approval_step': next_step,
                'submitted_at': doc.submitted_at.strftime("%Y-%m-%d %H:%M"),
                
                # Metrik Monitoring
                'current_approval_step': current_step,
                'longest_duration': bottleneck_data['longest_duration'],
                'bottleneck_step': bottleneck_data['bottleneck_step'],
                'elapsed_time': elapsed_time,
            }
            monitoring_data.append(doc_data)

        context['monitoring_data'] = monitoring_data # Variabel baru untuk menampung semua data monitoring
        
        # Kita juga bisa menyediakan daftar dokumen yang butuh aksi (opsional)
        context['pending_my_action'] = ChecksheetPI.objects.filter(status='SUB')
        
    elif is_in_group_b(user):
        template_name = 'accounts/dashboard_user_b.html'
        context['group_name'] = "Group B (Approval Level 2)"
        context['pending_docs'] = ChecksheetPI.objects.filter(status='APR1').order_by('-submitted_at')

        
    elif is_in_group_b(user):
        template_name = 'accounts/dashboard_user_b.html'
        context['group_name'] = "Group B (Approval Level 2)"
        # Isi data yang dibutuhkan dashboard B
        context['pending_docs'] = ChecksheetPI.objects.filter(status='APR1').order_by('-submitted_at')
        
    elif is_in_group_c(user):
        template_name = 'accounts/dashboard_user_c.html'
        context['group_name'] = "Group C (Approval Level 3 / Final)"
        # Isi data yang dibutuhkan dashboard C
        context['pending_docs'] = ChecksheetPI.objects.filter(status='APR2').order_by('-submitted_at')
    elif user.is_superuser:
            # Superuser diarahkan ke admin index bawaan (yang sekarang akan memiliki sidebar)
            template_name = 'admin/index.html'
            context['group_name'] = 'Superuser'
            # Di sini, Anda mungkin ingin menambahkan data kustom untuk superuser
            context['pending_docs'] = ChecksheetPI.objects.filter(status__in=['SUB', 'APR1', 'APR2']).order_by('-submitted_at')    
            
    else:
        # Fallback
        template_name = 'accounts/dashboard_default.html'
        context['group_name'] = "User Default"

    # --- 3. Tambahkan semua data lain yang dibutuhkan dashboard Anda di sini (misalnya bottleneck) ---
    # Contoh:
    # if 'pending_docs' in context:
    #     for doc in context['pending_docs']:
    #         doc.bottleneck_info = calculate_bottleneck_info(doc)
    # AKTIFKAN PENGHITUNGAN BOTTLENECK DI SINI
    if 'pending_docs' in context:
         for doc in context['pending_docs']:
             # Tambahkan dua atribut baru ke setiap objek ChecksheetPI
             bottleneck_data = calculate_bottleneck_info(doc)
             doc.bottleneck_step = bottleneck_data['bottleneck_step']
             doc.longest_duration = bottleneck_data['longest_duration']
             doc.current_approval_step = get_current_approval_step_name(doc.status)
             doc.elapsed_time = calculate_total_processing_time(doc)

    return render(request, template_name, context)

@staff_member_required # Hanya untuk user staff/superuser
def render_superuser_dashboard(request):
    """Menampilkan dashboard global monitoring untuk Superuser/Admin."""
    user = request.user
    my_admin_site = admin_site
    
    # Ambil konteks admin standar (untuk sidebar, header, dll.)
    context = my_admin_site.each_context(request)
    context['app_list'] = my_admin_site.get_app_list(request)
    context['group_name'] = "GLOBAL MONITORING DASHBOARD"

    # Ambil semua dokumen yang bukan DRAFT atau REJECTED
    all_docs = ChecksheetPI.objects.exclude(status__in=['DRAFT', 'REJ']).order_by('-submitted_at')
    
    monitoring_data = []
    
    for doc in all_docs:
        # Hitung metrik waktu
        bottleneck_data = calculate_bottleneck_info(doc)
        elapsed_time = calculate_total_processing_time(doc)
        current_step = get_current_approval_step_name(doc.status)

        # Siapkan data untuk template
        doc_data = {
            'pk': doc.pk,
            'cn_sap': doc.cn_sap,
            'status': doc.status,
            'submitted_at': doc.submitted_at.strftime("%Y-%m-%d %H:%M"),
            'current_approval_step': current_step,
            'longest_duration': bottleneck_data['longest_duration'],
            'bottleneck_step': bottleneck_data['bottleneck_step'],
            'elapsed_time': elapsed_time,
        }
        monitoring_data.append(doc_data)

    context['monitoring_data'] = monitoring_data
    
    # Template yang akan kita buat
    return render(request, 'accounts/dashboard_superuser.html', context)