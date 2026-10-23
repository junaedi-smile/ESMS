// static/js/forms/form_foto_4_sisi_disposed.js

// ============================================================
// PREVIEW GAMBAR
// ============================================================
window.previewImageModal = function(input, previewId, noPreviewId) {
    var img        = document.getElementById(previewId);
    var noPreview = noPreviewId ? document.getElementById(noPreviewId) : null;

    if (!img) {
        console.warn('[previewImageModal] element tidak ditemukan:', previewId);
        return;
    }

    if (input.files && input.files[0]) {
        var file = input.files[0];

        // Validasi ukuran max 5MB
        if (file.size > 5 * 1024 * 1024) {
            alert('File "' + file.name + '" terlalu besar. Maksimum 5MB.');
            input.value = '';
            return;
        }

        // PDF → tidak bisa preview, tampilkan nama file
        if (file.type === 'application/pdf') {
            img.style.display = 'none';
            if (noPreview) {
                noPreview.style.display = 'flex';
                noPreview.innerHTML = '📄 <strong style="margin-left:4px;">'
                    + file.name + '</strong>';
            }
            return;
        }

        // ✅ Preview gambar
        var reader = new FileReader();
        reader.onload = function(e) {
            img.src             = e.target.result;
            img.style.display = 'block';
            // ✅ Sembunyikan teks "Belum ada preview"
            if (noPreview) noPreview.style.display = 'none';
        };
        reader.onerror = function() {
            console.error('[previewImageModal] FileReader gagal membaca file.');
        };
        reader.readAsDataURL(file);

    } else {
        // Reset
        img.src             = '';
        img.style.display = 'none';
        if (noPreview) {
            noPreview.style.display = 'flex';
            noPreview.innerText     = 'Belum ada preview';
        }
    }
};


// ============================================================
// BUKA MODAL
// ============================================================
window.openFoto4SisiModal = function(cnSap, cnEllipse, sn, egi, fotoData) {
    cnEllipse = cnEllipse || '-';
    sn        = sn        || '-';
    egi       = egi       || '-';

    var setEl = function(id, val) {
        var el = document.getElementById(id);
        if (!el) return;
        if (el.tagName === 'INPUT') el.value = val;
        else el.innerText = val;
    };

    setEl('input_cn_sap',     cnSap);
    setEl('modal_cn_sap',     cnSap);
    setEl('modal_cn_ellipse', cnEllipse);
    setEl('modal_sn',         sn);
    setEl('modal_egi',        egi);

    // Reset form input file
    var form = document.getElementById('formFoto4SisiData');
    if (form) {
        form.reset();
        setEl('input_cn_sap', cnSap);
    }

    // ✅ Tampilkan foto lama pada kotak preview masing-masing sisi jika tersedia
    var sisiList = ['depan', 'belakang', 'kanan', 'kiri'];
    sisiList.forEach(function(sisi) {
        var img       = document.getElementById('preview_' + sisi);
        var noPreview = document.getElementById('no_preview_' + sisi);
        var oldUrl    = (fotoData && fotoData[sisi]) ? fotoData[sisi] : null;

        if (oldUrl) {
            if (img) {
                img.src = oldUrl;
                img.style.display = 'block';
            }
            if (noPreview) {
                noPreview.style.display = 'none';
            }
        } else {
            if (img) { img.src = ''; img.style.display = 'none'; }
            if (noPreview) {
                noPreview.style.display = 'flex';
                noPreview.innerText = 'Belum ada preview';
            }
        }
    });

    // Reset tombol
    var btn = document.getElementById('btnSimpanFoto');
    if (btn) { btn.disabled = false; btn.textContent = '💾 Simpan Perubahan'; }

    var btnPdf = document.getElementById('btnDownloadPdf');
    if (btnPdf) {
        btnPdf.href = `/asset/api/prepare-disposed/download-pdf/${cnSap}/`;
        btnPdf.style.display = 'inline-block';
    }

    var btnSubmit = document.getElementById('btnSubmitApproval');
    if (btnSubmit) {
        btnSubmit.style.display = 'inline-block';
    }

    var modalEl = document.getElementById('foto4SisiModal');
    if (!modalEl) {
        console.error('[foto4SisiModal] Tidak ditemukan di DOM!');
        return;
    }

    if (modalEl.parentElement !== document.body) {
        document.body.appendChild(modalEl);
    }

    _bindFoto4SisiSubmit();

    modalEl.style.zIndex = '99999';

    if (typeof bootstrap !== 'undefined' && typeof bootstrap.Modal === 'function') {
        if (typeof bootstrap.Modal.getInstance === 'function') {
            var existingInstance = bootstrap.Modal.getInstance(modalEl);
            if (existingInstance) {
                existingInstance.dispose();
            }
        }

        var bsModal = new bootstrap.Modal(modalEl, { backdrop: 'static' });
        bsModal.show();

        modalEl.addEventListener('shown.bs.modal', function() {
            var backdrop = document.querySelector('.modal-backdrop');
            if (backdrop) backdrop.style.zIndex = '99998';
            var dialog = modalEl.querySelector('.modal-dialog');
            if (dialog) dialog.style.zIndex = '100000';
        }, { once: true });

    } else {
        console.error('[foto4SisiModal] Bootstrap Modal API tidak tersedia dengan benar!');
        modalEl.style.display    = 'block';
        modalEl.style.background = 'rgba(0,0,0,0.5)';
        document.body.style.overflow = 'hidden';
    }
};


// ============================================================
// TUTUP MODAL
// ============================================================
window.closeFoto4SisiModal = function() {
    var modalEl = document.getElementById('foto4SisiModal');
    if (!modalEl) return;

    if (typeof bootstrap !== 'undefined' && typeof bootstrap.Modal === 'function' && typeof bootstrap.Modal.getInstance === 'function') {
        var bsModal = bootstrap.Modal.getInstance(modalEl);
        if (bsModal) {
            bsModal.hide();
        }
    }

    // ✅ Paksa pembersihan total untuk mengatasi isu blur / sisa backdrop
    modalEl.classList.remove('show');
    modalEl.setAttribute('aria-hidden', 'true');
    modalEl.removeAttribute('aria-modal');
    modalEl.style.display = 'none';

    document.body.classList.remove('modal-open');
    document.body.style.overflow = '';
    document.body.style.paddingRight = '';

    document.querySelectorAll('.modal-backdrop').forEach(function(el) {
        el.remove();
    });
};

// ✅ [TAMBAHAN] Fungsi tutup global khusus untuk modal Lihat Foto agar tombol X dan Close berfungsi mulus
window.closeViewFotoModal = function() {
    var modalEl = document.getElementById('viewFotoModal');
    if (!modalEl) return;

    modalEl.classList.remove('show');
    modalEl.setAttribute('aria-hidden', 'true');
    modalEl.removeAttribute('aria-modal');
    modalEl.style.display = 'none';

    document.body.classList.remove('modal-open');
    document.body.style.overflow = '';
    document.body.style.paddingRight = '';

    document.querySelectorAll('.modal-backdrop').forEach(function(el) {
        el.remove();
    });
};


// ============================================================
// BIND SUBMIT
// ============================================================
function _bindFoto4SisiSubmit() {
    var form = document.getElementById('formFoto4SisiData');
    if (!form) {
        console.warn('[foto4Sisi] Form tidak ditemukan saat _bindFoto4SisiSubmit.');
        return;
    }

    if (form.dataset.foto4SisiBound === 'true') return;
    form.dataset.foto4SisiBound = 'true';

    form.addEventListener('submit', function(e) {
        e.preventDefault();

        var btn = document.getElementById('btnSimpanFoto');

        var inputs = [
            { name: 'tampak_depan',        label: 'Tampak Depan' },
            { name: 'tampak_belakang',      label: 'Tampak Belakang' },
            { name: 'tampak_samping_kanan', label: 'Tampak Samping Kanan' },
            { name: 'tampak_samping_kiri',  label: 'Tampak Samping Kiri' },
        ];

        for (var i = 0; i < inputs.length; i++) {
            var inp = form.querySelector('input[name="' + inputs[i].name + '"]');
            if (!inp || !inp.files || inp.files.length === 0) {
                _swalOrAlert('warning', 'Perhatian',
                    'File "' + inputs[i].label + '" belum dipilih.');
                return;
            }
        }

        if (btn) { btn.disabled = true; btn.textContent = '⏳ Menyimpan...'; }

        if (typeof Swal !== 'undefined') {
            Swal.fire({
                title: 'Menyimpan Foto...',
                text: 'Mohon tunggu',
                allowOutsideClick: false,
                didOpen: function() { Swal.showLoading(); }
            });
        }

        var formData  = new FormData(form);
        var csrfMatch = document.cookie.match(/csrftoken=([^;]+)/);
        var csrfToken = csrfMatch ? csrfMatch[1] : '';

        fetch('/asset/api/prepare-disposed/upload-foto-4-sisi/', {
            method:  'POST',
            body:    formData,
            headers: { 'X-CSRFToken': csrfToken },
        })
        .then(function(response) {
            var ct = response.headers.get('content-type') || '';
            if (!ct.includes('application/json')) {
                throw new Error('Session expired. Silakan refresh halaman.');
            }
            return response.json();
        })
        .then(function(data) {
            if (data.status === 'success') {
                if (typeof Swal !== 'undefined') {
                    Swal.fire('Berhasil!',
                        data.message || 'Foto berhasil disimpan.', 'success')
                    .then(function() {
                        closeFoto4SisiModal();
                        location.reload();
                    });
                } else {
                    alert('Berhasil! ' + (data.message || ''));
                    closeFoto4SisiModal();
                    location.reload();
                }
            } else {
                if (btn) { btn.disabled = false; btn.textContent = '💾 Simpan Foto'; }
                _swalOrAlert('error', 'Gagal!', data.message || 'Terjadi kesalahan.');
            }
        })
        .catch(function(err) {
            if (btn) { btn.disabled = false; btn.textContent = '💾 Simpan Foto'; }
            console.error('[foto4Sisi] Error:', err);
            _swalOrAlert('error', 'Gagal!', err.message || 'Koneksi bermasalah.');
        });
    });
}


// ============================================================
// HELPER — SweetAlert atau alert biasa
// ============================================================
function _swalOrAlert(type, title, message) {
    if (typeof Swal !== 'undefined') {
        Swal.fire(title, message, type);
    } else {
        alert(title + ': ' + message);
    }
}


// ============================================================
// DOMContentLoaded: Inisialisasi Modal, Pindah ke Body, & Form Fallback
// ============================================================
document.addEventListener("DOMContentLoaded", function() {
    
    // ✅ [PERBAIKAN] Pindahkan modal view & edit ke document.body agar terbebas dari overflow/z-index Jazzmin
    const viewModalEl = document.getElementById('viewFotoModal');
    const editModalEl = document.getElementById('foto4SisiModal');
    
    if (viewModalEl) {
        document.body.appendChild(viewModalEl);
    }

    if (editModalEl) {
        document.body.appendChild(editModalEl);
    }

    // 2. FALLBACK: Coba bind jika form upload/edit sudah ada saat DOMContentLoaded
    var form = document.getElementById('formFoto4SisiData');
    if (form && typeof _bindFoto4SisiSubmit === 'function') {
        _bindFoto4SisiSubmit();
    }
});


// ============================================================
// FUNGSI AKSI TAMBAHAN (PRINT, DOWNLOAD, SUBMIT)
// ============================================================

function handleModalSuccess(cnSap) {
    const btnPdf = document.getElementById('btnDownloadPdf');
    const btnSubmit = document.getElementById('btnSubmitApproval');
    
    if (btnPdf && btnSubmit) {
        btnPdf.href = `/asset/api/prepare-disposed/download-pdf/${cnSap}/`;
        btnPdf.style.display = 'inline-block';
        btnSubmit.style.display = 'inline-block';
    }
}

function printFoto4Sisi() {
    const cnSap = document.getElementById('input_cn_sap').value;
    if (!cnSap) {
        alert('Data unit tidak valid.');
        return;
    }
    window.open(`/asset/api/prepare-disposed/download-pdf/${cnSap}/?print=true`, '_blank');
}

function submitApprovalDisposedFromCell(cnSap) {
    if (!cnSap) return;

    if (!confirm(`Yakin ingin submit Form Foto 4 Sisi unit ${cnSap} kepada Atasan?`)) return;

    var csrfMatch = document.cookie.match(/csrftoken=([^;]+)/);
    var csrfToken = csrfMatch ? csrfMatch[1] : '';

    // ✅ URL baru per form Foto 4 Sisi
    fetch('/asset/api/prepare-disposed/foto-4-sisi/' + encodeURIComponent(cnSap) + '/submit/', {
        method: 'POST',
        headers: { 'X-CSRFToken': csrfToken }
    })
    .then(function(response) {
        var ct = response.headers.get('content-type') || '';
        if (!ct.includes('application/json')) {
            throw new Error('Server error (bukan JSON). Kemungkinan session expired.');
        }
        return response.json();
    })
    .then(function(data) {
        if (data.status === 'success') {
            if (typeof Swal !== 'undefined') {
                Swal.fire('Berhasil!', data.message, 'success').then(function() {
                    location.reload();
                });
            } else {
                alert(data.message);
                location.reload();
            }
        } else {
            if (typeof Swal !== 'undefined') {
                Swal.fire('Gagal!', data.message || 'Terjadi kesalahan.', 'error');
            } else {
                alert('Gagal: ' + (data.message || 'Terjadi kesalahan.'));
            }
        }
    })
    .catch(function(error) {
        console.error('[submitFoto4Sisi] Error:', error);
        alert('Gagal terhubung ke server: ' + error.message);
    });
}

// ============================================================
// ✅ BARU: Approve Foto 4 Sisi (dipanggil dari halaman atasan)
// ============================================================
function approveFoto4Sisi(cnSap) {
    if (!cnSap) return;
    if (!confirm(`Approve Form Foto 4 Sisi unit ${cnSap}?`)) return;

    var csrfToken = getCookie('csrftoken');

    fetch('/asset/api/prepare-disposed/foto-4-sisi/' + encodeURIComponent(cnSap) + '/approve/', {
        method: 'POST',
        headers: { 'X-CSRFToken': csrfToken }
    })
    .then(function(r) { return r.json(); })
    .then(function(data) {
        if (data.status === 'success') {
            if (typeof Swal !== 'undefined') {
                Swal.fire('Approved!', data.message, 'success').then(function() { location.reload(); });
            } else {
                alert(data.message); location.reload();
            }
        } else {
            alert('Gagal: ' + data.message);
        }
    })
    .catch(function(e) { alert('Error: ' + e.message); });
}

// ============================================================
// HAPUS SEMUA FOTO LANGSUNG DARI TABEL ADMIN (TANPA MODAL)
// ============================================================
window.hapusSemuaFotoDirect = function(cnSap) {
    var executeDelete = function() {
        var csrftoken = '';
        var name = 'csrftoken';
        var cookies = document.cookie.split(';');
        for (var i = 0; i < cookies.length; i++) {
            var cookie = cookies[i].trim();
            if (cookie.indexOf(name + '=') === 0) {
                csrftoken = decodeURIComponent(cookie.substring(name.length + 1));
                break;
            }
        }

        fetch('/asset/api/prepare-disposed/delete-foto/' + cnSap + '/', {
            method: 'POST',
            headers: {
                'X-CSRFToken': csrftoken,
                'Content-Type': 'application/json'
            }
        })
        .then(response => response.json())
        .then(data => {
            if (data.status === 'success' || data.success) {
                if (typeof Swal !== 'undefined') {
                    Swal.fire({
                        icon: 'success',
                        title: 'Berhasil!',
                        text: 'Semua foto berhasil dihapus dan status dikembalikan ke Prog.',
                        timer: 1500,
                        showConfirmButton: false
                    }).then(() => {
                        location.reload();
                    });
                } else {
                    alert('Foto berhasil dihapus.');
                    location.reload();
                }
            } else {
                alert('Gagal menghapus foto: ' + (data.message || 'Terjadi kesalahan'));
            }
        })
        .catch(error => {
            console.error('Error:', error);
            alert('Terjadi kesalahan jaringan saat menghapus foto.');
        });
    };

    if (typeof Swal !== 'undefined') {
        Swal.fire({
            title: 'Hapus Semua Foto?',
            text: "Tindakan ini akan menghapus 4 foto terpisah dan mengembalikan status unit ke 'Upload Foto & Prog'!",
            icon: 'warning',
            showCancelButton: true,
            confirmButtonColor: '#dc3545',
            cancelButtonColor: '#6c757d',
            confirmButtonText: 'Ya, Hapus!',
            cancelButtonText: 'Batal'
        }).then((result) => {
            if (result.isConfirmed) {
                executeDelete();
            }
        });
    } else {
        if (confirm("Apakah Anda yakin ingin menghapus semua foto dan mereset statusnya?")) {
            executeDelete();
        }
    }
};

function rejectApprovalDisposed(cnSap) {
    var alasan = prompt("Masukkan alasan penolakan Foto 4 Sisi untuk unit " + cnSap + ":");
    if (alasan === null) return;
    alasan = alasan.trim();
    if (!alasan) { alert("Alasan penolakan wajib diisi!"); return; }

    // ✅ URL baru per form Foto 4 Sisi
    fetch('/asset/api/prepare-disposed/foto-4-sisi/' + encodeURIComponent(cnSap) + '/reject/', {
        method: 'POST',
        headers: {
            'Content-Type': 'application/x-www-form-urlencoded',
            'X-CSRFToken': getCookie('csrftoken')
        },
        body: 'cn_sap=' + encodeURIComponent(cnSap) + '&alasan=' + encodeURIComponent(alasan)
    })
    .then(function(r) { return r.json(); })
    .then(function(data) {
        if (data.status === 'success') {
            alert(data.message); location.reload();
        } else {
            alert("Gagal: " + data.message);
        }
    })
    .catch(function(e) { console.error(e); alert('Terjadi kesalahan koneksi.'); });
}

function getCookie(name) {
    let cookieValue = null;
    if (document.cookie && document.cookie !== '') {
        const cookies = document.cookie.split(';');
        for (let i = 0; i < cookies.length; i++) {
            const cookie = cookies[i].trim();
            if (cookie.substring(0, name.length + 1) === (name + '=')) {
                cookieValue = decodeURIComponent(cookie.substring(name.length + 1));
                break;
            }
        }
    }
    return cookieValue;
}

// ============================================================
// Fungsi untuk Membuka Modal View Foto 4 Sisi
// ============================================================
function openViewFotoModal(cnSap) {
    fetch(`/asset/api/prepare-disposed/detail/${cnSap}/`)
        .then(response => {
            const contentType = response.headers.get("content-type");
            if (contentType && contentType.indexOf("application/json") !== -1) {
                return response.json();
            } else {
                throw new Error("Server mengembalikan halaman HTML (kemungkinan belum login atau URL API salah).");
            }
        })
        .then(data => {
            if (data.status === 'success') {
                document.getElementById('view_cn_sap').textContent = data.cn_sap || '-';
                document.getElementById('view_egi').textContent = data.egi || '-';
                document.getElementById('view_cn_ellipse').textContent = data.cn_ellipse || '-';
                document.getElementById('view_sn').textContent = data.sn || '-';

                document.getElementById('view_img_depan').src = data.tampak_depan || '';
                document.getElementById('view_img_belakang').src = data.tampak_belakang || '';
                document.getElementById('view_img_kanan').src = data.tampak_samping_kanan || '';
                document.getElementById('view_img_kiri').src = data.tampak_samping_kiri || '';

                var modalEl = document.getElementById('viewFotoModal');
                if (modalEl) {
                    if (modalEl.parentElement !== document.body) {
                        document.body.appendChild(modalEl);
                    }
                    modalEl.style.zIndex = '99999';
                }

                var myModal = new bootstrap.Modal(document.getElementById('viewFotoModal'));
                myModal.show();
            } else {
                Swal.fire('Gagal', data.message || 'Gagal memuat data foto unit.', 'error');
            }
        })
        .catch(error => {
            console.error('Error:', error);
            Swal.fire('Error', error.message || 'Terjadi kesalahan pada sistem.', 'error');
        });
}