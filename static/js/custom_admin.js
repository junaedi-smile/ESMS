// static/js/custom_admin.js
//
// Tanda perbaikan di file ini: cari "PERBAIKAN JS"

document.addEventListener("DOMContentLoaded", function () {

    var currentPath = window.location.pathname;

    // ── Router: load JS sesuai halaman ───────────────────────
    if (currentPath.includes("/asset/assetequipmentdisposed/")) {
        loadScript("/static/js/forms/capex_lampiran.js");
    }

    // Tambah form lain di sini nanti:
    // if (currentPath.includes("/asset/anothemodel/")) {
    //     loadScript("/static/js/forms/another_form.js");
    // }

    // ── Helper: dynamic load JS file ─────────────────────────
    function loadScript(src) {
        var script    = document.createElement("script");
        script.src    = src;
        script.async  = false;
        document.head.appendChild(script);
    }


    // ==========================================================
    // KONFIGURASI MENU 3 TINGKAT
    // ----------------------------------------------------------
    // Key utama = teks main menu persis seperti tampil di sidebar.
    // items     = potongan URL model: "/<app>/<namamodel_huruf_kecil>/"
    //             Boleh berupa:
    //               "/form/xxx/"                         -> link asli saja
    //               { url, label, icon }                 -> link asli kalau ada,
    //                                                       kalau belum terdaftar
    //                                                       tampil sebagai placeholder
    // Urutan items = urutan tampil.
    // Satu URL hanya masuk satu grup (grup yang diproses lebih dulu).
    // Grup yang tidak punya item cocok disembunyikan, kecuali alwaysShow: true.
    // ==========================================================

    // ✅ [PERBAIKAN JS 11] MENU_TREE dirapikan:
    //   - semua URL huruf kecil
    //   - formrepaircostanalisis / formfotokonditionunit tidak lagi tertulis
    //     di Equipment Standby dan Pengaktifan Equipment (dobel)
    //   - Equipment Disposed: placeholder yang sudah punya model asli
    //     digabung jadi satu entri (url = model asli, label = nama dokumen)
    //   ⚠ CEK: pasangan dokumen dan model di Equipment Disposed adalah perkiraan.
    const MENU_TREE = {

        "REPORT": [
            {
                title: "Report Summary Final",
                alwaysShow: true,
                items: [
                    { url: "/form/reportmonthly/",    label: "Report Monthly Final Status Eqp" },
                    { url: "/form/reportyearly/", label: "Report Year Final Status Eqp" },
                ],
            },

            {
                title: "Monitoring Approval Dokumen Disposed",
                items: [                   
                    { url: "/form/spb/",                 label: "Form Surat Pengiriman Barang (SPB)" },
                    { url: "/form/ami/",                 label: "Form Asset Moving Instructions (AMI)" },
                ],
            },

            {
                title: "Other",
                items: [                   
                    { url: "/form/ChecksheetPI/",                   label: "Cheecksheet PI" },
                    { url: "/form/FormPengajuanEquipmentDisposed/", label: "PDE" },
                    { url: "/form/FormRepairCostAnalisis/",         label: "RCA" },
                ],
            },
            
        ],

        "ACTIVITY": [
            {
                title: "Equipment Register",
                alwaysShow: true,
                items: [
                    { url: "/report/newequipmentsis/",    label: "Form Permintaan CN New Equipment SIS" },
                    { url: "/report/newequipmentnonsis/", label: "Form Permintaan CN New Equipment NON SIS" },
                ],
            },

            {
                title: "Equipment Movement",
                items: [                   
                    { url: "/report/spb/",                 label: "Form Surat Pengiriman Barang (SPB)" },
                    { url: "/report/ami/",                 label: "Form Asset Moving Instructions (AMI)" },
                    { url: "/report/SA/",                  label: "Form Spesial Approval" },
                ],
            },

            {
                title: "Equipment Standby",
                items: [
                    { url: "/report/eqpstandbprodnonprod/",  label: "Form Pengajuan Equipment Standby" },                    
                ],
            },

            {
                title: "Equipment Activation",
                items: [
                    { url: "/report/aktivasieqpstbpermanen/",  label: "Form BA Aktivasi Equipment Standby Permanen" },
                    { url: "/report/aktivasieqpstbsementara/", label: "Form BA Aktivasi Equipment Standby Sementara" },
                    { url: "/report/aktivasieqpdisposed/",     label: "Form BA Aktivasi Equipment Disposed" },
                ],
            },

            {
                title: "Equipment Disposed",
                items: [
                    { url: "/asset/AssetEquipmentPrepareDisposed/",    label: "Form Checksheet Inspection Equipment" },
                    { url: "/report/formrepaircostanalisis/",          label: "Form RCA" },
                    { url: "/report/kondisiatth/",                     label: "Form Kondisi Attachment Equipment" },
                    { url: "/report/formfotokonditionunit/",           label: "Form Foto 4 Sisi Equipment" },
                    { url: "/report/updatehmlt/",                      label: "Form BA pembaruan HM dan Lifetime Komponen" },
                    { url: "/report/formlampirancapex/",               label: "Form Lampiran PDE" },
                    { url: "/report/formpengajuanequipmentdisposed/",  label: "Form PDE" },
                    { url: "/report/summarypde/",                      label: "Form Summary PDE" },
                    "/form/formpengajuandisposedsite/",
                    
                ],
            },

            {
                title: "Equipment Conversion",
                alwaysShow: true,
                items: [
                    { url: "/report/alihfungsi/",           label: "Form Alih Fungsi Equipment" },
                    { url: "/report/persetujuanalihfungsi/",label: "Form Persetujuan Alih Fungsi Equipment (Disposed)" },
                ],
            },

            {
                title: "Other",
                alwaysShow: true,
                items: [                  
                    { url: "/asset/AssetEquipment/",                   label: "AssetEqp" },
                    { url: "/asset/AssetMonthlyStatus/",               label: "AssetEqp" },
                    { url: "/asset/AssetEquipmentDisposed/",           label: "AssetEqp" },
                    { url: "/asset/AssetEquipmentPrepareDisposed/",    label: "AssetEqp" },
                    { url: "/asset/AssetMasterMonthlyStatus/",         label: "AssetEqp" },
                    { url: "/asset/AssetFinalMonthlyStatus/",          label: "AssetEqp" },
                    { url: "/asset/AssetEquipmentStandby/",            label: "AssetEqp" },
                    { url: "/asset/AssetEquipmentBreakdown/",          label: "AssetEqp" },
                    { url: "/asset/AssetEquipmentOperate/",            label: "AssetEqp" },
                ],
            },
        ],

    };


    // ==========================================================
    // PENGGABUNGAN MAIN MENU (ISI DIPINDAH, TANPA FOLDER)
    // ----------------------------------------------------------
    // Format: "main menu tujuan": ["main menu yang isinya dipindahkan", ...]
    // Teks dicocokkan persis dengan teks header di sidebar,
    // tidak membedakan huruf besar dan kecil.
    // Main menu asal otomatis disembunyikan setelah kosong (lihat JS 6).
    // ==========================================================

    // ✅ [PERBAIKAN JS 12] Gabungkan main menu
    const MERGE_MENUS = {
        "ACCOUNTS": ["Authentication and Authorization"],
    };


    // ==========================================================
    // ✅ [PERBAIKAN JS 13] STATUS BUKA-TUTUP MENU DIINGAT ANTAR HALAMAN
    // ----------------------------------------------------------
    // Django admin memuat ulang SELURUH halaman setiap link diklik, termasuk
    // sidebar, sehingga JS ini berjalan lagi dari awal dan semua menu kembali
    // tertutup (aturan JS 9). Supaya sidebar terasa "tetap", status buka-tutup
    // disimpan di sessionStorage (per tab, hilang saat tab ditutup) lalu
    // dipulihkan di halaman berikutnya.
    //
    // RESET_ON_RELOAD  true  : tekan F5 / Ctrl+F5 -> semua menu tertutup lagi
    //                  false : F5 tetap mempertahankan menu yang terbuka
    // OPEN_ACTIVE_PATH true  : menu yang berisi halaman yang sedang dibuka
    //                          otomatis terbuka sampai ke item (child menu)-nya
    //                  false : hanya menu yang pernah Anda buka dengan klik
    // ==========================================================
    const STATE_KEY        = 'prima_sidebar_state_v1';
    const RESET_ON_RELOAD  = true;
    const OPEN_ACTIVE_PATH = true;

    function isReload() {
        try {
            const nav = performance.getEntriesByType('navigation')[0];
            if (nav) return nav.type === 'reload';
            return !!(performance.navigation && performance.navigation.type === 1);
        } catch (e) {
            return false;
        }
    }

    // false kalau halaman ini hasil F5 dan RESET_ON_RELOAD aktif
    const keepState = !(RESET_ON_RELOAD && isReload());

    let openState = {};
    if (keepState) {
        try {
            openState = JSON.parse(sessionStorage.getItem(STATE_KEY) || '{}') || {};
        } catch (e) {
            openState = {};
        }
    }

    function saveState() {
        try { sessionStorage.setItem(STATE_KEY, JSON.stringify(openState)); } catch (e) {}
    }

    function setOpen(key, open) {
        if (open) openState[key] = 1; else delete openState[key];
        saveState();
    }

    if (!keepState) saveState();   // simpan status kosong setelah reset

    function mainKey(header) {
        return 'main|' + header.textContent.trim().toLowerCase();
    }

    // Apakah link ini menuju halaman yang sedang dibuka?
    // Link "#" (tombol folder) dan placeholder tidak dihitung.
    function linkIsActive(a) {
        const href = a.getAttribute('href') || '';
        if (!href || href.charAt(0) === '#' || href.indexOf('javascript') === 0) return false;
        const p   = new URL(a.href, window.location.origin).pathname.toLowerCase();
        const cur = window.location.pathname.toLowerCase();
        return p.length > 1 && cur.startsWith(p);
    }

    function containsActiveLink(container) {
        return Array.from(container.querySelectorAll('a')).some(linkIsActive);
    }


    // ==========================================================
    // FUNGSI PEMBANGUN SUB MENU
    // ==========================================================

    // ✅ [PERBAIKAN JS 2] pathOf dipisah jadi fungsi sendiri supaya
    // bisa dipakai oleh pencarian lintas app.
    function pathOf(li) {
        const a = li.querySelector('a');
        return a ? new URL(a.href, window.location.origin).pathname : '';
    }

    // ✅ [PERBAIKAN JS 1] Cari item di SELURUH sidebar, bukan hanya di wrapper
    // main menu yang sedang diproses.
    // ✅ [PERBAIKAN JS 10] Pencocokan tidak lagi sensitif huruf besar/kecil.
    function findSidebarItem(key) {
        const k = key.toLowerCase();
        const all = document.querySelectorAll('.sidebar .nav-sidebar li');
        return Array.from(all).find(function (li) {
            return !li.classList.contains('nav-header')
                && !li.classList.contains('submenu-group')
                && !li.closest('.submenu-list')
                && pathOf(li).toLowerCase().endsWith(k);
        });
    }

    // ✅ [PERBAIKAN JS 7] Item placeholder untuk model yang belum terdaftar di admin
    function createPlaceholderItem(label, icon) {
        const li = document.createElement('li');
        li.className = 'nav-item placeholder-item';

        const a = document.createElement('a');
        a.href = '#';
        a.className = 'nav-link';
        a.title = 'Belum tersedia';
        a.innerHTML = '<i class="nav-icon ' + (icon || 'far fa-circle') + '"></i><p></p>';
        a.querySelector('p').textContent = label;
        a.addEventListener('click', function (e) { e.preventDefault(); });

        li.appendChild(a);
        return li;
    }

    function buildSubGroups(header, wrapper) {
        const headerText = header.textContent.trim();
        const groups = MENU_TREE[headerText];
        if (!groups) return;

        const fragment = document.createDocumentFragment();

        groups.forEach(function (group) {

            // ✅ [PERBAIKAN JS 1] pakai findSidebarItem, plus cegah item ganda
            const members = [];
            group.items.forEach(function (item) {
                const key   = (typeof item === 'string') ? item : item.url;
                const label = (typeof item === 'string') ? null : item.label;
                const icon  = (typeof item === 'string') ? null : item.icon;

                const li = key ? findSidebarItem(key) : null;
                if (li) {
                    if (members.indexOf(li) === -1) members.push(li);
                } else if (label) {
                    members.push(createPlaceholderItem(label, icon));   // belum terdaftar, tampilkan placeholder
                }
            });
            if (!members.length && !group.alwaysShow) return;   // sub menu kosong tidak ditampilkan

            const groupLi = document.createElement('li');
            groupLi.className = 'nav-item submenu-group';

            const toggle = document.createElement('a');
            toggle.href = '#';
            toggle.className = 'nav-link submenu-toggle';
            toggle.innerHTML =
                '<i class="nav-icon ' + (group.icon || 'fas fa-folder') + '"></i>' +
                '<p>' + group.title + '</p>' +
                '<i class="fas fa-angle-down submenu-arrow"></i>';

            const list = document.createElement('ul');
            list.className = 'nav flex-column submenu-list';
            members.forEach(function (li) { list.appendChild(li); });

            // ✅ [PERBAIKAN JS 13] Sub menu terbuka kalau:
            //   - sebelumnya dibuka lewat klik (tersimpan), atau
            //   - berisi halaman yang sedang dibuka (OPEN_ACTIVE_PATH).
            // Selain itu tertutup. (Pengganti JS 9 untuk sub menu.)
            const subKey = 'sub|' + headerText.toLowerCase() + '|' + group.title.toLowerCase();
            const shouldOpen = keepState && !!(openState[subKey] || (OPEN_ACTIVE_PATH && containsActiveLink(list)));
            if (!shouldOpen) {
                list.style.display = 'none';
                toggle.classList.add('collapsed');
            }

            toggle.addEventListener('click', function (e) {
                e.preventDefault();
                e.stopPropagation();   // cegah handler treeview bawaan AdminLTE
                const hidden = list.style.display === 'none';
                // ✅ [PERBAIKAN JS 3] '' (bukan 'block') supaya kembali ke display
                // asli dari CSS (.nav = flex)
                list.style.display = hidden ? '' : 'none';
                toggle.classList.toggle('collapsed', !hidden);
                setOpen(subKey, hidden);   // ✅ [PERBAIKAN JS 13] simpan status
            });

            groupLi.appendChild(toggle);
            groupLi.appendChild(list);
            fragment.appendChild(groupLi);
        });

        wrapper.insertBefore(fragment, wrapper.firstChild);
    }

    // ✅ [PERBAIKAN JS 12] Cari pasangan header + wrapper berdasarkan teks header
    function findHeaderPair(text) {
        const h = Array.from(document.querySelectorAll('.sidebar .nav-sidebar .nav-header'))
            .find(function (x) {
                return x.textContent.trim().toLowerCase() === text.toLowerCase();
            });
        if (!h) return null;
        const w = h.nextElementSibling;
        return (w && w.classList.contains('menu-collapse-wrapper'))
            ? { header: h, wrapper: w }
            : null;
    }


    // ==========================================================
    // JAVASCRIPT UNTUK FUNGSI COLLAPSE/EXPAND SIDEBAR
    // ==========================================================
    const navHeaders = document.querySelectorAll('.sidebar .nav-sidebar .nav-header');

    navHeaders.forEach(header => {
        let nextElement = header.nextElementSibling;
        let subMenuContainer = document.createElement('div');
        subMenuContainer.className = 'menu-collapse-wrapper';

        // Membungkus elemen-elemen submenu di bawah header terkait
        while (nextElement && !nextElement.classList.contains('nav-header')) {
            let toMove = nextElement;
            nextElement = nextElement.nextElementSibling;
            subMenuContainer.appendChild(toMove);
        }

        header.parentNode.insertBefore(subMenuContainer, nextElement);
        buildSubGroups(header, subMenuContainer);

        // Awalnya semua main menu tertutup. Yang perlu terbuka dipulihkan
        // di langkah "PERBAIKAN JS 13" di bawah (setelah penggabungan menu).
        subMenuContainer.style.display = 'none';
        header.classList.add('collapsed');     // panah ikut menghadap ke kanan

        // Event listener saat header menu utama diklik
        header.addEventListener('click', function() {
            this.classList.toggle('collapsed');

            // Efek buka-tutup (Toggle display)
            // ✅ [PERBAIKAN JS 3] '' (bukan "block"), sama seperti di atas
            const wasHidden = subMenuContainer.style.display === "none";
            subMenuContainer.style.display = wasHidden ? "" : "none";
            setOpen(mainKey(header), wasHidden);   // ✅ [PERBAIKAN JS 13] simpan status
        });
    });

    // ✅ [PERBAIKAN JS 12] Pindahkan isi main menu asal ke main menu tujuan.
    // Harus dijalankan SETELAH semua header selesai dibungkus (blok di atas)
    // dan SEBELUM pengecekan main menu kosong (JS 6 di bawah).
    Object.keys(MERGE_MENUS).forEach(function (targetText) {
        const target = findHeaderPair(targetText);
        if (!target) return;

        MERGE_MENUS[targetText].forEach(function (sourceText) {
            const src = findHeaderPair(sourceText);
            if (!src || src.wrapper === target.wrapper) return;

            Array.from(src.wrapper.children).forEach(function (li) {
                target.wrapper.appendChild(li);
            });
        });
    });

    // ✅ [PERBAIKAN JS 13] Pulihkan main menu yang harus terbuka.
    // Dijalankan SETELAH penggabungan menu (JS 12), supaya item yang sudah
    // dipindah ikut dihitung saat mencari halaman aktif.
    document.querySelectorAll('.menu-collapse-wrapper').forEach(function (w) {
        const h = w.previousElementSibling;
        if (!h || !h.classList.contains('nav-header')) return;

        const shouldOpen = keepState &&
            !!(openState[mainKey(h)] || (OPEN_ACTIVE_PATH && containsActiveLink(w)));
        if (shouldOpen) {
            w.style.display = '';
            h.classList.remove('collapsed');
        }
    });

    // ✅ [PERBAIKAN JS 6] Sembunyikan main menu yang isinya sudah habis dipindah
    // ke grup lain. Dijalankan setelah semua header selesai diproses
    // supaya tidak tergantung urutan menu.
    document.querySelectorAll('.menu-collapse-wrapper').forEach(function (w) {
        if (w.children.length === 0) {
            w.style.display = 'none';
            const h = w.previousElementSibling;
            if (h && h.classList.contains('nav-header')) h.style.display = 'none';
        }
    });

});
