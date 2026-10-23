// static/js/forms/capex_lampiran.js
(function () {

    var AJAX_LOOKUP_URL  = "/form/ajax/asset-lookup/";
    var CAPEX_SUBMIT_URL = "/form/lampiran-capex/create-ajax/";
    var CAPEX_FORM_URL   = "/admin/asset/get-capex-form/";

    // ── Expose fungsi ke global scope ────────────────────────
    window.openCapexModal = function (cnSap) {
        if (!cnSap) {
            alert("Gagal membuka form: CN SAP tidak ditemukan.");
            return;
        }

        var existing = document.getElementById("modalCapexOverlay");
        if (existing) existing.remove();

        fetch(CAPEX_FORM_URL + "?cn_sap=" + encodeURIComponent(cnSap))
            .then(function (r) {
                if (!r.ok) throw new Error("Gagal memuat form");
                return r.text();
            })
            .then(function (html) {
                var wrapper = document.createElement("div");
                wrapper.innerHTML = html;
                document.body.appendChild(wrapper);

                var overlay = document.getElementById("modalCapexOverlay");
                if (overlay) {
                    overlay.style.display = "block";
                    document.body.style.overflow = "hidden";
                }

                fetchAssetData(cnSap);
                registerModalEvents(cnSap);
            })
            .catch(function (err) {
                console.error(err);
                alert("Error: Gagal memuat form.");
            });
    };

    window.closeCapexModal = function () {
        var overlay = document.getElementById("modalCapexOverlay");
        if (overlay) overlay.remove();
        document.body.style.overflow = "";
    };

    // ── Fetch data asset untuk auto-fill ─────────────────────
    function fetchAssetData(cnSap) {
        fetch(AJAX_LOOKUP_URL + "?cn_sap=" + encodeURIComponent(cnSap))
            .then(function (r) { return r.json(); })
            .then(function (result) {
                var loading = document.getElementById("modal-loading");
                if (loading) loading.style.display = "none";

                if (result.found) {                         // ── if buka ①
                    var d = result.data;

                    // Dari AssetEquipment
                    setVal("modal-CN_SAP",         d.CN_SAP);
                    setVal("modal-GROUP",           d.GROUP);
                    setVal("modal-TYPE",            d.TYPE);
                    setVal("modal-EGI",             d.EGI);
                    setVal("modal-HM_SMR",          d.HM_SMR);
                    setVal("modal-SPO_EQUIPMENT",   d.SPO_EQUIPMENT);                    
                    setVal("modal-PERSENTASE_SPO",  d.PERSENTASE_SPO);

                    // Dari AR01
                    setVal("modal-NILAI_AKUISISI",  d.NILAI_AKUISISI);
                    setVal("modal-NBV",             d.NBV);

                    // ─── MODIFIKASI PENEMPATAN LOGIKA TOMBOL PDF DI SINI ───
                    var btnPdf = document.getElementById("btnCetakCapexPDF");
                    if (btnPdf) {
                        // Periksa apakah data unit ini sudah memiliki record Capex ID dari backend
                        if (d.capex_id) {
                            // Merakit URL PDF sesuai routing custom get_urls() di AssetEquipmentDisposedAdmin
                            var pdfUrl = "/admin/asset/assetequipmentdisposed/lampiran-capex/" + d.capex_id + "/pdf/";
                            btnPdf.href = pdfUrl;
                            btnPdf.style.display = "inline-block"; // Tampilkan tombol cetak
                        } else {
                            // Jika data pengajuan baru (baru klik Create Form), sembunyikan tombol PDF
                            btnPdf.style.display = "none";
                        }
                    }
                    // ────────────────────────────────────────────────────────

                    // Preview grid
                    var previewItems = {
                        "CN SAP":         d.CN_SAP,
                        "No Asset":       d.No_Asset,
                        "Class":          d.GROUP,
                        "Type":           d.TYPE,
                        "EGI":            d.EGI,
                        "Hour Meter":     d.HM_SMR,
                        "Location":       d.LOCATION,
                        "Nilai Akuisisi": d.NILAI_AKUISISI
                            ? "$ " + formatNumber(d.NILAI_AKUISISI)
                            : "-",
                        "NBV": d.NBV
                            ? "$ " + formatNumber(d.NBV)
                            : "-",
                    };

                    var html = "";
                    for (var k in previewItems) {
                        if (previewItems[k] && previewItems[k] !== "-") {
                            html +=
                                "<div style='background:#fff;" +
                                "border:1px solid #c8e6c9;" +
                                "border-radius:6px;padding:6px 10px;'>" +
                                "<div style='font-size:10px;color:#888;" +
                                "font-weight:600;'>" + k + "</div>" +
                                "<div style='font-size:12px;color:#333;" +
                                "font-weight:500;margin-top:1px;'>" +
                                previewItems[k] + "</div></div>";
                        }
                    }

                    var grid = document.getElementById("modal-preview-grid");
                    if (grid) grid.innerHTML = html;

                    var info = document.getElementById("modal-unit-info");
                    if (info) info.style.display = "block";

                    var label = document.getElementById("modal-cn-sap-label");
                    if (label) label.textContent = "CN SAP: " + cnSap;

                    // Info sumber data di console
                    if (d._ar01_rows_count > 0) {   // ── if buka ②
                        console.log(
                            "AR01: " + d._ar01_rows_count +
                            " baris diagregasi untuk CN SAP " + cnSap
                        );
                    } else {                         // ── else ②
                        console.warn(
                            "AR01: tidak ada data untuk CN SAP " + cnSap
                        );
                    }                                // ── if tutup ②

                } else {                             // ── else ①
                    showModalError(
                        "Unit tidak ditemukan: " + (result.error || "")
                    );
                }                                    // ── if tutup ①
            })
            .catch(function (err) {
                var loading = document.getElementById("modal-loading");
                if (loading) loading.style.display = "none";
                showModalError("Gagal mengambil data unit.");
                console.error(err);
            });
    }

    // ── Helper format angka ───────────────────────────────────
    function formatNumber(val) {
        var num = parseFloat(val);
        if (isNaN(num)) return val;
        return num.toLocaleString("id-ID", {
            minimumFractionDigits: 2,
            maximumFractionDigits: 2
        });
    }

    // ── Register event listeners ──────────────────────────────
    function registerModalEvents(cnSap) {
        var closeBtn = document.getElementById("closeCapexModalBtn");
        if (closeBtn) {
            closeBtn.onclick = function () { closeCapexModal(); };
        }

        var overlay = document.getElementById("modalCapexOverlay");
        if (overlay) {
            overlay.addEventListener("click", function (e) {
                if (e.target === overlay) closeCapexModal();
            });
        }

        var submitBtn = document.getElementById("modal-btn-submit");
        if (submitBtn) {
            submitBtn.onclick = function () { submitCapexModal(cnSap); };
        }

        // ✅ Generate nomor dokumen otomatis
        var docAutoField = document.getElementById("modal-doc-number-auto");
        if (docAutoField && !docAutoField.value) {
            docAutoField.value = generateDocNumber(cnSap);
        }
    }

    // ── Generate nomor dokumen otomatis ──────────────────
    function generateDocNumber(cnSap) {
        var now   = new Date();
        var year  = now.getFullYear();
        var month = String(now.getMonth() + 1).padStart(2, "0");
        var day   = String(now.getDate()).padStart(2, "0");
        var rand  = Math.floor(Math.random() * 900) + 100;
        return "CAPEX/" + cnSap + "/" + year + month + day + "/" + rand;
    }

    // ── Kumpulkan semua data form ─────────────────────────
    function collectFormData() {
        var form = document.getElementById("capex-modal-form");
        var data = {};
        var inputs = form.querySelectorAll("input, select, textarea");
        inputs.forEach(function(el) {
            if (el.name) data[el.name] = el.value || "";
        });
        return data;
    }

    // ── Print ─────────────────────────────────────────────
    window.printCapexForm = function() {
        var data    = collectFormData();
        data.output_type = "preview";

        // Buka tab baru untuk print
        submitToPreview(data, "/form/lampiran-capex/preview/");
    };

    // ── Download PDF ──────────────────────────────────────
    window.downloadCapexPDF = function() {
        var data    = collectFormData();
        data.output_type = "pdf";

        submitToPreview(data, "/form/lampiran-capex/preview/");
    };

    // ── Helper: submit form data ke URL preview ───────────
    function submitToPreview(data, url) {
        var form = document.createElement("form");
        form.method = "POST";
        form.action = url;
        form.target = "_blank";     // buka di tab baru

        // CSRF token
        var csrf = document.querySelector(
            "#capex-modal-form [name='csrfmiddlewaretoken']"
        );
        if (csrf) {
            var csrfInput   = document.createElement("input");
            csrfInput.type  = "hidden";
            csrfInput.name  = "csrfmiddlewaretoken";
            csrfInput.value = csrf.value;
            form.appendChild(csrfInput);
        }

        // Semua data
        for (var key in data) {
            if (key === "csrfmiddlewaretoken") continue;
            var input   = document.createElement("input");
            input.type  = "hidden";
            input.name  = key;
            input.value = data[key] || "";
            form.appendChild(input);
        }

        document.body.appendChild(form);
        form.submit();
        setTimeout(function() { form.remove(); }, 1000);
    }


    // ── Submit form ───────────────────────────────────────────
    function submitCapexModal(cnSap) {
        var form   = document.getElementById("capex-modal-form");
        var btn    = document.getElementById("modal-btn-submit");
        var errDiv = document.getElementById("modal-error");

        clearFieldErrors();

        if (!form.checkValidity()) {
            form.reportValidity();
            return;
        }

        btn.disabled    = true;
        btn.textContent = "⏳ Menyimpan...";
        if (errDiv) errDiv.style.display = "none";

        fetch(CAPEX_SUBMIT_URL, {
            method:  "POST",
            body:    new FormData(form),
            headers: { "X-Requested-With": "XMLHttpRequest" }
        })
        .then(function (r) { return r.json(); })
        .then(function (result) {
            if (result.success) {
                closeCapexModal();
                updateRowButton(
                    cnSap,
                    result.detail_url,
                    result.status_display
                );
                showNotif(
                    "✅ Form " + result.cn_sap + " berhasil dibuat.",
                    "#28a745"
                );
            } else {
                highlightFieldErrors(result.errors);
                btn.disabled    = false;
                btn.textContent = "💾 Simpan & Submit Approval";
            }
        })
        .catch(function (err) {
            showModalError("Gagal terhubung ke server.");
            btn.disabled    = false;
            btn.textContent = "💾 Simpan & Submit Approval";
            console.error(err);
        });
    }

    // ── Update tombol tabel setelah berhasil ──────────────────
    function updateRowButton(cnSap, detailUrl, statusDisplay) {
        document.querySelectorAll("button[type='button']").forEach(
            function (btn) {
                var oc = btn.getAttribute("onclick") || "";
                if (oc.indexOf("openCapexModal('" + cnSap + "')") !== -1) {
                    var wrapper = document.createElement("div");
                    wrapper.style.cssText =
                        "display:flex;flex-direction:column;" +
                        "align-items:center;gap:4px;";
                    wrapper.innerHTML =
                        "<a href='" + detailUrl + "' " +
                        "style='display:inline-block;padding:5px 12px;" +
                        "background:#f0f9f0;color:#28a745;" +
                        "border:1.5px solid #28a745;border-radius:6px;" +
                        "font-size:11px;font-weight:600;" +
                        "text-decoration:none;'>📄 Lihat Form</a>" +
                        "<span style='font-size:10px;color:#1883ff;" +
                        "font-weight:600;'>● " + statusDisplay + "</span>";
                    btn.parentNode.replaceChild(wrapper, btn);
                }
            }
        );
    }

    // ── Helpers ───────────────────────────────────────────────
    function setVal(id, val) {
        var el = document.getElementById(id);
        if (el) el.value = val || "";
    }

    function showModalError(msg) {
        var el = document.getElementById("modal-error");
        if (el) {
            el.innerHTML     = "❌ " + msg;
            el.style.display = "block";
        }
    }

    // ... (Fungsi helper highlightFieldErrors, clearFieldErrors, dan showNotif tetap sama di bawah) ...
    function highlightFieldErrors(errors) {
        var errDiv   = document.getElementById("modal-error");
        var messages = [];

        if (typeof errors === "string") {
            if (errDiv) {
                errDiv.innerHTML     = "❌ " + errors;
                errDiv.style.display = "block";
            }
            return;
        }

        for (var fieldName in errors) {
            var msgs    = errors[fieldName];
            var msgText = Array.isArray(msgs) ? msgs.join(", ") : msgs;
            var inputEl = document.querySelector(
                "#capex-modal-form [name='" + fieldName + "']"
            );

            if (inputEl) {
                inputEl.style.border          = "2px solid #dc3545";
                inputEl.style.backgroundColor = "#fff8f8";

                var existing = document.getElementById("err-" + fieldName);
                if (existing) existing.remove();

                var errMsg       = document.createElement("div");
                errMsg.id        = "err-" + fieldName;
                errMsg.innerHTML = "⚠️ " + msgText;
                errMsg.style.cssText =
                    "color:#dc3545;font-size:11px;" +
                    "margin-top:3px;font-weight:600;";
                inputEl.parentNode.appendChild(errMsg);

                if (messages.length === 0) {
                    inputEl.scrollIntoView({
                        behavior: "smooth",
                        block: "center"
                    });
                    inputEl.focus();
                }
                messages.push(
                    "<strong>" + fieldName + "</strong>: " + msgText
                );
            } else {
                messages.push(
                    "<strong>" + fieldName + "</strong>: " + msgText
                );
            }
        }

        if (messages.length > 0 && errDiv) {
            errDiv.innerHTML =
                "❌ Terdapat " + messages.length +
                " kesalahan:<br>" + messages.join("<br>");
            errDiv.style.display = "block";
        }
    }

    function clearFieldErrors() {
        var fields = document.querySelectorAll(
            "#capex-modal-form input, " +
            "#capex-modal-form select, " +
            "#capex-modal-form textarea"
        );
        fields.forEach(function (el) {
            el.style.border          = "";
            el.style.backgroundColor = "";
        });
        document.querySelectorAll("[id^='err-']").forEach(function (el) {
            el.remove();
        });
        var errDiv = document.getElementById("modal-error");
        if (errDiv) errDiv.style.display = "none";
    }

    function showNotif(msg, bg) {
        var existing = document.getElementById("capex-notif");
        if (existing) existing.remove();

        var el           = document.createElement("div");
        el.id            = "capex-notif";
        el.textContent   = msg;
        el.style.cssText =
            "position:fixed;top:20px;right:20px;" +
            "padding:14px 20px;border-radius:8px;" +
            "font-size:13px;font-weight:600;z-index:99999;" +
            "color:#fff;background:" + bg + ";" +
            "box-shadow:0 4px 12px rgba(0,0,0,0.2);" +
            "max-width:380px;";
        document.body.appendChild(el);
        setTimeout(function () { el.remove(); }, 4000);
    }

})();