/**
 * quick_upload_disposed.js
 * Sistem Upload & Verifikasi OCR Cepat untuk Dokumen Asset Disposal (INSIDE/PRIMA)
 */

// ── KOORDINAT ENDPOINT DJANGO ──
var QUICK_UPLOAD_URL  = "/asset/upload-quick-disposed/";
var QUICK_DELETE_URL  = "/asset/delete-quick-disposed/";

// ============================================================
// HELPER FUNCTIONS (GLOBAL SCOPE)
// ============================================================

function getCsrfToken() {
    var matches = document.cookie.match(/csrftoken=([^;]+)/);
    if (matches) return matches[1];
    var csrfInput = document.querySelector('[name=csrfmiddlewaretoken]');
    return csrfInput ? csrfInput.value : "";
}

function closeModalClean(modalEl) {
    if (!modalEl) return;
    modalEl.classList.remove('show');
    modalEl.style.display = 'none';
    document.querySelectorAll('.modal-backdrop').forEach(function (el) { el.remove(); });
    document.body.classList.remove('modal-open');
    document.body.style.overflow    = '';
    document.body.style.paddingRight = '';
}

function isValidFileType(file) {
    var allowed = ['.pdf', '.png', '.jpg', '.jpeg'];
    var ext     = '.' + file.name.split('.').pop().toLowerCase();
    return allowed.includes(ext);
}

function renderOcrFeedback(type, message) {
    var ocrBox = document.getElementById('ocrFeedbackBox');
    if (!ocrBox) return;

    var styles = {
        loading: { bg: '#e8f4fd', color: '#0d3c61', border: '#1883ff', icon: '🔄' },
        success: { bg: '#d4edda', color: '#155724', border: '#28a745', icon: '✅' },
        warning: { bg: '#fff3cd', color: '#856404', border: '#ffc107', icon: '⚠️' },
        error:   { bg: '#f8d7da', color: '#721c24', border: '#dc3545', icon: '❌' },
    };

    var s = styles[type] || styles.warning;
    ocrBox.innerHTML = `
        <div style="background:${s.bg};color:${s.color};padding:12px;border-radius:6px;
                    border-left:4px solid ${s.border};font-size:13px;margin-top:10px;line-height: 1.5;">
            ${s.icon} <strong>${type === 'loading' ? 'Memproses' : type === 'success' ? 'Berhasil' : 'Perhatian'}:</strong> ${message}
        </div>`;
}

// ============================================================
// FUNGSI UTAMA 1: BUKA MODAL UPLOAD (GLOBAL)
// ============================================================
window.openUploadModal = function (cnSap, docType, docLabel) {
    if (!cnSap || !docType) {
        alert("Gagal membuka modal: Parameter tidak lengkap.");
        return;
    }

    // Default label jika parameter tidak disertakan dari template
    docLabel = docLabel || docType.toUpperCase().replace('_', ' ');

    var modalEl = document.getElementById('uploadDocModal');

    // ── Buat elemen modal secara dinamis jika belum ada di DOM ──
    if (!modalEl) {
        var modalHTML = `
        <div class="modal fade" id="uploadDocModal" tabindex="-1" role="dialog"
             style="z-index:1060; background:rgba(0,0,0,0.5); display:none;">
            <div class="modal-dialog modal-dialog-centered" role="document">
                <form id="uploadDocForm" method="POST" enctype="multipart/form-data">
                    <input type="hidden" name="csrfmiddlewaretoken" value="${getCsrfToken()}">
                    <div class="modal-content" style="border-radius:8px;background:#fff;box-shadow:0 4px 12px rgba(0,0,0,0.2);">
                        <div class="modal-header" style="display:flex;justify-content:space-between;align-items:center;padding:16px 20px;border-bottom:1px solid #e0e0e0;">
                            <h5 class="modal-title" id="modalDocTitle" style="font-weight:bold;color:#333;margin:0;font-size:15px;">
                                Upload Dokumen
                            </h5>
                            <button type="button" class="btn-close-modal"
                                style="background:none;border:none;font-size:22px;cursor:pointer;color:#aaa;line-height:1;"
                                title="Tutup">&times;</button>
                        </div>
                        <div class="modal-body" style="padding:20px;">
                            <input type="hidden" name="cn_sap"   id="modalCnSap">
                            <input type="hidden" name="doc_type" id="modalDocType">
                            <div style="margin-bottom:12px;">
                                <label style="font-weight:600;color:#555;display:block;margin-bottom:6px;font-size:13px;">
                                    Pilih File — <span id="labelDocName" style="color:#1883ff;"></span>
                                </label>
                                <input type="file" name="document_file" id="modalFileInput"
                                    accept=".pdf,.png,.jpg,.jpeg"
                                    style="width:100%;box-sizing:border-box;padding:6px;border:1.5px solid #ddd;border-radius:4px;font-size:13px;">
                                <small style="color:#888;font-size:11px;margin-top:4px;display:block;">
                                    Format yang diizinkan: PDF, PNG, JPG, JPEG
                                </small>
                            </div>
                            <div id="ocrFeedbackBox"></div>
                        </div>
                        <div class="modal-footer" style="display:flex;justify-content:flex-end;gap:8px;padding:12px 20px;border-top:1px solid #e0e0e0;">
                            <button type="button" class="btn-close-modal" id="btnCancelDoc"
                                style="background:#6c757d;color:white;border:none;padding:7px 16px;border-radius:5px;cursor:pointer;font-size:13px;transition:background 0.2s;">
                                Batal
                            </button>
                            <button type="submit" id="btnSubmitDoc"
                                style="background:#1883ff;color:white;border:none;padding:7px 16px;border-radius:5px;font-weight:600;cursor:pointer;font-size:13px;transition:background 0.2s;">
                                💾 Simpan Dokumen
                            </button>
                        </div>
                    </div>
                </form>
            </div>
        </div>`;

        var wrapper = document.createElement('div');
        wrapper.innerHTML = modalHTML;
        document.body.appendChild(wrapper.firstElementChild);
        modalEl = document.getElementById('uploadDocModal');

        // ── Bind event tombol tutup/batal ──
        modalEl.querySelectorAll('.btn-close-modal').forEach(function (btn) {
            btn.addEventListener('click', function () { closeModalClean(modalEl); });
        });

        // ── Klik area luar modal untuk menutup ──
        modalEl.addEventListener('click', function (e) {
            if (e.target === modalEl) closeModalClean(modalEl);
        });

        // ── Daftarkan handler submit form ──
        bindFormSubmit();
    }

    // ── RESET STATE MODAL SEBELUM DITAMPILKAN ──
    var ocrBox    = document.getElementById('ocrFeedbackBox');       
    var submitBtn = document.getElementById('btnSubmitDoc');
    var cancelBtn = document.getElementById('btnCancelDoc');
    var fileInput = document.getElementById('modalFileInput');

    if (ocrBox)    ocrBox.innerHTML = '';
    if (fileInput) fileInput.value  = '';

    if (submitBtn) {
        submitBtn.style.display = '';
        submitBtn.disabled      = false;
        submitBtn.textContent   = '💾 Simpan Dokumen';
        submitBtn.style.background = '#1883ff';
    }

    if (cancelBtn) {
        cancelBtn.textContent      = 'Batal';
        cancelBtn.style.background = '#6c757d';
    }

    // ── Suntik data dinamis ke dalam modal form ──
    document.getElementById('modalDocTitle').innerText = `Upload ${docLabel} — Unit ${cnSap}`;
    document.getElementById('labelDocName').innerText  = docLabel;
    document.getElementById('modalCnSap').value        = cnSap;
    document.getElementById('modalDocType').value      = docType;

    document.getElementById('uploadDocForm').action = QUICK_UPLOAD_URL;

    // ── Munculkan Modal ──
    modalEl.style.display = 'block';
    setTimeout(function() {
        modalEl.classList.add('show');
    }, 15);
};

// ============================================================
// BIND SUBMIT FORM (UPLOAD AJAX & OCR FEEDBACK)
// ============================================================

function bindFormSubmit() {
    var form = document.getElementById('uploadDocForm');
    if (!form || form.dataset.bound === 'true') return;
    form.dataset.bound = 'true';

    form.addEventListener('submit', function (e) {
        e.preventDefault();

        var submitBtn = document.getElementById('btnSubmitDoc');
        var cancelBtn = document.getElementById('btnCancelDoc');
        var fileInput = document.getElementById('modalFileInput');
        var docType   = document.getElementById('modalDocType').value.toLowerCase();
        var cnSap     = document.getElementById('modalCnSap').value;

        if (!fileInput || !fileInput.files || fileInput.files.length === 0) {
            alert('Silakan pilih file terlebih dahulu.');
            return;
        }

        var selectedFile = fileInput.files[0];
        if (!isValidFileType(selectedFile)) {
            alert('Format file tidak didukung.\nGunakan: PDF, PNG, JPG, atau JPEG.');
            return;
        }

        // Batas maksimal upload file 10MB
        var maxSize = 10 * 1024 * 1024;
        if (selectedFile.size > maxSize) {
            alert('Ukuran file terlalu besar. Maksimum 10MB.');
            return;
        }

        submitBtn.disabled    = true;
        submitBtn.textContent = '⏳ Mengunggah...';

        // 🌟 PERBAIKAN 1: Tambahkan 'inspeksi_unit' ke target OCR agar Loading Text EasyOCR menyala
        var targetOcrTypes = ['rca', 'pengajuan_disposed', 'foto_4_sisi', 'inspeksi_unit'];
        if (targetOcrTypes.includes(docType)) {
            renderOcrFeedback('loading',
                'Sistem sedang mengekstrak teks dokumen dengan EasyOCR. ' +
                'Proses ini membutuhkan beberapa saat, mohon tunggu...'
            );
        }

        var formData = new FormData(form);

        fetch(QUICK_UPLOAD_URL, {
            method:  'POST',
            body:    formData,
            headers: {
                'X-Requested-With': 'XMLHttpRequest',
                'X-CSRFToken':      getCsrfToken(),
            },
        })
        .then(function (response) {
            if (!response.ok) throw new Error('Server error: ' + response.status);
            return response.json();
        })
        .then(function (result) {

            // ── KASUS 1: VERIFIKASI OCR GAGAL (File tidak disimpan) ──
            if (!result.success && result.ocr_failed) {
                var errorTable = '';
                
                // JIKA FOTO 4 SISI GAGAL
                if (docType === 'foto_4_sisi' && result.detail_error) {
                    var det = result.detail_error;
                    errorTable = `
                        <table style="font-size:12px;width:100%;border-collapse:collapse;margin-top:5px;">
                            <tr><td style="padding:2px 0;width:140px;">- Tampak Depan</td><td>: <strong>${det.tampak_depan ? '✅ Ketemu' : '❌ Tidak Ada'}</strong></td></tr>
                            <tr><td style="padding:2px 0;">- Tampak Belakang</td><td>: <strong>${det.tampak_belakang ? '✅ Ketemu' : '❌ Tidak Ada'}</strong></td></tr>
                            <tr><td style="padding:2px 0;">- Tampak Kanan</td><td>: <strong>${det.tampak_kanan ? '✅ Ketemu' : '❌ Tidak Ada'}</strong></td></tr>
                            <tr><td style="padding:2px 0;">- Tampak Kiri</td><td>: <strong>${det.tampak_kiri ? '✅ Ketemu' : '❌ Tidak Ada'}</strong></td></tr>
                            <tr style="border-top:1px dashed #ccc;"><td style="padding:4px 0;">- Kecocokan Unit CN</td><td>: <strong>${det.cn_status ? '✅ Cocok' : '❌ Tidak Cocok'}</strong></td></tr>
                        </table>`;
                } else {
                    // Dokumen teks biasa (RCA / Pengajuan / Inspeksi Unit)
                    errorTable = `
                        <table style="font-size:12px;width:100%;border-collapse:collapse;margin-top:5px;">
                            <tr><td style="padding:3px 0;width:130px;">- No. Dokumen</td><td>: <strong>${result.no_dokumen || '-'}</strong></td></tr>
                            <tr><td style="padding:3px 0;">- Nama Dokumen</td><td>: <strong>${result.nama_dok_ocr || '-'}</strong></td></tr>
                        </table>`;
                }

                renderOcrFeedback('warning',
                    '<strong>Dokumen tidak tersimpan</strong> — Gagal verifikasi OCR:<br><br>' +
                    result.ocr_message +
                    '<br>' + errorTable +
                    '<br><span style="color:#721c24;font-weight:bold;">' +
                    '⚠️ Periksa kembali dokumen dan silakan unggah ulang dokumen yang sesuai.</span>'
                );

                submitBtn.style.display = 'none';

                if (cancelBtn) {
                    cancelBtn.textContent      = '✕ Tutup & Upload Ulang';
                    cancelBtn.style.background = '#dc3545';
                }

                if (fileInput) fileInput.value = '';
                return;
            }

            // ── KASUS 2: UPLOAD & VERIFIKASI SUKSES ──
            if (result.success) {
                // Non-OCR File: Langsung tutup modal & reload halaman
                if (!targetOcrTypes.includes(docType) || result.ocr_valid === undefined) {
                    closeModalClean(document.getElementById('uploadDocModal'));
                    alert('✅ Dokumen ' + result.doc_label + ' untuk unit ' + result.cn_sap + ' berhasil diunggah!');
                    window.location.reload();
                    return;
                }

                // OCR File Valid: Tampilkan umpan balik sukses, tunggu sebentar lalu reload
                if (result.ocr_valid) {
                    var infoTambahan = '';
                    if (docType === 'rca' && result.usd_max && result.usd_max !== '-') {
                        infoTambahan = '<br><small>Nilai estimasi biaya RCA: <strong>' + result.usd_max + '</strong></small>';
                    } else if (docType === 'pengajuan_disposed' && result.no_pengajuan && result.no_pengajuan !== '-') {
                        infoTambahan = '<br><small>No. Pengajuan: <strong>' + result.no_pengajuan + '</strong></small>';
                    }

                    renderOcrFeedback('success', result.ocr_message + infoTambahan);
                    
                    submitBtn.textContent      = '✓ Tersimpan';
                    submitBtn.style.background = '#28a745';
                    submitBtn.disabled         = true;

                    setTimeout(function () {
                        closeModalClean(document.getElementById('uploadDocModal'));
                        window.location.reload();
                    }, 3000);
                }
                return;
            }

            // ── KASUS 3: ERROR SERVER KLASIK ──
            renderOcrFeedback('error', result.error || 'Terjadi kesalahan pada server.');
            submitBtn.disabled    = false;
            submitBtn.textContent = '💾 Simpan Dokumen';
        })
        .catch(function (err) {
            console.error('[Upload] Error:', err);
            renderOcrFeedback('error', 'Gagal terhubung ke server: ' + err.message);
            submitBtn.disabled    = false;
            submitBtn.textContent = '💾 Simpan Dokumen';
        });
    });
}

// Ensure binding form submit saat dokumen siap di awal load
document.addEventListener('DOMContentLoaded', bindFormSubmit);


// ============================================================
// FUNGSI UTAMA 2: HAPUS DOKUMEN DISPOSAL (GLOBAL)
// ============================================================
window.deleteDocument = function (cnSap, docType, docLabel) {
    if (!cnSap || !docType) {
        alert("Gagal menghapus: Parameter unit tidak lengkap.");
        return;
    }
    
    docLabel = docLabel || docType.toUpperCase().replace('_', ' ');

    if (!confirm(
        `Apakah Anda yakin ingin menghapus dokumen [${docLabel}] untuk unit ${cnSap}?\n` +
        `File fisik yang terhapus dari server tidak dapat dikembalikan.`
    )) return;

    fetch(QUICK_DELETE_URL, {
        method:  'POST',
        body:    new URLSearchParams({ cn_sap: cnSap, doc_type: docType }),
        headers: {
            'X-Requested-With':     'XMLHttpRequest',
            'X-CSRFToken':          getCsrfToken(),
            'Content-Type':         'application/x-www-form-urlencoded',
        },
    })
    .then(function (response) {
        if (!response.ok) throw new Error('Server error: ' + response.status);
        return response.json();
    })
    .then(function (result) {
        if (result.success) {
            alert(`🗑️ Dokumen ${result.doc_label} untuk unit ${cnSap} berhasil dihapus.`);
            window.location.reload();
        } else {
            alert('❌ Gagal menghapus dokumen: ' + (result.error || 'Error tidak diketahui.'));
        }
    })
    .catch(function (err) {
        console.error('[Delete] Error:', err);
        alert('❌ Gagal terhubung ke server saat menghapus: ' + err.message);
    });
};