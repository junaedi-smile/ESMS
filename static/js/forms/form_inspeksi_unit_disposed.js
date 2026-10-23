// ============================================================
// DOMContentLoaded: Pindahkan Modal Inspeksi ke Body
// ============================================================
document.addEventListener("DOMContentLoaded", function() {
    const inspectionModalEl = document.getElementById('inspectionModal');
    if (inspectionModalEl) {
        if (inspectionModalEl.parentElement !== document.body) {
            document.body.appendChild(inspectionModalEl);
        }
    }
});

// ============================================================
// FUNGSI BUKA MODAL INSPEKSI (PERBAIKAN)
// ============================================================
function openInspeksiItemModal(cnSap, equipmentType) {
    const modalContainer = document.getElementById('inspectionModal');
    if (!modalContainer) {
        console.error("Modal elemen tidak ditemukan di DOM!");
        return;
    }

    // ✅ Pastikan modal selalu berada di level body terluar (bebas dari jebakan AdminLTE)
    if (modalContainer.parentElement !== document.body) {
        document.body.appendChild(modalContainer);
    }

    // Ambil data item via Fetch API
    fetch(`/asset/api/prepare-disposed/inspection-items/${cnSap}/`)
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
                
                // ========================================================
                // ✅ ISI DATA HEADER MODAL DARI RESPON `unit_info` BACKEND
                // ========================================================
                const info = data.unit_info || {};
                document.getElementById('header_type').innerText = info.type || equipmentType || '-';
                document.getElementById('header_cn_sap').innerText = info.cn_sap || cnSap || '-';
                document.getElementById('header_egi').innerText = info.egi || egi || '-';
                document.getElementById('header_sn').innerText = info.sn || '-';
                document.getElementById('header_hm_smr').innerText = info.hm_smr || '-';
                document.getElementById('header_location').innerText = info.location || '-';

                // ========================================================
                // RENDER TABEL ITEM INSPEKSI
                // ========================================================
                let tbody = document.getElementById('inspectionTableBody');
                tbody.innerHTML = '';

                data.items.forEach((item, index) => {
                    let row = `
                        <tr>
                            <td>${index + 1}</td>
                            <td>${item.item_group || '-'}</td>
                            <td>${item.item_name || '-'}</td>
                            <td>${item.qty || '-'}</td>
                            <td>
                                <select name="condition_${item.id}" class="form-control item-condition">
                                    <option value="GOOD">Good</option>
                                    <option value="BAD">Bad</option>
                                    <option value="NA">N/A</option>
                                </select>
                            </td>
                            <td>
                                <input type="text" name="remark_${item.id}" class="form-control item-remark" placeholder="Keterangan...">
                                <input type="hidden" class="item-template-id" value="${item.id}">
                            </td>
                        </tr>
                    `;
                    tbody.insertAdjacentHTML('beforeend', row);
                });

                // Simpan CN_SAP ke tombol simpan di modal
                document.getElementById('saveInspectionBtn').setAttribute('data-cnsap', cnSap);
                
                // Atur z-index manual agar tampil di lapisan paling atas
                modalContainer.style.zIndex = '99999';

                // Buka modal menggunakan Bootstrap 5 Native API
                if (typeof bootstrap !== 'undefined' && typeof bootstrap.Modal === 'function') {
                    if (typeof bootstrap.Modal.getInstance === 'function') {
                        let existingInstance = bootstrap.Modal.getInstance(modalContainer);
                        if (existingInstance) {
                            existingInstance.dispose();
                        }
                    }

                    let myModal = new bootstrap.Modal(modalContainer, { backdrop: 'static' });
                    myModal.show();

                    // Penyesuaian z-index backdrop saat modal muncul
                    modalContainer.addEventListener('shown.bs.modal', function() {
                        let backdrop = document.querySelector('.modal-backdrop');
                        if (backdrop) backdrop.style.zIndex = '99998';
                        let dialog = modalContainer.querySelector('.modal-dialog');
                        if (dialog) dialog.style.zIndex = '100000';
                    }, { once: true });
                } else {
                    modalContainer.style.display = 'block';
                    modalContainer.style.background = 'rgba(0,0,0,0.5)';
                    document.body.style.overflow = 'hidden';
                }
            } else {
                alert('Gagal memuat item inspeksi: ' + data.message);
            }
        })
        .catch(error => {
            console.error('Error fetching inspection items:', error);
            alert(error.message);
        });
}

// ============================================================
// ✅ [BARU] FUNGSI TUTUP MODAL INSPEKSI (UNTUK TOMBOL X / CLOSE)
// ============================================================
window.closeInspectionModal = function() {
    const modalContainer = document.getElementById('inspectionModal');
    if (!modalContainer) return;

    if (typeof bootstrap !== 'undefined' && typeof bootstrap.Modal === 'function' && typeof bootstrap.Modal.getInstance === 'function') {
        var bsModal = bootstrap.Modal.getInstance(modalContainer);
        if (bsModal) {
            bsModal.hide();
        }
    }

    // Paksa pembersihan total agar layar tidak tertinggal efek blur/backdrop menggantung
    modalContainer.classList.remove('show');
    modalContainer.setAttribute('aria-hidden', 'true');
    modalContainer.removeAttribute('aria-modal');
    modalContainer.style.display = 'none';

    document.body.classList.remove('modal-open');
    document.body.style.overflow = '';
    document.body.style.paddingRight = '';

    document.querySelectorAll('.modal-backdrop').forEach(function(el) {
        el.remove();
    });
};

// ============================================================
// FUNGSI SIMPAN DATA INSPEKSI
// ============================================================
function saveInspectionData() {
    const btn = document.getElementById('saveInspectionBtn');
    const cnSap = btn.getAttribute('data-cnsap');
    
    if (!cnSap) {
        alert('Nomor CN SAP tidak valid!');
        return;
    }

    let inspections = [];
    let isValid = true;

    // Ambil semua baris pada tabel item inspeksi
    document.querySelectorAll('#inspectionTableBody tr').forEach(tr => {
        let templateIdInput = tr.querySelector('.item-template-id');
        let conditionSelect = tr.querySelector('.item-condition');
        let remarkInput = tr.querySelector('.item-remark');

        if (templateIdInput && conditionSelect) {
            inspections.push({
                template_id: templateIdInput.value,
                condition: conditionSelect.value,
                remark: remarkInput ? remarkInput.value : ''
            });
        }
    });

    if (inspections.length === 0) {
        alert('Tidak ada item inspeksi yang dapat disimpan.');
        return;
    }

    // Ubah status tombol menjadi loading sementara
    btn.disabled = true;
    btn.innerText = 'Menyimpan...';

    fetch(`/asset/api/prepare-disposed/inspection-items/${cnSap}/save/`, {
        method: 'POST',
        headers: {
            'Content-Type': 'application/json',
            'X-CSRFToken': getCookie('csrftoken') // Pastikan fungsi getCookie tersedia di file JS Anda
        },
        body: JSON.stringify({ inspections: inspections })
    })
    .then(response => response.json())
    .then(data => {
        if (data.status === 'success') {
            // Tampilkan notifikasi sukses (bisa menggunakan SweetAlert2 jika ingin lebih elegan)
            if (typeof Swal !== 'undefined') {
                Swal.fire({
                    icon: 'success',
                    title: 'Berhasil!',
                    text: data.message,
                    timer: 1500,
                    showConfirmButton: false
                });
            } else {
                alert(data.message);
            }
            
            // Tutup modal secara bersih
            closeInspectionModal();

            // Refresh halaman agar perubahan status siap approval tampil di change_list
            setTimeout(() => {
                location.reload();
            }, 1200);

        } else {
            alert('Gagal menyimpan: ' + data.message);
            btn.disabled = false;
            btn.innerText = 'Simpan Inspeksi';
        }
    })
    .catch(error => {
        console.error('Error saving inspection:', error);
        alert('Terjadi kesalahan jaringan saat menyimpan data.');
        btn.disabled = false;
        btn.innerText = 'Simpan Inspeksi';
    });
}


// ============================================================
// ✅ BARU: Approve Inspeksi (dipanggil dari halaman atasan)
// ============================================================
function approveInspeksiUnit(cnSap) {
    if (!cnSap) return;
    if (!confirm(`Approve Form Inspeksi Unit ${cnSap}?`)) return;

    fetch('/asset/api/prepare-disposed/inspeksi/' + encodeURIComponent(cnSap) + '/approve/', {
        method: 'POST',
        headers: { 'X-CSRFToken': getCookie('csrftoken') }
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
// ✅ BARU: Reject Inspeksi (dipanggil dari halaman atasan)
// ============================================================
function rejectInspeksiUnit(cnSap) {
    var alasan = prompt("Masukkan alasan penolakan Inspeksi Unit untuk " + cnSap + ":");
    if (alasan === null) return;
    alasan = alasan.trim();
    if (!alasan) { alert("Alasan wajib diisi!"); return; }

    fetch('/asset/api/prepare-disposed/inspeksi/' + encodeURIComponent(cnSap) + '/reject/', {
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
    .catch(function(e) { alert('Terjadi kesalahan koneksi.'); });
}


// Fungsi untuk menghapus/reset data inspeksi (Draft)
function hapusSemuaInspeksiDirect(cnSap) {
    if (!confirm(`PERHATIAN: Apakah Anda yakin ingin menghapus data inspeksi unit ${cnSap} dan mereset status ke Draft?`)) {
        return;
    }

    fetch(`/asset/api/prepare-disposed/inspection-items/${cnSap}/delete/`, {
        method: 'POST',
        headers: {
            'Content-Type': 'application/json',
            'X-CSRFToken': getCookie('csrftoken')
        }
    })
    .then(response => response.json())
    .then(data => {
        if (data.status === 'success') {
            alert('Data inspeksi berhasil direset.');
            location.reload();
        } else {
            alert('Gagal menghapus: ' + data.message);
        }
    })
    .catch(error => console.error('Error deleting inspection:', error));
}

function submitApprovalInspeksiFromCell(cnSap) {
    if (!confirm(`Yakin ingin men-submit approval untuk inspeksi unit ${cnSap}?`)) {
        return;
    }

    // DITAMBAHKAN PREFIKS /asset SESUAI DENGAN STRUKTUR URL DJANGO ANDA
    fetch(`/asset/api/prepare-disposed/inspeksi/${cnSap}/submit/`, {  
        method: 'POST',
        headers: {
            'Content-Type': 'application/json',
            'X-CSRFToken': getCookie('csrftoken')
        },
        body: JSON.stringify({}) 
    })
    .then(response => {
        if (!response.ok) {
            return response.json().then(errData => {
                throw new Error(errData.message || 'Terjadi kesalahan pada server.');
            }).catch(() => {
                throw new Error(`Server merespons dengan status ${response.status}`);
            });
        }
        return response.json();
    })
    .then(data => {
        if (data.status === 'success' || data.success) {
            alert('Berhasil men-submit approval inspeksi.');
            location.reload(); 
        } else {
            alert('Gagal: ' + (data.message || 'Terjadi kesalahan sistem.'));
        }
    })
    .catch(error => {
        console.error('Error:', error);
        alert(error.message || 'Terjadi kesalahan koneksi ke server.');
    });
}

// Helper standar untuk mengambil CSRF Token di Django
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