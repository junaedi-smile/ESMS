# asset/utils_ocr.py
import os
import re
import cv2
import easyocr
import numpy as np
import pymupdf as fitz
import tempfile
from pdf2image import convert_from_path
from django.conf import settings
import warnings

# ✅ Suppress semua warning yang tidak perlu saat startup
warnings.filterwarnings("ignore", category=UserWarning)
warnings.filterwarnings("ignore", category=DeprecationWarning)
warnings.filterwarnings("ignore", category=FutureWarning)

# Suppress warning PyTorch quantize
os.environ['PYTHONWARNINGS'] = 'ignore'

import logging
logging.getLogger('easyocr').setLevel(logging.ERROR)

from difflib import SequenceMatcher

warnings.filterwarnings("ignore", category=UserWarning, module="torch.utils.data.dataloader")

# ✅ Inisialisasi sekali di level modul agar tidak reload tiap request
reader = easyocr.Reader(['id', 'en'], gpu=False, verbose=False)


# ===========================================================================
# ── 1. FUNGSI PEMBANTU DETEKSI FISIK TANDA TANGAN ──────────────────────────
# ===========================================================================

def analisis_goresan_tangan(roi_image):
    if roi_image is None or roi_image.size == 0:
        return False
        
    # 1. Konversi ke Grayscale
    gray = cv2.cvtColor(roi_image, cv2.COLOR_BGR2GRAY)
    
    # 2. Peningkatan Kontras menggunakan CLAHE (Dioptimalkan grid-nya)
    clahe = cv2.createCLAHE(clipLimit=3.0, tileGridSize=(4, 4))
    enhanced = clahe.apply(gray)
    
    # 3. Gunakan Adaptive Thresholding (Jauh lebih peka terhadap tinta tipis dibandingkan Otsu murni)
    thresh = cv2.adaptiveThreshold(
        enhanced, 255, 
        cv2.ADAPTIVE_THRESH_GAUSSIAN_C, 
        cv2.THRESH_BINARY_INV, 
        11, 2
    )
    
    # 4. Melunakkan Morphological Kernel (Menggunakan ukuran 2x2 agar coretan tipis/halus tidak tergerus hilang)
    kernel = np.ones((2,2), np.uint8)
    clean_thresh = cv2.morphologyEx(thresh, cv2.MORPH_OPEN, kernel)
    
    # 5. Deteksi Kontur Area Goresan Tangan
    contours, _ = cv2.findContours(clean_thresh, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
    
    total_contour_area = 0
    valid_contours_count = 0
    
    for contour in contours:
        area = cv2.contourArea(contour)
        # 🌟 Menurunkan threshold luas kontur minimal dari 20 ke 8 agar goresan pulpen halus tertangkap
        if 8 < area < 10000: 
            total_contour_area += area
            valid_contours_count += 1
            
    # Tuning logika keberhasilan yang ramah terhadap tanda tangan minimalis
    # Menurunkan batas total area kontur dari 150 menjadi 65 piksel
    if valid_contours_count >= 2 or total_contour_area > 65:
        return True
    
    return False


def verifikasi_tanda_tangan_dinamis(image_path, reader_results, anchor_text):
    """
    Mencari letak koordinat anchor_text (misal: "Approved by,"),
    menemukan baris nama terdekat di bawahnya secara dinamis, 
    lalu meng-crop area di antara keduanya untuk dideteksi tanda tangannya.
    """
    img = cv2.imread(image_path)
    if img is None:
        return False, "Gagal memproses gambar untuk deteksi tanda tangan."

    h, w, _ = img.shape
    anchor_text_lc = anchor_text.lower().strip()
    
    anchor_bbox = None
    anchor_y_bottom = None
    
    for bbox, text, prob in reader_results:
        clean_text = text.lower().strip()
        if anchor_text_lc in clean_text:
            anchor_bbox = bbox
            anchor_y_bottom = int(bbox[2][1]) 
            break
            
    if anchor_y_bottom is None:
        return False, f"Teks jangkar '{anchor_text}' tidak ditemukan pada dokumen."

    target_name_y_top = None
    target_name_text = ""
    min_distance_y = 999999
    
    anchor_x_left = int(anchor_bbox[0][0])
    anchor_x_right = int(anchor_bbox[1][0])
    
    for bbox, text, prob in reader_results:
        text_y_top = int(bbox[0][1])
        text_x_left = int(bbox[0][0])
        text_x_right = int(bbox[1][0])
        
        if text_y_top > anchor_y_bottom:
            if not (text_x_right < anchor_x_left - 100 or text_x_left > anchor_x_right + 100):
                distance_y = text_y_top - anchor_y_bottom
                if distance_y < min_distance_y and distance_y > 30:
                    min_distance_y = distance_y
                    target_name_y_top = text_y_top
                    target_name_text = text

    if target_name_y_top is None:
        return False, f"Nama penandatangan di bawah '{anchor_text}' tidak terdeteksi."

    x_start = max(min(anchor_x_left, int(anchor_bbox[0][0])) - 30, 0)
    x_end = min(max(anchor_x_right, int(anchor_bbox[1][0])) + 150, w)
    
    roi_signature = img[anchor_y_bottom:target_name_y_top, x_start:x_end]
    signature_exists = analisis_goresan_tangan(roi_signature)
    
    if signature_exists:
        return True, f"Tanda tangan '{anchor_text}' terdeteksi (Atas nama: {target_name_text})"
    else:
        return False, f"Tanda tangan basah di atas nama '{target_name_text}' kosong atau tidak terdeteksi."
    

def verifikasi_tanda_tangan_disposed(image_path, reader_results, anchor_jabatan):
    """
    Khusus Form Disposed: Mencari teks jabatan secara fleksibel menggunakan Fuzzy Matching,
    untuk mengatasi teks jabatan yang terpotong menjadi beberapa baris oleh OCR.
    Lalu mengambil area di ATASNYA untuk analisis tanda tangan.
    """
    img = cv2.imread(image_path)
    if img is None:
        return False, "Gagal memproses gambar untuk deteksi tanda tangan."

    h, w, _ = img.shape
    
    # Normalisasi target pencarian (lower, hilangkan spasi & non-alfanumerik)
    target_norm = re.sub(r"[^a-z0-9]", "", anchor_jabatan.lower())
    
    best_bbox = None
    best_y_top = None
    best_ratio = 0.0
    matched_text = ""

    # 1. Pencarian Fleksibel Menggunakan Substring & Fuzzy Matching
    for bbox, text, prob in reader_results:
        text_norm = re.sub(r"[^a-z0-9]", "", text.lower())
        if not text_norm:
            continue
            
        # Skenario A: Kecocokan Langsung Substring (Sangat Akurat)
        if target_norm in text_norm or text_norm in target_norm:
            best_bbox = bbox
            best_y_top = int(bbox[0][1])
            matched_text = text
            break
            
        # Skenario B: Fuzzy Matching (Mengatasi OCR pecah baris seperti "Dept. Head" & "Engineering")
        ratio = SequenceMatcher(None, target_norm, text_norm).ratio()
        
        if ("engineering" in target_norm and "engineering" in text_norm) or \
           ("operation" in target_norm and "operation" in text_norm) or \
           ("section" in target_norm and "section" in text_norm):
            ratio = 0.95 # Paksa ratio tinggi jika kata kunci utama cocok
            
        if ratio > best_ratio and ratio > 0.6:  # Threshold kecocokan minimal 60%
            best_ratio = ratio
            best_bbox = bbox
            best_y_top = int(bbox[0][1])
            matched_text = text

    # Jika pencarian fuzzy dasar masih gagal, lakukan scanning gabungan teks berdekatan (Concatenation scan)
    if best_y_top is None:
        combined_text = " ".join([text.lower() for _, text, _ in reader_results])
        combined_text_norm = re.sub(r"[^a-z0-9]", "", combined_text)
        
        if target_norm in combined_text_norm:
            keyword_map = {
                "headengineering": "engineering",
                "chiefoperation": "operation",
                "sectionhead": "section",
                "headlogistic": "logistic",
                "headplantmining": "plant"
            }
            sub_keyword = keyword_map.get(target_norm, target_norm[:5])
            
            for bbox, text, prob in reader_results:
                if sub_keyword in text.lower():
                    best_bbox = bbox
                    best_y_top = int(bbox[0][1])
                    matched_text = text
                    break

    if best_y_top is None:
        return False, f"Jabatan '{anchor_jabatan}' tidak ditemukan pada dokumen."

    # 2. Tentukan ROI di atas teks jabatan (setinggi 140 piksel ke atas)
    y_start = max(best_y_top - 140, 0)
    y_end = max(best_y_top - 5, 0) 
    
    x_start = max(int(best_bbox[0][0]) - 40, 0)
    x_end = min(int(best_bbox[1][0]) + 60, w)
    
    # 3. Crop area tanda tangan
    roi_signature = img[y_start:y_end, x_start:x_end]
    
    # 4. Analisis goresan menggunakan fungsi OpenCV
    signature_exists = analisis_goresan_tangan(roi_signature)
    
    if signature_exists:
        return True, f"Tanda tangan untuk '{anchor_jabatan}' terdeteksi (Terbaca sebagai: {matched_text})."
    else:
        return False, f"Tanda tangan basah di atas jabatan '{anchor_jabatan}' kosong atau tidak terdeteksi."


def preprocess_image_for_ocr(image_path):
    """
    Dioptimalkan untuk Akurasi OCR Teks Tinggi:
    Menggunakan Grayscale + CLAHE ringan tanpa denoising berat, 
    menjaga keutuhan font teks dokumen agar tidak pecah/blur saat dibaca EasyOCR.
    """
    img = cv2.imread(image_path)
    if img is None:
        return image_path

    # 1. Cukup konversi ke Grayscale
    gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
    
    # 2. Angkat kontras tulisan pudar dengan CLAHE ringan
    clahe = cv2.createCLAHE(clipLimit=2.0, tileGridSize=(8, 8))
    enhanced = clahe.apply(gray)

    base, ext = os.path.splitext(image_path)
    processed_path = f"{base}_processed{ext}"
    cv2.imwrite(processed_path, enhanced)
    return processed_path

# ===========================================================================
# ── 2. FUNGSI UTAMA EKSTRAKSI OCR ──────────────────────────────────────────
# ===========================================================================

def extract_text_from_file(file_path):
    """
    Ekstrak teks berkecepatan tinggi dengan Garbage Collection yang aman (Anti-Leak).
    """
    extracted_text = ""
    ext = os.path.splitext(file_path)[1].lower()

    temp_dir = os.path.join(settings.MEDIA_ROOT, 'temp_ocr')
    os.makedirs(temp_dir, exist_ok=True)
    image_paths = []

    # 1. Konversi PDF ke Gambar PNG
    if ext == '.pdf':
        pages = convert_from_path(file_path, dpi=200)
        for i, page in enumerate(pages):
            img_path = os.path.join(temp_dir, f"page_{i}.png")
            page.save(img_path, 'PNG')
            image_paths.append(img_path)
    elif ext in ['.png', '.jpg', '.jpeg']:
        image_paths.append(file_path)
    else:
        return "", [], file_path
    
    results_per_page = {}
    
    # 2. Blok Try-Finally Menjamin File Temp Selalu Terhapus Walau Terjadi Error/Crash
    try:
        for idx, img_p in enumerate(image_paths):
            try:
                # Gunakan pre-process ringan khusus teks
                clean_img = preprocess_image_for_ocr(img_p)
                raw_results = reader.readtext(clean_img, detail=1)
                
                results_per_page[idx] = raw_results
                extracted_text += "\n" + " ".join([text for _, text, _ in raw_results])            

                if os.path.exists(clean_img) and clean_img != img_p:
                    os.remove(clean_img)          
            except Exception as e:
                print(f"[OCR] Gagal memproses gambar pada halaman {idx}: {e}")

        idx_halaman_terakhir = len(image_paths) - 1
        target_image_for_signature = image_paths[idx_halaman_terakhir] if image_paths else file_path
        last_page_results = results_per_page.get(idx_halaman_terakhir, [])
        
        return extracted_text.upper(), last_page_results, target_image_for_signature

    finally:
        # 🌟 GARBAGE COLLECTION: Hapus seluruh halaman awal, sisakan halaman terakhir untuk tanda tangan
        idx_halaman_terakhir = len(image_paths) - 1
        for idx, img_p in enumerate(image_paths):
            if idx != idx_halaman_terakhir and os.path.exists(img_p) and img_p != file_path:
                try:
                    os.remove(img_p)
                except:
                    pass


# ===========================================================================
# ── 3. EKSTRAK NILAI USD TERTINGGI PADA RCA ────────────────────────────────
# ===========================================================================

def ekstrak_usd_tertinggi(text):
    if not text:
        return "-"

    text_upper = text.upper()
    kandidat_angka = []

    pola_total = re.findall(r'TOTAL\s*:?\s*([\d,]+\.?\d*)', text_upper)
    for match in pola_total:
        angka_clean = match.replace(',', '')
        try:
            kandidat_angka.append(float(angka_clean))
        except ValueError:
            continue

    pola_mata_uang = re.findall(r'(?:USD|\$)\s*:?\s*([\d,]+\.?\d*)', text_upper)
    for match in pola_mata_uang:
        angka_clean = match.replace(',', '')
        try:
            kandidat_angka.append(float(angka_clean))
        except ValueError:
            continue

    if not kandidat_angka:
        pola_umum = re.findall(r'\b\d{1,3}(?:,\d{3})+\b', text_upper)
        for match in pola_umum:
            angka_clean = match.replace(',', '')
            try:
                kandidat_angka.append(float(angka_clean))
            except ValueError:
                continue

    if kandidat_angka:
        nilai_tertinggi = max(kandidat_angka)
        angka_format = f"{nilai_tertinggi:,.0f}"
        return f"USD {angka_format}"
    
    return "-"


# ===========================================================================
# ── 4. FUNGSI VERIFIKASI DOKUMEN RCA ───────────────────────────────────────
# ===========================================================================

def verifikasi_dokumen_rca(file_path, cn_sap, egi, serial_number, expected_no="PLO/09/F-020", expected_nama="REPAIR COST ANALYSIS"):
    if not os.path.exists(file_path):
        return False, f"File tidak ditemukan di path: {file_path}", "-", "-", "-"

    signature_img_path = None
    try:
        text_result, results, signature_img_path = extract_text_from_file(file_path)
    except Exception as e:
        return False, f"Gagal membaca file: {str(e)}", "-", "-", "-"

    if not text_result.strip():
        # ✅ Perbaikan: Jika pembacaan gagal, pastikan temp halaman terakhir dihapus sebelum return
        if signature_img_path and file_path != signature_img_path and os.path.exists(signature_img_path):
            os.remove(signature_img_path)
        return False, "Teks tidak berhasil diekstrak dari dokumen. Pastikan kualitas scan cukup baik.", "-", "-", "-"

    is_valid       = True
    error_messages = []

    text_upper = text_result.upper()
    text_normalized = text_upper.replace("|", "/")

    def clean_text(val):
        return re.sub(r"[^A-Z0-9]", "", str(val).upper())

    def fuzzy_text(val):
        return (clean_text(val).replace("0", "O").replace("1", "I").replace("L", "I").replace("9", "O").replace("5", "S"))

    text_clean = clean_text(text_normalized)
    text_fuzzy = fuzzy_text(text_normalized)

    if "PLOIO9IF020" in text_clean or "PLO09F020" in text_fuzzy or "PLOIOSIF020" in text_clean:
        text_normalized += f" {expected_no.upper()}"
        text_clean = clean_text(text_normalized)
        text_fuzzy = fuzzy_text(text_normalized)

    usd_tertinggi = ekstrak_usd_tertinggi(text_result)

    no_dokumen = "-"
    no_dokumen_ditemukan = False 

    if expected_no.upper() in text_normalized or clean_text(expected_no) in text_clean or fuzzy_text(expected_no) in text_fuzzy:
        no_dokumen = expected_no
        no_dokumen_ditemukan = True
    else:
        match_no = re.search(r"PLO[/|]\d{2}[/|][A-Z]-\d{3}", text_upper)
        if match_no:
            no_dokumen = match_no.group(0).replace("|", "/")
            no_dokumen_ditemukan = True
        else:
            if "PLO" in text_clean:
                no_dokumen = f"{expected_no} (Terbaca Lemah)"
                no_dokumen_ditemukan = True

    if not no_dokumen_ditemukan:
        is_valid = False
        error_messages.append(f"Nomor Dokumen '{expected_no}' tidak ditemukan.")

    nama_dokumen = "-"
    nama_dokumen_ditemukan = False

    if clean_text(expected_nama) in text_clean or fuzzy_text(expected_nama) in text_fuzzy:
        nama_dokumen = expected_nama
        nama_dokumen_ditemukan = True
    else:
        kata_kunci   = ["REPAIR", "COST", "ANALYSIS"]
        kata_cocok   = sum(1 for k in kata_kunci if k in text_upper)
        if kata_cocok >= 2:
            nama_dokumen           = f"{expected_nama} (Partial Read)"
            nama_dokumen_ditemukan = True
        elif kata_cocok == 1:
            nama_dokumen           = f"{expected_nama} (Terbaca Lemah)"
            nama_dokumen_ditemukan = False

    if not nama_dokumen_ditemukan:
        is_valid = False
        error_messages.append(f"Nama Dokumen '{expected_nama}' tidak ditemukan.")

    # --- VALIDASI DATA UNIT ---
    cn_sap_valid = False
    if cn_sap:
        if (cn_sap.upper() in text_normalized or clean_text(cn_sap) in text_clean or fuzzy_text(cn_sap) in text_fuzzy):
            cn_sap_valid = True
        else:
            is_valid = False
            error_messages.append(f"CN SAP '{cn_sap}' tidak ditemukan.")

    egi_valid = False
    if egi:
        if (egi.upper() in text_normalized or clean_text(egi) in text_clean or fuzzy_text(egi) in text_fuzzy):
            egi_valid = True
        else:
            is_valid = False
            error_messages.append(f"EGI '{egi}' tidak ditemukan.")

    sn_valid = False
    if serial_number:
        if (serial_number.upper() in text_normalized or clean_text(serial_number) in text_clean or fuzzy_text(serial_number) in text_fuzzy):
            sn_valid = True
        else:
            is_valid = False
            error_messages.append(f"Serial Number '{serial_number}' tidak ditemukan.")

    # --- VALIDASI OTORISASI TANDA TANGAN ---
    status_signature = "Lengkap ✅ VALID"
    if is_valid:
        approved_valid, approved_msg = verifikasi_tanda_tangan_dinamis(signature_img_path, results, "Approved by")
        if not approved_valid:
            is_valid = False
            status_signature = "Tidak Lengkap ❌ TIDAK VALID"
            error_messages.append(approved_msg)

        prepared_valid, prepared_msg = verifikasi_tanda_tangan_dinamis(signature_img_path, results, "Prepared by")
        if not prepared_valid:
            is_valid = False
            status_signature = "Tidak Lengkap ❌ TIDAK VALID"
            error_messages.append(prepared_msg)
    else:
        status_signature = "Belum Diperiksa (Data Unit Invalid) ❌"

    # ✅ PERBAIKAN LOGIKA PEMBERSIHAN: Selalu pastikan temp file terakhir dihapus di akhir eksekusi
    if signature_img_path and file_path != signature_img_path and os.path.exists(signature_img_path):
        try:
            os.remove(signature_img_path)
        except Exception as e:
            print(f"[OCR] Gagal menghapus file signature temp: {e}")

    # 📊 PEMBUATAN STRUKTUR TEKS LAPORAN (CHECKLIST UX)
    report_details = (
        f"Nomor Dokumen : {no_dokumen} " + ("✅ VALID" if no_dokumen_ditemukan else "❌ TIDAK DITEMUKAN") + f"\n"
        f"Nama Dokumen  : {nama_dokumen} " + ("✅ VALID" if nama_dokumen_ditemukan else "❌ TIDAK DITEMUKAN") + f"\n"
        f"CN SAP         : {cn_sap if cn_sap else '-'} " + ("✅ VALID" if cn_sap_valid else "❌ TIDAK MATCH") + f"\n"
        f"EGI            : {egi if egi else '-'} " + ("✅ VALID" if egi_valid else "❌ TIDAK MATCH") + f"\n"
        f"SN             : {serial_number if serial_number else '-'} " + ("✅ VALID" if sn_valid else "❌ TIDAK MATCH") + f"\n"
        f"Otorisasi Form : {status_signature}"
    )

    report_details_html = report_details.replace("\n", "<br>")

    if is_valid:
        return True, f"Dokumen valid — Identitas Dokumen cocok dengan data sistem dan Tanda Tangan Lengkap.", no_dokumen, nama_dokumen, usd_tertinggi

    summary_err = " | ".join(error_messages)
    full_message = f"{summary_err}<br><br>{report_details_html}"
    return False, full_message, no_dokumen, nama_dokumen, usd_tertinggi


# ===========================================================================
# ── 5. FUNGSI VERIFIKASI FORM PENGAJUAN DISPOSED EQUIPMENT ──────────────────
# ===========================================================================

def verifikasi_dokumen_pengajuan_disposed(file_path, cn_sap, egi, serial_number, expected_no="PBA/14/F-003",
                                         expected_nama="FORM PENGAJUAN DISPOSE EQUIPMENT"):
    if not os.path.exists(file_path):
        return False, f"File tidak ditemukan: {file_path}", "-", "-", "-"

    signature_img_path = None
    try:
        text_result, results, signature_img_path = extract_text_from_file(file_path)
    except Exception as e:
        return False, f"Gagal membaca file: {str(e)}", "-", "-", "-"

    if not text_result.strip():
        # ✅ Perbaikan pembersihan temp
        if signature_img_path and file_path != signature_img_path and os.path.exists(signature_img_path):
            os.remove(signature_img_path)
        return False, "Teks tidak berhasil diekstrak dari dokumen.", "-", "-", "-"

    is_valid       = True
    error_messages = []

    text_upper      = text_result.upper()
    text_normalized = text_upper.replace("|", "/")

    def clean_text(val):
        return re.sub(r"[^A-Z0-9]", "", str(val).upper())

    def fuzzy_text(val):
        return (clean_text(val).replace("0", "O").replace("1", "I").replace("L", "I").replace("9", "O").replace("5", "S"))

    text_clean = clean_text(text_normalized)
    text_fuzzy = fuzzy_text(text_normalized)

    no_pengajuan = "-"
    match_no_peng = re.search(r'\d{3}/\w+/\w+/\w+/\w+/\d{4}', text_upper)
    if match_no_peng:
        no_pengajuan = match_no_peng.group(0)

    no_form           = "-"
    no_form_ditemukan = False

    if (expected_no.upper() in text_normalized or clean_text(expected_no) in text_clean or fuzzy_text(expected_no) in text_fuzzy):
        no_form           = expected_no
        no_form_ditemukan = True
    else:
        match_no = re.search(r'PBA[/|]\d{2}[/|]F-\d{3}', text_upper)
        if match_no:
            no_form           = match_no.group(0).replace("|", "/")
            no_form_ditemukan = True
        elif "PBA" in text_clean:
            no_form           = f"{expected_no} (Terbaca Lemah)"
            no_form_ditemukan = True

    if not no_form_ditemukan:
        is_valid = False
        error_messages.append(f"Nomor Form '{expected_no}' tidak ditemukan.")

    nama_form           = "-"
    nama_form_ditemukan = False

    if (clean_text(expected_nama) in text_clean or fuzzy_text(expected_nama) in text_fuzzy):
        nama_form           = expected_nama
        nama_form_ditemukan = True
    else:
        kata_kunci  = ["PENGAJUAN", "DISPOSE", "EQUIPMENT"]
        kata_cocok  = sum(1 for k in kata_kunci if k in text_upper)
        if kata_cocok >= 2:
            nama_form           = f"{expected_nama} (Partial Read)"
            nama_form_ditemukan = True
        elif kata_cocok == 1:
            nama_form           = f"{expected_nama} (Terbaca Lemah)"
            nama_form_ditemukan = False

    if not nama_form_ditemukan:
        is_valid = False
        error_messages.append(f"Nama Form '{expected_nama}' tidak ditemukan.")

    # --- VALIDASI DATA UNIT ---
    cn_sap_valid = False
    if cn_sap:
        if (cn_sap.upper() in text_normalized or clean_text(cn_sap) in text_clean or fuzzy_text(cn_sap) in text_fuzzy):
            cn_sap_valid = True
        else:
            is_valid = False
            error_messages.append(f"CN SAP '{cn_sap}' tidak ditemukan.")

    egi_valid = False
    if egi:
        if (egi.upper() in text_normalized or clean_text(egi) in text_clean or fuzzy_text(egi) in text_fuzzy):
            egi_valid = True
        else:
            is_valid = False
            error_messages.append(f"EGI '{egi}' tidak ditemukan.")

    sn_valid = False
    if serial_number:
        if (serial_number.upper() in text_normalized or clean_text(serial_number) in text_clean or fuzzy_text(serial_number) in text_fuzzy):
            sn_valid = True
        else:
            is_valid = False
            error_messages.append(f"Serial Number '{serial_number}' tidak ditemukan.")

    # --- VALIDASI OTORISASI TANDA TANGAN FORM DISPOSED ---
    status_signature = "Lengkap ✅ VALID"
    if is_valid:
        # Check 1: Chief Operation ADMO
        co_valid, co_msg = verifikasi_tanda_tangan_disposed(signature_img_path, results, "Chief Operation")
        if not co_valid:
            is_valid = False
            status_signature = "Tidak Lengkap ❌ TIDAK VALID"
            error_messages.append(co_msg)

        # Check 2: Dept. Head Engineering
        eng_valid, eng_msg = verifikasi_tanda_tangan_disposed(signature_img_path, results, "Head - Engineering")
        if not eng_valid:
            is_valid = False
            status_signature = "Tidak Lengkap ❌ TIDAK VALID"
            error_messages.append(eng_msg)

        # Check 3: Plant Section Head
        psh_valid, psh_msg = verifikasi_tanda_tangan_disposed(signature_img_path, results, "Section Head")
        if not psh_valid:
            is_valid = False
            status_signature = "Tidak Lengkap ❌ TIDAK VALID"
            error_messages.append(psh_msg)
    else:
        status_signature = "Belum Diperiksa (Data Unit Invalid) ❌"

    # ✅ PERBAIKAN LOGIKA PEMBERSIHAN: Selalu pastikan temp file terakhir dihapus di akhir eksekusi
    if signature_img_path and file_path != signature_img_path and os.path.exists(signature_img_path):
        try:
            os.remove(signature_img_path)
        except Exception as e:
            print(f"[OCR] Gagal menghapus file signature temp: {e}")

    # 📊 PEMBUATAN STRUKTUR TEKS LAPORAN DENGAN LINE BREAK HTML (<br>)
    report_details = (
        f"Nomor Form    : {no_form} " + ("✅ VALID" if no_form_ditemukan else "❌ TIDAK DITEMUKAN") + "<br>"
        f"Nama Form     : {nama_form} " + ("✅ VALID" if nama_form_ditemukan else "❌ TIDAK DITEMUKAN") + "<br>"
        f"CN SAP         : {cn_sap if cn_sap else '-'} " + ("✅ VALID" if cn_sap_valid else "❌ TIDAK MATCH") + "<br>"
        f"EGI            : {egi if egi else '-'} " + ("✅ VALID" if egi_valid else "❌ TIDAK MATCH") + "<br>"
        f"SN             : {serial_number if serial_number else '-'} " + ("✅ VALID" if sn_valid else "❌ TIDAK MATCH") + "<br>"
        f"Otorisasi Form : {status_signature}"
    )

    if is_valid:
        return True, f"Dokumen valid — Identitas Dokumen cocok dengan data sistem dan Tanda Tangan Lengkap.", no_form, nama_form, no_pengajuan

    summary_err = " | ".join(error_messages)
    full_message = f"{summary_err}<br><br>{report_details}"
    return False, full_message, no_form, nama_form, no_pengajuan


# ===========================================================================
# ── 6. FUNGSI VERIFIKASI FOTO 4 SISI EQUIPMENT DISPOSED ──────────────────
# ===========================================================================

def verifikasi_foto_empat_sisi(file_path, target_cn, target_sn, unit_model, extracted_text=None, **kwargs):
    """
    Fungsi untuk memvalidasi dokumen Foto 4 Sisi Unit.
    Wajib mendeteksi keberadaan objek gambar fisik secara spesifik di tiap area koordinat kotak (Depan, Belakang, Kanan, Kiri).
    """
    import re
    import os
    import pymupdf as fitz  # PyMuPDF
    import easyocr
    import numpy as np
    import cv2
    
    # 1. Definisi Koordinat Kotak (Bounding Box) pada Template A4 (595 x 842 pt)
    BOX_TEMPLATES = {
        "tampak_depan":    (30, 280, 290, 510),
        "tampak_belakang": (305, 280, 565, 510),
        "tampak_kanan":    (30, 525, 290, 755),
        "tampak_kiri":     (305, 525, 565, 755)
    }

    images_detected = {
        "tampak_depan": False,
        "tampak_belakang": False,
        "tampak_kanan": False,
        "tampak_kiri": False
    }

    ext = os.path.splitext(file_path)[1].lower()

    cn_found_in_any_image = False # Flag penanda nomor lambung ketemu di foto

    # Ambil digit terakhir dari CN SAP (misal WT090-0015 diambil "0015" atau "015")
    cn_digits = re.findall(r'\d+', target_cn)
    search_digits = cn_digits[-1] if cn_digits else None # Menghasilkan "0015"
    short_digits = str(int(search_digits)) if search_digits else None # Menghasilkan "15" atau "015" dikondisikan    
    
    # ── DETEKSI GAMBAR PER KORIDOR/KOTAK (KHUSUS PDF) ──
    if ext == '.pdf':
        try:
            # Inisialisasi EasyOCR reader jika belum ada
            reader = easyocr.Reader(['en'], gpu=False) # set True jika server ada GPU

            doc = fitz.open(file_path)
            page = doc[0] 
            
            # Dapatkan semua objek gambar di halaman pertama
            images_list = page.get_images(full=True)
            valid_large_images_count = 0  # Counter untuk menghitung jumlah total foto truk asli           

            for img_info in images_list:
                # Ambil nilai xref (ID referensi unik gambar di PDF)
                xref = img_info[0]
                
                try:
                    # Ambil metadata gambar untuk mengecek dimensi fisik pixel-nya
                    base_image = doc.extract_image(xref)
                    width = base_image.get("width", 0)
                    height = base_image.get("height", 0)
                    
                    # 🌟 Filter dimensi gambar (Abaikan logo kecil / garis ikon tabel)
                    if width < 150 or height < 150:
                        continue  # Lewati objek ini dan lanjut ke gambar berikutnya
                except Exception:
                    pass

                # Jika lolos filter dimensi besar, naikkan counter foto truk asli
                valid_large_images_count += 1

                # ── LAYER 2: VALIDASI KEBENARAN FOTO (EVALUASI NOMOR LAMBUNG DI BADAN UNIT) ──
                try:
                    image_bytes = base_image["image"]
                    nparr = np.frombuffer(image_bytes, np.uint8)
                    img_np = cv2.imdecode(nparr, cv2.IMREAD_COLOR)
                    
                    # Jalankan EasyOCR spesifik pada potongan gambar unit fisik ini
                    image_ocr_results = reader.readtext(img_np)
                    
                    for (_, text, conf) in image_ocr_results:
                        text_upper = text.upper()
                        clean_text = re.sub(r"[^0-9]", "", text)  # Ambil angka saja untuk pencocokan lambung
                        
                        # Jalankan verifikasi kecocokan nomor lambung
                        if search_digits and (search_digits in text_upper or search_digits in clean_text):
                            cn_found_in_any_image = True
                        elif short_digits and (short_digits in text_upper or short_digits in clean_text):
                            if len(clean_text) >= 2:  # Memastikan minimal ada 2 digit kecocokan nomor lambung unit
                                cn_found_in_any_image = True
                except Exception as img_ocr_err:
                    print(f"[OCR WARNING] Gagal membaca tulisan nomor lambung di dalam gambar unit: {img_ocr_err}")
                
                # ── LAYER 1: VALIDASI KOORDINAT TEMPLATE ──
                rects = page.get_image_rects(xref)
                
                # Lakukan pencocokan irisan area dengan template box 4 sisi
                for img_rect in rects:
                    for box_name, box_coords in BOX_TEMPLATES.items():
                        box_rect = fitz.Rect(box_coords)
                        intersection_area = box_rect.intersect(img_rect).get_area()
                        box_area = box_rect.get_area()
                        
                        # Toleransi irisan ke 25% (0.25) agar lebih aman dari "serempetan" garis
                        if intersection_area > 0 and (intersection_area / box_area) > 0.25:
                            images_detected[box_name] = True

            # 🌟 VALIDASI MUTLAK: Jika jumlah foto truk besar di dokumen tidak pas 4 buah, 
            # maka gagalkan salah satu sisi secara paksa (dalam kasus ini tampak_belakang)
            if valid_large_images_count != 4:
                print(f"[OCR VALIDATION] Jumlah gambar besar hanya {valid_large_images_count}, seharusnya 4.")
                for box_name in BOX_TEMPLATES.keys():
                    if not images_detected[box_name]:
                        images_detected[box_name] = False
                
                # Pengaman tambahan: jika kebetulan koordinat overlap membuat semua true, paksa false jika total gambar tidak 4
                if all(images_detected.values()):
                    images_detected["tampak_belakang"] = False

        except Exception as img_err:
            print(f"[OCR ERROR] Gagal mendeteksi gambar per koordinat: {img_err}")
            images_detected = {k: False for k in BOX_TEMPLATES.keys()}
    else:
        # Jika format non-PDF (PNG/JPG), bypass koordinat, asumsikan konten validasi diserahkan ke OCR teks utama
        images_detected = {k: True for k in BOX_TEMPLATES.keys()}
        cn_found_in_any_image = True


    # ── 2. PROSES OCR TEKS (SISI LABEL & IDENTITAS UNIT) ──
    temp_signature_path = None
    if extracted_text:
        text_result = extracted_text
    else:
        if not os.path.exists(file_path):
            return False, f"File tidak ditemukan di path: {file_path}", "-", "-", {
                "tampak_depan": False, "tampak_belakang": False, "tampak_kanan": False, "tampak_kiri": False,
                "cn_status": False, "sn_status": False, "model_status": False
            }
        try:
            from .utils_ocr import extract_text_from_file 
            text_result, _, temp_signature_path = extract_text_from_file(file_path)
        except Exception as e:
            try:
                text_result, _, temp_signature_path = extract_text_from_file(file_path)
            except Exception as inner_e:
                return False, f"Gagal membaca file foto 4 sisi: {str(inner_e)}", "-", "-", {
                    "tampak_depan": False, "tampak_belakang": False, "tampak_kanan": False, "tampak_kiri": False,
                    "cn_status": False, "sn_status": False, "model_status": False
                }

    if temp_signature_path and file_path != temp_signature_path and os.path.exists(temp_signature_path):
        try: os.remove(temp_signature_path)
        except: pass

    default_error_details = {
        "tampak_depan": False, "tampak_belakang": False, "tampak_kanan": False, "tampak_kiri": False,
        "cn_status": False, "sn_status": False, "model_status": False
    }

    if not text_result or not text_result.strip():
        return False, "Teks tidak berhasil diekstrak.", "-", "FOTO EMPAT SISI UNIT DISPOSED", default_error_details

    text_upper = text_result.upper()

    label_depan = "TAMPAK DEPAN" in text_upper
    label_belakang = "TAMPAK BELAKANG" in text_upper
    label_kanan = any(x in text_upper for x in ["TAMPAK SAMPING KANAN", "SAMPING KANAN", "SAMPMNG KANAN"])
    label_kiri = any(x in text_upper for x in ["TAMPAK SAMPING KIRI", "SAMPING KIRI", "SAMPMNG KIRI"])

    def clean_str(val):
        return re.sub(r"[^A-Z0-9]", "", str(val or "").upper())

    cn_clean = clean_str(target_cn)
    sn_clean = clean_str(target_sn)
    model_clean = clean_str(unit_model)
    doc_clean = clean_str(text_upper)

    doc_normalized = doc_clean.replace("O", "0")
    cn_normalized = cn_clean.replace("O", "0")

    # Evaluasi kecocokan identitas teks tabel CN SAP
    cn_status = False
    if cn_clean and (cn_clean in doc_clean or cn_normalized in doc_normalized):
        cn_status = True
    elif cn_clean:
        nomor_lambung = re.findall(r'\d+$', target_cn)
        if nomor_lambung and nomor_lambung[0] in doc_clean:
            cn_status = True

    # 🌟 VALIDASI MUTLAK 2: Jika nomor lambung fisik tidak terdeteksi sama sekali pada salah satu FOTO truk,
    # maka gagalkan status kecocokan CN (cn_status) secara paksa demi aspek kebenaran data fisik.
    if ext == '.pdf' and not cn_found_in_any_image:
        print(f"[OCR VALIDATION] Fraud Detected / Salah Unit: Nomor lambung {search_digits} tidak ditemukan menempel di foto unit.")
        cn_status = False

    sn_status = True if not sn_clean else (sn_clean in doc_clean)
    model_status = True if not model_clean else (model_clean in doc_clean)

    v_depan    = label_depan and images_detected["tampak_depan"]
    v_belakang = label_belakang and images_detected["tampak_belakang"]
    v_kanan    = label_kanan and images_detected["tampak_kanan"]
    v_kiri     = label_kiri and images_detected["tampak_kiri"]

    sisi_lengkap = v_depan and v_belakang and v_kanan and v_kiri
    identitas_cocok = cn_status and sn_status

    is_valid = sisi_lengkap and identitas_cocok

    detail_error = {
        "tampak_depan": v_depan,
        "tampak_belakang": v_belakang,
        "tampak_kanan": v_kanan,
        "tampak_kiri": v_kiri,
        "cn_status": cn_status,
        "sn_status": sn_status,
        "model_status": model_status
    }

    # 🌟 REVISI: Gabungkan informasi kecocokan data teks dan fisik agar tidak menumpuk di render modal JS
    report_details = (
        f"Tampak Depan : {'✅ Terverifikasi' if v_depan else '❌ KOSONG / LABEL TIDAK ADA'}<br>"
        f"Tampak Belakang : {'✅ Terverifikasi' if v_belakang else '❌ KOSONG / LABEL TIDAK ADA'}<br>"
        f"Tampak Samping Kanan : {'✅ Terverifikasi' if v_kanan else '❌ KOSONG / LABEL TIDAK ADA'}<br>"
        f"Tampak Samping Kiri : {'✅ Terverifikasi' if v_kiri else '❌ KOSONG / LABEL TIDAK ADA'}<br>"
        f"Kesesuaian Teks Tabel CN : {'✅ COCOK' if (cn_clean in doc_clean) else '❌ TIDAK MATCH'}<br>"
        f"Kebenaran Fisik Nomor Lambung di Foto : {'✅ VALID (Angka sesuai)' if cn_found_in_any_image else f'❌ TIDAK MATCH / SALAH UNIT (Mencari nomor bodi: {search_digits})'}"
    )

    if is_valid:
        success_msg = f"Dokumen Foto 4 Sisi VALID. Unit {target_cn} terverifikasi lengkap beserta kebenaran unit fisik."
        return True, success_msg, "-", "FOTO EMPAT SISI UNIT DISPOSED", detail_error

    errors = []
    missing_sides = []
    if not v_depan: missing_sides.append("Tampak Depan")
    if not v_belakang: missing_sides.append("Tampak Belakang")
    if not v_kanan: missing_sides.append("Samping Kanan")
    if not v_kiri: missing_sides.append("Samping Kiri")
    
    if missing_sides:
        errors.append(f"Kolom foto tidak lengkap atau kosong pada sisi: ({', '.join(missing_sides)})")
    if not cn_status:
        if ext == '.pdf' and not cn_found_in_any_image:
            errors.append(f"Nomor lambung fisik pada bodi foto truk tidak sesuai/tidak ditemukan (Mencari: {target_cn})")
        else:
            errors.append(f"Identitas tabel CN SAP tidak cocok (Mencari: {target_cn})")

    summary_err = "Gagal Validasi: " + ", ".join(errors) + "."
    full_message = f"{summary_err}<br><br>{report_details}"
    
    return False, full_message, "-", "FOTO EMPAT SISI UNIT DISPOSED", detail_error


# ===========================================================================
# ── 7. FUNGSI VERIFIKASI DOKUMEN INSPEKSI UNIT (CHECK SHEET) ──────────────
# ===========================================================================

def verifikasi_dokumen_inspeksi(file_path, target_cn, target_sn, unit_model, expected_nama="CHECK SHEET"):
    """
    Fungsi untuk memvalidasi dokumen CHECK SHEET (Inspeksi Unit).
    Memeriksa:
    1. Keberadaan Judul Dokumen (Check Sheet / Unit Inspection)
    2. Kesesuaian Ex Unit Code (CN SAP)
    3. Kesesuaian EGI / Unit Model (Tidak boleh kosong di dokumen & wajib match)
    4. Kesesuaian SN / Serial Number (Tidak boleh kosong di dokumen & wajib match)
    5. Kebenaran / Keberadaan Tanda Tangan Fisik menggunakan verifikasi_tanda_tangan_dinamis
    """
    import os
    import re

    if not os.path.exists(file_path):
        return False, f"File tidak ditemukan di path: {file_path}", "-", "-", "-"

    signature_img_path = None
    try:
        # 💡 PERBAIKAN 1: Tampung return value ke variabel 'results' agar sinkron dengan fungsi tanda tangan dinamis
        text_result, results, signature_img_path = extract_text_from_file(file_path)
    except Exception as e:
        return False, f"Gagal membaca file Check Sheet: {str(e)}", "-", "-", "-"

    if not text_result.strip():
        if signature_img_path and file_path != signature_img_path and os.path.exists(signature_img_path):
            os.remove(signature_img_path)
        return False, "Teks tidak berhasil diekstrak dari dokumen Check Sheet.", "-", "-", "-"

    is_valid = True
    error_messages = []

    text_upper = text_result.upper()

    # ── 1. VALIDASI NAMA DOKUMEN ──
    is_check_sheet = any(x in text_upper for x in [expected_nama.upper(), "UNIT INSPECTION", "RECEIVING AND DELIVERY"])
    if not is_check_sheet:
        is_valid = False
        error_messages.append("Dokumen yang diunggah bukan formulir CHECK SHEET / UNIT INSPECTION yang valid.")

    # Helper untuk membersihkan string & normalisasi karakter OCR yang mirip
    def clean_str(val):
        return re.sub(r"[^A-Z0-9]", "", str(val or "").upper())

    def normalize_fuzzy(val):
        # Mengubah O besar menjadi 0, dan I/L menjadi 1 demi akurasi verifikasi data bodi alat berat
        return clean_str(val).replace("O", "0").replace("I", "1").replace("L", "1")

    cn_clean = clean_str(target_cn)
    sn_clean = clean_str(target_sn)
    model_clean = clean_str(unit_model)
    
    doc_clean = clean_str(text_upper)
    doc_fuzzy = normalize_fuzzy(text_upper)
    cn_fuzzy = normalize_fuzzy(target_cn)

    # ── 2. VALIDASI KESESUAIAN CN UNIT (Ex Unit Code No) ──
    cn_status = False
    if cn_clean and (cn_clean in doc_clean or cn_fuzzy in doc_fuzzy):
        cn_status = True
    else:
        nomor_lambung = re.findall(r'\d+$', target_cn)
        if nomor_lambung and (nomor_lambung[0] in doc_clean or str(int(nomor_lambung[0])) in doc_clean):
            cn_status = True

    if not cn_status:
        is_valid = False
        error_messages.append(f"Nomor lambung unit pada dokumen tidak cocok. Mencari: {target_cn}")

    # ── 3 & 4. VALIDASI MODEL (EGI) DAN SERIAL NUMBER (SN) ──
    # Validasi Model (EGI)
    extracted_model = ""
    pos_model = doc_clean.find("UNITMODEL")
    if pos_model != -1:
        sub_text_model = doc_clean[pos_model:pos_model+60]
        sub_fuzzy_model = doc_fuzzy[pos_model:pos_model+60]
    else:
        sub_text_model = doc_clean
        sub_fuzzy_model = doc_fuzzy

    if model_clean in sub_text_model or normalize_fuzzy(unit_model) in sub_fuzzy_model:
        extracted_model = model_clean

    # 🌟 PERBAIKAN TOTAL & KETAT: SERIAL NUMBER MENGUNCI AREA TABEL ATAS
    extracted_sn = ""
    
    # 1. Cari jangkar eksklusif di wilayah tabel identitas atas
    pos_sn = doc_clean.find("SERIALNUMBER")
    if pos_sn == -1:
        pos_sn = doc_clean.find("SERIALNO")
    if pos_sn == -1:
        pos_sn = doc_clean.find("UNITSN")

    if pos_sn != -1:
        # Isolasi area kotak atas: ambil 60 karakter setelah jangkar ditemukan
        sub_text_sn = doc_clean[pos_sn:pos_sn+60]
        sub_fuzzy_sn = doc_fuzzy[pos_sn:pos_sn+60]
        
        # 2. Verifikasi kecocokan data: WAJIB cocok dengan database (sn_clean atau target_sn fuzzy)
        if sn_clean in sub_text_sn or normalize_fuzzy(target_sn) in sub_fuzzy_sn:
            extracted_sn = sn_clean
        else:
            # Jika user menginput SN salah, atau lembar atas kosong, JANGAN lakukan re.search seluruh dokumen!
            # Biarkan extracted_sn tetap kosong "" agar sistem menolak dokumen ini.
            print(f"[OCR INFO] Serial Number target '{target_sn}' tidak cocok di area tabel atas.")
    else:
        # Jika teks jangkar utama "SERIAL NUMBER" di atas dokumen tidak terbaca sama sekali oleh OCR,
        # baru lakukan fallback regex, namun dibatasi ketat agar tidak mengambil data dari baris komponen 46.
        sn_match = re.search(r"(?:SERIAL\s*NUMBER|SERIAL\s*NO)\s*[:\-\s]+([A-Z0-9\-]+)", text_upper)
        if sn_match:
            matched_val = clean_str(sn_match.group(1))
            # Pastikan teks yang tertangkap lolos filter kata bawaan form dan cocok dengan target
            if matched_val and "YEAR" not in matched_val and "MFG" not in matched_val:
                if sn_clean in matched_val or matched_val in sn_clean:
                    extracted_sn = sn_clean

    # Evaluasi kecocokan & kelengkapan administratif (Wajib Ada & Wajib Match)
    if not extracted_model:
        is_valid = False
        error_messages.append(f"Kolom 'Unit Model' ({unit_model}) tidak ditemukan atau tidak cocok pada dokumen.")

    if not extracted_sn:
        is_valid = False
        error_messages.append(f"Kolom 'Unit Serial Number' ({target_sn}) tidak ditemukan, kosong, atau tidak cocok pada dokumen.")

    # ── 5. VALIDASI OTORISASI TANDA TANGAN (DENGAN FALLBACK AMAN) ──
    status_signature = "Lengkap ✅ VALID"
    if is_valid:
        # ── A. VERIFIKASI TANDA TANGAN APPROVED BY ──
        approved_valid, approved_msg = verifikasi_tanda_tangan_dinamis(signature_img_path, results, "Approved")
        
        # Fallback Offset jika Approved By mendeteksi noise nama[cite: 2]
        if not approved_valid:
            anchor_bbox = None
            for bbox, text, prob in results:
                if "approved" in text.lower().strip():
                    anchor_bbox = bbox
                    break
            
            if anchor_bbox:
                try:
                    img = cv2.imread(signature_img_path)
                    h, w, _ = img.shape
                    anchor_y_bottom = int(anchor_bbox[2][1])
                    x_start = max(int(anchor_bbox[0][0]) - 40, 0)
                    x_end = min(int(anchor_bbox[1][0]) + 160, w)
                    y_start = anchor_y_bottom + 5
                    y_end = min(anchor_y_bottom + 135, h)
                    
                    roi_signature = img[y_start:y_end, x_start:x_end]
                    
                    # 💡 SOLUSI: Panggil langsung fungsi lokal tanpa redundansi import file sendiri
                    if analisis_goresan_tangan(roi_signature):
                        approved_valid = True
                        approved_msg = "Tanda tangan basah terdeteksi di bawah area Approved (Fallback)."
                except Exception as ex:
                    print(f"[OCR FALLBACK] Gagal eksekusi fallback approved: {ex}")

        # ── B. VERIFIKASI TANDA TANGAN INSPECTED BY ──[cite: 2, 3]
        inspected_valid, inspected_msg = verifikasi_tanda_tangan_dinamis(signature_img_path, results, "Inspected")
        
        # Fallback Offset jika Inspected By mendeteksi noise nama[cite: 3]
        if not inspected_valid:
            inspected_anchor_bbox = None
            for bbox, text, prob in results:
                if "inspected" in text.lower().strip():
                    inspected_anchor_bbox = bbox
                    break
            
            if inspected_anchor_bbox:
                try:
                    img = cv2.imread(signature_img_path)
                    h, w, _ = img.shape
                    inspected_y_bottom = int(inspected_anchor_bbox[2][1])
                    x_start_ins = max(int(inspected_anchor_bbox[0][0]) - 40, 0)
                    x_end_ins = min(int(inspected_anchor_bbox[1][0]) + 160, w)
                    y_start_ins = inspected_y_bottom + 5
                    y_end_ins = min(inspected_y_bottom + 135, h)
                    
                    roi_inspected = img[y_start_ins:y_end_ins, x_start_ins:x_end_ins]
                    
                    # 💡 SOLUSI: Panggil langsung fungsi lokal
                    if analisis_goresan_tangan(roi_inspected):
                        inspected_valid = True
                        inspected_msg = "Tanda tangan basah terdeteksi di bawah area Inspected (Fallback)."
                except Exception as ex:
                    print(f"[OCR FALLBACK] Gagal eksekusi fallback inspected: {ex}")

        # Evaluasi akhir kombinasi kedua tanda tangan[cite: 3]
        if not approved_valid or not inspected_valid:
            is_valid = False
            status_signature = "Tidak Lengkap ❌ TIDAK VALID"
            
            err_list = []
            if not approved_valid: err_list.append("Tanda Tangan 'Approved By' Kosong")
            if not inspected_valid: err_list.append("Tanda Tangan 'Inspected By' Kosong")
            error_messages.append(" | ".join(err_list))
    else:
        status_signature = "Belum Diperiksa (Data Unit Invalid) ❌"

    if signature_img_path and file_path != signature_img_path and os.path.exists(signature_img_path):
        try: os.remove(signature_img_path)
        except: pass

    # 📊 PEMBUATAN STRUKTUR TEKS LAPORAN (CHECKLIST UX)
    report_details = (
        f"Judul Dokumen  : {'CHECK SHEET' if is_check_sheet else 'TIDAK VALID'} " + ("✅ VALID" if is_check_sheet else "❌ TIDAK MATCH") + "<br>"
        f"CN SAP         : {target_cn if target_cn else '-'} " + ("✅ VALID" if cn_status else "❌ TIDAK MATCH") + "<br>"
        f"Unit Model     : {unit_model if unit_model else '-'} " + ("✅ VALID" if extracted_model else "❌ TIDAK MATCH / KOSONG") + "<br>"
        f"Serial Number  : {target_sn if target_sn else '-'} " + ("✅ VALID" if extracted_sn else "❌ TIDAK MATCH / KOSONG") + "<br>"
        f"Otorisasi Form : {status_signature}"
    )

    if is_valid:
        success_msg = f"Dokumen Check Sheet VALID untuk unit {target_cn}. Model, Serial Number, dan Tanda Tangan terverifikasi."
        return True, success_msg, "CHECK SHEET", "UNIT INSPECTION", "-"

    summary_err = " | ".join(error_messages)
    full_message = f"{summary_err}<br><br>{report_details}"
    return False, full_message, "CHECK SHEET", "UNIT INSPECTION", "-"



# ===================================================================
# ========Fungsi PDF Form Foto 4 sisi===============================
# ===================================================================
import os
from django.conf import settings
from django.utils import timezone
from django.http import HttpResponse
from reportlab.lib.pagesizes import letter
from reportlab.lib import colors
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle, Image

def generate_foto_4_sisi_pdf(obj, cn_sap, request=None, print_mode=False):
    """
    Fungsi utility terpusat untuk merakit dan menghasilkan file PDF Foto 4 Sisi Disposed.
    """
    response = HttpResponse(content_type='application/pdf')
    # 🔄 Menyesuaikan header berdasarkan mode (Print atau Download Murni)
    if print_mode:
        response['Content-Disposition'] = f'inline; filename="Foto_4_Sisi_{cn_sap}.pdf"'
    else:
        response['Content-Disposition'] = f'attachment; filename="Foto_4_Sisi_{cn_sap}.pdf"'

    doc = SimpleDocTemplate(response, pagesize=letter, rightMargin=30, leftMargin=30, topMargin=30, bottomMargin=30, title=f"Foto_4_Sisi_{cn_sap}")
    elements = []
    styles = getSampleStyleSheet()

    # Logo Perusahaan
    logo_path = os.path.join(settings.STATIC_ROOT if not settings.DEBUG else settings.STATICFILES_DIRS[0], 'img', 'logo_perusahaan.png')
    if not os.path.exists(logo_path):
        logo_path = os.path.join(settings.BASE_DIR, 'static', 'img', 'logo_perusahaan.png')

    if os.path.exists(logo_path):
        try:
            logo_img = Image(logo_path)
            orig_w, orig_h = logo_img.imageWidth, logo_img.imageHeight
            if orig_w > 0 and orig_h > 0:
                aspect = orig_h / orig_w
            else:
                aspect = 164 / 468  
            
            max_w = 55
            logo_img.drawWidth = max_w
            logo_img.drawHeight = max_w * aspect
        except Exception:
            logo_img = Paragraph('<b>[LOGO]</b>', styles['Normal'])
    else:
        logo_img = Paragraph('<b>[LOGO]</b>', styles['Normal'])
    
    # Ambil lokasi unit
    unit_location = getattr(obj, 'location', None) or getattr(obj, 'LOCATION', 'SITE')

    # Teks Kiri: PT Saptaindra Sejati & Plant Dept - Location
    company_style = ParagraphStyle(
        'CompanyTextStyle',
        parent=styles['Normal'],
        fontSize=9,
        leading=11
    )

    company_text = Paragraph(
        '<b>PT SAPTAINDRA SEJATI</b><br/><font fontName="Helvetica">PLANT DEPARTMENT - ' + str(unit_location) + '</font>', 
        company_style
    )

    # Teks Judul Form di Tengah / Sejajar
    title_style = ParagraphStyle(
        'CustomTitleStyle',
        parent=styles['Normal'],
        alignment=0,  
        fontSize=14,  
        leading=16    
    )

    form_title_text = Paragraph(
        '<b>FOTO EMPAT SISI EQUIPMENT DISPOSED</b>',
        title_style
    )

    # Tabel Header (3 Kolom: Logo, Info Perusahaan, Judul Form)
    header_data = [
        [
            logo_img,           
            company_text,       
            form_title_text       
        ]
    ]
    header_table = Table(header_data, colWidths=[65, 165, 332])
    header_table.setStyle(TableStyle([
        ('VALIGN', (0,0), (0,0), 'MIDDLE'),
        ('VALIGN', (1,0), (2,0), 'TOP'),
        ('ALIGN', (2,0), (2,0), 'LEFT'),
        ('LEFTPADDING', (2,0), (2,0), 10),
        ('RIGHTPADDING', (1,0), (1,0), 2),
        ('BOTTOMPADDING', (0,0), (-1,-1), 2),
        ('TOPPADDING', (1,0), (2,0), 4),    
    ]))
    
    elements.append(header_table)
    elements.append(Spacer(1, 10))

    # Informasi Detail Unit
    info_data = [
        [Paragraph('<b>Ex Unit Code No.</b>', styles['Normal']), Paragraph(f': {obj.asset.CN_SAP}', styles['Normal']),
         Paragraph('<b>Inspected Date</b>', styles['Normal']), Paragraph(f': {timezone.now().strftime("%d-%m-%Y")}', styles['Normal'])],
        [Paragraph('<b>Unit Model</b>', styles['Normal']), Paragraph(f': {getattr(obj.asset, "EGI", "-")}', styles['Normal']),
         Paragraph('<b>Location</b>', styles['Normal']), Paragraph(f': {getattr(obj.asset, "LOCATION", "-")}', styles['Normal'])],
        [Paragraph('<b>Unit Serial Number</b>', styles['Normal']), Paragraph(f': {getattr(obj.asset, "SN", "-")}', styles['Normal']),
         Paragraph('<b>SMR</b>', styles['Normal']), Paragraph(f': {getattr(obj.asset, "HM_SMR", "-")}', styles['Normal'])],
    ]
    t_info = Table(info_data, colWidths=[110, 160, 90, 180])
    t_info.setStyle(TableStyle([
        ('BOX', (0,0), (-1,-1), 0.5, colors.HexColor('#003366')),
        ('VALIGN', (0,0), (-1,-1), 'MIDDLE'),
        ('PADDING', (0,0), (-1,-1), 5),
        ('BACKGROUND', (0,0), (-1,-1), colors.HexColor('#f8f9fa')),
    ]))
    elements.append(t_info)
    elements.append(Spacer(1, 15))

    def get_img_path(field_file):
        try:
            if field_file and hasattr(field_file, 'path') and os.path.exists(field_file.path):
                return field_file.path
        except Exception:
            pass
        return None

    img_depan = get_img_path(obj.tampak_depan)
    img_belakang = get_img_path(obj.tampak_belakang)
    img_kanan = get_img_path(obj.tampak_samping_kanan)
    img_kiri = get_img_path(obj.tampak_samping_kiri)

    # Style khusus untuk label agar posisinya di tengah (Center Alignment)
    label_style = ParagraphStyle(
        'CenterLabelStyle',
        parent=styles['Normal'],
        alignment=1,  # Rata Tengah
        fontSize=10,
        fontName='Helvetica-Bold'
    )

    # Helper function untuk membuat objek Image dengan menjaga aspek rasio
    def get_proportional_image(path, max_width=230, max_height=130):
        if not path:
            return Paragraph('Tidak ada gambar', styles['Normal'])
        try:
            img_obj = Image(path)
            orig_w, orig_h = img_obj.imageWidth, img_obj.imageHeight
            
            if orig_w > 0 and orig_h > 0:
                aspect = orig_h / orig_w
                w = max_width
                h = w * aspect
                if h > max_height:
                    h = max_height
                    w = h / aspect
                img_obj.drawWidth = w
                img_obj.drawHeight = h
            return img_obj
        except Exception:
            return Paragraph('Gagal memuat gambar', styles['Normal'])

    # Grid Foto 4 Sisi dengan label rata tengah
    foto_grid = [
        [Paragraph('TAMPAK DEPAN', label_style), Paragraph('TAMPAK BELAKANG', label_style)],
        [
            get_proportional_image(img_depan),
            get_proportional_image(img_belakang)
        ],
        [Paragraph('TAMPAK SAMPING KANAN', label_style), Paragraph('TAMPAK SAMPING KIRI', label_style)],
        [
            get_proportional_image(img_kanan),
            get_proportional_image(img_kiri)
        ]
    ]

    t_foto = Table(foto_grid, colWidths=[270, 270])
    t_foto.setStyle(TableStyle([
        ('ALIGN', (0,0), (-1,-1), 'CENTER'),
        ('VALIGN', (0,0), (-1,-1), 'MIDDLE'),
        ('GRID', (0,0), (-1,-1), 0.5, colors.HexColor('#cccccc')),
        ('BACKGROUND', (0,0), (-1,0), colors.HexColor('#e9ecef')),
        ('BACKGROUND', (0,2), (-1,2), colors.HexColor('#e9ecef')),
        ('PADDING', (0,0), (-1,-1), 6),
    ]))

    elements.append(t_foto)
    elements.append(Spacer(1, 25))

    # ==========================================
    # BAGIAN TANDA TANGAN (Diajukan & Disetujui)
    # ==========================================
    
    # 1. Ambil uploader dari database
    uploader = getattr(obj, 'foto_4_sisi_uploaded_by', None) or getattr(obj, 'updated_by', None)

    # Inisialisasi variabel default
    prep_name = "PIC Planner Plant"
    prep_title = "Maintenance Planner"
    sig_image_file = None

    appr_name = getattr(obj, 'approved_by_name', None) or "PIC Plant Section Head"
    appr_title = getattr(obj, 'approved_by_title', None) or "Plant Section Head"
    sig_image_appr_file = None

    if uploader:
        prep_name = uploader.get_full_name() or uploader.username
        
        profile = getattr(uploader, 'userprofile', None)
        if profile:
            prep_title = getattr(profile, 'jabatan_nama_resmi', None) or getattr(profile, 'jabatan', None) or "Senior Officer"
            sig_image_file = profile.tanda_tangan
            
            if getattr(obj, 'status_approval', '') == 'APPROVED':
                atasan_profile = profile.atasan_langsung
                if atasan_profile:
                    if atasan_profile.user:
                        appr_name = atasan_profile.user.get_full_name() or atasan_profile.user.username
                    
                    appr_title = getattr(atasan_profile, 'jabatan_nama_resmi', None) or atasan_profile.get_jabatan_level_display()
                    sig_image_appr_file = atasan_profile.tanda_tangan

   # 🔄 DIUBAH: Hapus updated_at dari sini agar jam Ibram murni milik Ibram sendiri
    submitted_date_str = ""
    active_submit_time = (
        getattr(obj, 'submitted_at', None) or 
        getattr(obj, 'foto_4_sisi_uploaded_at', None)
    )
    
    if active_submit_time:
        # Konversi paksa datetime ke zona waktu Asia/Jakarta (WIB)
        local_submit_time = timezone.localtime(active_submit_time)
        submitted_date_str = local_submit_time.strftime('%d %b %Y %H:%M')

    approved_date_str = ""
    if getattr(obj, 'approved_at', None) and getattr(obj, 'status_approval', '') == 'APPROVED':
        local_approve_time = timezone.localtime(obj.approved_at)
        approved_date_str = local_approve_time.strftime('%d %b %Y %H:%M')

    sig_style_left = ParagraphStyle(
        'SigLeft',
        parent=styles['Normal'],
        alignment=0,  # Rata kiri
        fontSize=9,
        leading=13
    )

    sig_style_right = ParagraphStyle(
        'SigRight',
        parent=styles['Normal'],
        alignment=2,  # Rata kanan
        fontSize=9,
        leading=13
    )
    
    # Menyiapkan elemen gambar tanda tangan pembuat (Diajukan oleh)
    if sig_image_file and hasattr(sig_image_file, 'path') and os.path.exists(sig_image_file.path):
        img_prep = Image(sig_image_file.path, width=100, height=40)
        img_prep.hAlign = 'LEFT'
    else:
        img_prep = Spacer(1, 40)

    # --- PERBAIKAN UTAMA: Bungkus tanda tangan atasan dengan mini-table agar 100% rata kanan ---
    if sig_image_appr_file and hasattr(sig_image_appr_file, 'path') and os.path.exists(sig_image_appr_file.path):
        img_appr_raw = Image(sig_image_appr_file.path, width=100, height=40)
        img_appr_raw.hAlign = 'RIGHT'
        # Buat tabel kecil selebar sel utama (210 pt setelah dikurangi padding) untuk memaksa gambar di kanan
        t_nested_appr = Table([[img_appr_raw]], colWidths=[210])
        t_nested_appr.setStyle(TableStyle([
            ('ALIGN', (0,0), (-1,-1), 'RIGHT'),
            ('LEFTPADDING', (0,0), (-1,-1), 0),
            ('RIGHTPADDING', (0,0), (-1,-1), 0),
            ('TOPPADDING', (0,0), (-1,-1), 0),
            ('BOTTOMPADDING', (0,0), (-1,-1), 0),
        ]))
        img_appr = t_nested_appr
    else:
        img_appr = Spacer(1, 40)

    # Menyisipkan informasi tanggal di atas tanda tangan
    sig_data = [
        [
            Paragraph('Diajukan oleh,', sig_style_left),
            Paragraph('Disetujui oleh,', sig_style_right)
        ],
        [
            Paragraph(f'<font color="#555555" size="8">Tanggal: {submitted_date_str}</font>' if submitted_date_str else '', sig_style_left),
            Paragraph(f'<font color="#555555" size="8">Tanggal: {approved_date_str}</font>' if approved_date_str else '', sig_style_right)
        ],
        [
            img_prep,
            img_appr
        ],
        [
            Paragraph(f'<b><u>{prep_name}</u></b><br/>{prep_title}', sig_style_left),
            Paragraph(f'<b><u>{appr_name}</u></b><br/>{appr_title}', sig_style_right)
        ]
    ]

    t_sig = Table(sig_data, colWidths=[240, 240])
    t_sig.setStyle(TableStyle([
        ('VALIGN', (0,0), (-1,-1), 'MIDDLE'),
        ('LEFTPADDING', (0,0), (-1,-1), 15),
        ('RIGHTPADDING', (0,0), (-1,-1), 15),
        ('BOTTOMPADDING', (0,0), (-1,-1), 2),
        ('TOPPADDING', (0,0), (-1,-1), 2),
    ]))

    elements.append(t_sig)

    doc.build(elements)
    
    return response

#===================================================================================
#==================== GENERATE FOTO 4 SISI DALAM PDF ================================
#====================================================================================

 
def generate_pdf_foto_4_sisi_file(instance):
    """
    Fungsi helper khusus background email untuk membangun file PDF fisik 
    secara temporary menggunakan ReportLab berdasarkan struktur generate_foto_4_sisi_pdf.
    """
    try:
        cn_sap = instance.asset.CN_SAP if instance.asset else getattr(instance, 'CN_SAP', 'UNKNOWN')
        
        # Tentukan lokasi penyimpanan file PDF sementara di folder media/temp_pdf
        output_dir = os.path.join(settings.MEDIA_ROOT, 'temp_pdf')
        os.makedirs(output_dir, exist_ok=True)
        
        safe_cn_name = str(cn_sap).replace('/', '_')
        file_name = f"Form_Foto_Empat_Sisi_Equipment_Disposed_{safe_cn_name}.pdf"
        pdf_output_path = os.path.join(output_dir, file_name)

        # Menggunakan SimpleDocTemplate langsung ke file fisik (bukan HttpResponse)
        doc = SimpleDocTemplate(
            pdf_output_path, 
            pagesize=letter, 
            rightMargin=30, 
            leftMargin=30, 
            topMargin=30, 
            bottomMargin=30, 
            title=f"Foto_4_Sisi_{safe_cn_name}"
        )
        
        elements = []
        styles = getSampleStyleSheet()

        # Logo Perusahaan
        logo_path = os.path.join(settings.STATIC_ROOT if not settings.DEBUG else settings.STATICFILES_DIRS[0], 'img', 'logo_perusahaan.png')
        if not os.path.exists(logo_path):
            logo_path = os.path.join(settings.BASE_DIR, 'static', 'img', 'logo_perusahaan.png')

        if os.path.exists(logo_path):
            try:
                logo_img = Image(logo_path)
                orig_w, orig_h = logo_img.imageWidth, logo_img.imageHeight
                aspect = (orig_h / orig_w) if (orig_w > 0 and orig_h > 0) else (164 / 468)
                max_w = 55
                logo_img.drawWidth = max_w
                logo_img.drawHeight = max_w * aspect
            except Exception:
                logo_img = Paragraph('<b>[LOGO]</b>', styles['Normal'])
        else:
            logo_img = Paragraph('<b>[LOGO]</b>', styles['Normal'])
        
        unit_location = getattr(instance, 'location', None) or getattr(instance, 'LOCATION', 'SITE')

        company_style = ParagraphStyle('CompanyTextStyle', parent=styles['Normal'], fontSize=9, leading=11)
        company_text = Paragraph(f'<b>PT SAPTAINDRA SEJATI</b><br/><font fontName="Helvetica">PLANT DEPARTMENT - {unit_location}</font>', company_style)

        title_style = ParagraphStyle('CustomTitleStyle', parent=styles['Normal'], alignment=0, fontSize=14, leading=16)
        form_title_text = Paragraph('<b>FOTO EMPAT SISI EQUIPMENT DISPOSED</b>', title_style)

        header_data = [[logo_img, company_text, form_title_text]]
        header_table = Table(header_data, colWidths=[65, 165, 332])
        header_table.setStyle(TableStyle([
            ('VALIGN', (0,0), (0,0), 'MIDDLE'),
            ('VALIGN', (1,0), (2,0), 'TOP'),
            ('ALIGN', (2,0), (2,0), 'LEFT'),
            ('LEFTPADDING', (2,0), (2,0), 10),
            ('RIGHTPADDING', (1,0), (1,0), 2),
            ('BOTTOMPADDING', (0,0), (-1,-1), 2),
            ('TOPPADDING', (1,0), (2,0), 4),    
        ]))
        
        elements.append(header_table)
        elements.append(Spacer(1, 10))

        # Informasi Detail Unit
        info_data = [
            [Paragraph('<b>Ex Unit Code No.</b>', styles['Normal']), Paragraph(f': {cn_sap}', styles['Normal']),
             Paragraph('<b>Inspected Date</b>', styles['Normal']), Paragraph(f': {timezone.now().strftime("%d-%m-%Y")}', styles['Normal'])],
            [Paragraph('<b>Unit Model</b>', styles['Normal']), Paragraph(f': {getattr(instance.asset, "EGI", "-")}', styles['Normal']),
             Paragraph('<b>Location</b>', styles['Normal']), Paragraph(f': {getattr(instance.asset, "LOCATION", "-")}', styles['Normal'])],
            [Paragraph('<b>Unit Serial Number</b>', styles['Normal']), Paragraph(f': {getattr(instance.asset, "SN", "-")}', styles['Normal']),
             Paragraph('<b>SMR</b>', styles['Normal']), Paragraph(f': {getattr(instance.asset, "HM_SMR", "-")}', styles['Normal'])],
        ]
        t_info = Table(info_data, colWidths=[110, 160, 90, 180])
        t_info.setStyle(TableStyle([
            ('BOX', (0,0), (-1,-1), 0.5, colors.HexColor('#003366')),
            ('VALIGN', (0,0), (-1,-1), 'MIDDLE'),
            ('PADDING', (0,0), (-1,-1), 5),
            ('BACKGROUND', (0,0), (-1,-1), colors.HexColor('#f8f9fa')),
        ]))
        elements.append(t_info)
        elements.append(Spacer(1, 15))

        def get_img_path(field_file):
            try:
                if field_file and hasattr(field_file, 'path') and os.path.exists(field_file.path):
                    return field_file.path
            except Exception:
                pass
            return None

        img_depan = get_img_path(instance.tampak_depan)
        img_belakang = get_img_path(instance.tampak_belakang)
        img_kanan = get_img_path(instance.tampak_samping_kanan)
        img_kiri = get_img_path(instance.tampak_samping_kiri)

        label_style = ParagraphStyle('CenterLabelStyle', parent=styles['Normal'], alignment=1, fontSize=10, fontName='Helvetica-Bold')

        def get_proportional_image(path, max_width=230, max_height=130):
            if not path:
                return Paragraph('Tidak ada gambar', styles['Normal'])
            try:
                img_obj = Image(path)
                orig_w, orig_h = img_obj.imageWidth, img_obj.imageHeight
                if orig_w > 0 and orig_h > 0:
                    aspect = orig_h / orig_w
                    w = max_width
                    h = w * aspect
                    if h > max_height:
                        h = max_height
                        w = h / aspect
                    img_obj.drawWidth = w
                    img_obj.drawHeight = h
                return img_obj
            except Exception:
                return Paragraph('Gagal memuat gambar', styles['Normal'])

        foto_grid = [
            [Paragraph('TAMPAK DEPAN', label_style), Paragraph('TAMPAK BELAKANG', label_style)],
            [get_proportional_image(img_depan), get_proportional_image(img_belakang)],
            [Paragraph('TAMPAK SAMPING KANAN', label_style), Paragraph('TAMPAK SAMPING KIRI', label_style)],
            [get_proportional_image(img_kanan), get_proportional_image(img_kiri)]
        ]

        t_foto = Table(foto_grid, colWidths=[270, 270])
        t_foto.setStyle(TableStyle([
            ('ALIGN', (0,0), (-1,-1), 'CENTER'),
            ('VALIGN', (0,0), (-1,-1), 'MIDDLE'),
            ('GRID', (0,0), (-1,-1), 0.5, colors.HexColor('#cccccc')),
            ('BACKGROUND', (0,0), (-1,0), colors.HexColor('#e9ecef')),
            ('BACKGROUND', (0,2), (-1,2), colors.HexColor('#e9ecef')),
            ('PADDING', (0,0), (-1,-1), 6),
        ]))

        elements.append(t_foto)
        elements.append(Spacer(1, 25))

        # Tanda Tangan Logic
        uploader = getattr(instance, 'foto_4_sisi_uploaded_by', None) or getattr(instance, 'updated_by', None)
        prep_name, prep_title, sig_image_file = "PIC Planner Plant", "Maintenance Planner", None
        appr_name, appr_title, sig_image_appr_file = getattr(instance, 'approved_by_name', None) or "PIC Plant Section Head", "Plant Section Head", None

        if uploader:
            prep_name = uploader.get_full_name() or uploader.username
            profile = getattr(uploader, 'userprofile', None)
            if profile:
                prep_title = getattr(profile, 'jabatan_nama_resmi', None) or getattr(profile, 'jabatan', None) or "Senior Officer"
                sig_image_file = profile.tanda_tangan
                if getattr(instance, 'status_approval', '') == 'APPROVED':
                    atasan_profile = profile.atasan_langsung
                    if atasan_profile and atasan_profile.user:
                        appr_name = atasan_profile.user.get_full_name() or atasan_profile.user.username
                        appr_title = getattr(atasan_profile, 'jabatan_nama_resmi', None) or atasan_profile.get_jabatan_level_display()
                        sig_image_appr_file = atasan_profile.tanda_tangan

        submitted_date_str = ""
        active_submit_time = getattr(instance, 'submitted_at', None) or getattr(instance, 'foto_4_sisi_uploaded_at', None)
        if active_submit_time:
            submitted_date_str = timezone.localtime(active_submit_time).strftime('%d %b %Y %H:%M')

        approved_date_str = ""
        if getattr(instance, 'approved_at', None) and getattr(instance, 'status_approval', '') == 'APPROVED':
            approved_date_str = timezone.localtime(instance.approved_at).strftime('%d %b %Y %H:%M')

        sig_style_left = ParagraphStyle('SigLeft', parent=styles['Normal'], alignment=0, fontSize=9, leading=13)
        sig_style_right = ParagraphStyle('SigRight', parent=styles['Normal'], alignment=2, fontSize=9, leading=13)
        
        img_prep = Image(sig_image_file.path, width=100, height=40) if (sig_image_file and hasattr(sig_image_file, 'path') and os.path.exists(sig_image_file.path)) else Spacer(1, 40)
        
        if sig_image_appr_file and hasattr(sig_image_appr_file, 'path') and os.path.exists(sig_image_appr_file.path):
            img_appr_raw = Image(sig_image_appr_file.path, width=100, height=40)
            t_nested_appr = Table([[img_appr_raw]], colWidths=[210])
            t_nested_appr.setStyle(TableStyle([('ALIGN', (0,0), (-1,-1), 'RIGHT'), ('LEFTPADDING', (0,0), (-1,-1), 0), ('RIGHTPADDING', (0,0), (-1,-1), 0), ('TOPPADDING', (0,0), (-1,-1), 0), ('BOTTOMPADDING', (0,0), (-1,-1), 0)]))
            img_appr = t_nested_appr
        else:
            img_appr = Spacer(1, 40)

        sig_data = [
            [Paragraph('Diajukan oleh,', sig_style_left), Paragraph('Disetujui oleh,', sig_style_right)],
            [Paragraph(f'<font color="#555555" size="8">Tanggal: {submitted_date_str}</font>' if submitted_date_str else '', sig_style_left),
             Paragraph(f'<font color="#555555" size="8">Tanggal: {approved_date_str}</font>' if approved_date_str else '', sig_style_right)],
            [img_prep, img_appr],
            [Paragraph(f'<b><u>{prep_name}</u></b><br/>{prep_title}', sig_style_left),
             Paragraph(f'<b><u>{appr_name}</u></b><br/>{appr_title}', sig_style_right)]
        ]

        t_sig = Table(sig_data, colWidths=[240, 240])
        t_sig.setStyle(TableStyle([
            ('VALIGN', (0,0), (-1,-1), 'MIDDLE'),
            ('LEFTPADDING', (0,0), (-1,-1), 15),
            ('RIGHTPADDING', (0,0), (-1,-1), 15),
            ('BOTTOMPADDING', (0,0), (-1,-1), 2),
            ('TOPPADDING', (0,0), (-1,-1), 2),
        ]))

        elements.append(t_sig)
        doc.build(elements)

        if os.path.exists(pdf_output_path):
            return pdf_output_path
            
    except Exception as e:
        print(f" --> [ERROR] Gagal generate PDF file fisik: {str(e)}")
        
    return None



#=========================================================================
#======= GENERATE PDF FORM INSPEKSI EQUIPMENT ============================
#=========================================================================

import os
from django.conf import settings
from django.utils import timezone
from reportlab.lib.pagesizes import letter
from reportlab.lib import colors
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle, Image
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle

def generate_pdf_inspeksi_unit_file(instance):
    """
    Fungsi helper khusus background email untuk membangun file PDF fisik 
    check sheet inspeksi unit secara temporary menggunakan ReportLab.
    """
    try:
        cn_sap = instance.asset.CN_SAP if instance.asset else getattr(instance, 'CN_SAP', 'UNKNOWN')
        
        # Tentukan lokasi penyimpanan file PDF sementara di folder media/temp_pdf
        output_dir = os.path.join(settings.MEDIA_ROOT, 'temp_pdf')
        os.makedirs(output_dir, exist_ok=True)
        
        safe_cn_name = str(cn_sap).replace('/', '_')
        file_name = f"Checksheet_Inspeksi_Unit_Disposed_{safe_cn_name}.pdf"
        pdf_output_path = os.path.join(output_dir, file_name)

        # Menggunakan SimpleDocTemplate langsung ke file fisik (bukan HttpResponse)
        doc = SimpleDocTemplate(
            pdf_output_path, 
            pagesize=letter, 
            rightMargin=30, 
            leftMargin=30, 
            topMargin=30, 
            bottomMargin=30, 
            title=f"Checksheet_Inspeksi_{safe_cn_name}"
        )
        
        elements = []
        styles = getSampleStyleSheet()

        # Logo Perusahaan
        logo_path = os.path.join(settings.STATIC_ROOT if not settings.DEBUG else settings.STATICFILES_DIRS[0], 'img', 'logo_perusahaan.png')
        if not os.path.exists(logo_path):
            logo_path = os.path.join(settings.BASE_DIR, 'static', 'img', 'logo_perusahaan.png')

        if os.path.exists(logo_path):
            try:
                logo_img = Image(logo_path)
                orig_w, orig_h = logo_img.imageWidth, logo_img.imageHeight
                aspect = (orig_h / orig_w) if (orig_w > 0 and orig_h > 0) else (164 / 468)
                max_w = 55
                logo_img.drawWidth = max_w
                logo_img.drawHeight = max_w * aspect
            except Exception:
                logo_img = Paragraph('<b>[LOGO]</b>', styles['Normal'])
        else:
            logo_img = Paragraph('<b>[LOGO]</b>', styles['Normal'])
        
        unit_location = getattr(instance, 'location', None) or getattr(instance, 'LOCATION', 'SITE')

        company_style = ParagraphStyle('CompanyTextStyle', parent=styles['Normal'], fontSize=9, leading=11)
        company_text = Paragraph(f'<b>PT SAPTAINDRA SEJATI</b><br/><font fontName="Helvetica">PLANT DEPARTMENT - {unit_location}</font>', company_style)

        title_style = ParagraphStyle('CustomTitleStyle', parent=styles['Normal'], alignment=0, fontSize=13, leading=15)
        form_title_text = Paragraph('<b>CHECK SHEET INSPEKSI UNIT DISPOSED</b>', title_style)

        header_data = [[logo_img, company_text, form_title_text]]
        header_table = Table(header_data, colWidths=[65, 165, 332])
        header_table.setStyle(TableStyle([
            ('VALIGN', (0,0), (0,0), 'MIDDLE'),
            ('VALIGN', (1,0), (2,0), 'TOP'),
            ('ALIGN', (2,0), (2,0), 'LEFT'),
            ('LEFTPADDING', (2,0), (2,0), 10),
            ('RIGHTPADDING', (1,0), (1,0), 2),
            ('BOTTOMPADDING', (0,0), (-1,-1), 2),
            ('TOPPADDING', (1,0), (2,0), 4),    
        ]))
        
        elements.append(header_table)
        elements.append(Spacer(1, 10))

        # Informasi Detail Unit
        info_data = [
            [Paragraph('<b>Ex Unit Code No.</b>', styles['Normal']), Paragraph(f': {cn_sap}', styles['Normal']),
             Paragraph('<b>Inspected Date</b>', styles['Normal']), Paragraph(f': {timezone.now().strftime("%d-%m-%Y")}', styles['Normal'])],
            [Paragraph('<b>Unit Model / EGI</b>', styles['Normal']), Paragraph(f': {getattr(instance, "EGI", "-")}', styles['Normal']),
             Paragraph('<b>Equipment Type</b>', styles['Normal']), Paragraph(f': {getattr(instance, "TYPE", "-")}', styles['Normal'])],
            [Paragraph('<b>Unit Serial Number</b>', styles['Normal']), Paragraph(f': {getattr(instance, "SN", "-")}', styles['Normal']),
             Paragraph('<b>SMR</b>', styles['Normal']), Paragraph(f': {getattr(instance, "HM_SMR", "-")}', styles['Normal'])],
        ]
        t_info = Table(info_data, colWidths=[110, 160, 90, 180])
        t_info.setStyle(TableStyle([
            ('BOX', (0,0), (-1,-1), 0.5, colors.HexColor('#003366')),
            ('VALIGN', (0,0), (-1,-1), 'MIDDLE'),
            ('PADDING', (0,0), (-1,-1), 5),
            ('BACKGROUND', (0,0), (-1,-1), colors.HexColor('#f8f9fa')),
        ]))
        elements.append(t_info)
        elements.append(Spacer(1, 15))

        # ── TABEL DAFTAR ITEM INSPEKSI ──
        th_style = ParagraphStyle('TableHeader', parent=styles['Normal'], fontName='Helvetica-Bold', fontSize=9, textColor=colors.white, alignment=1)
        td_style = ParagraphStyle('TableCell', parent=styles['Normal'], fontSize=8, leading=10)
        td_center = ParagraphStyle('TableCellCenter', parent=styles['Normal'], fontSize=8, alignment=1)

        item_headers = [
            Paragraph('No', th_style),
            Paragraph('Group Item', th_style),
            Paragraph('Uraian Pemeriksaan / Item Check', th_style),
            Paragraph('Status / Hasil', th_style)
        ]
                       
        item_rows = [item_headers]
        
        # Ambil data item dari relasi model jika ada (sesuaikan dengan related name / method Anda)
        # Contoh iterasi item check yang tersimpan pada instance unit
        # PERBAIKAN: Ambil template item inspeksi langsung dari aplikasi data berdasarkan EGI unit
        from data.models import InspectionTemplateItem
        unit_type = getattr(instance, 'TYPE', None)
        
        inspection_items = []
        if unit_type:
            inspection_items = InspectionTemplateItem.objects.filter(TYPE=unit_type)
        
        if inspection_items:
            for idx, item in enumerate(inspection_items, 1):
                item_rows.append([
                    Paragraph(str(idx), td_center),
                    Paragraph(str(getattr(item, 'ITEM_GROUP', '-')), td_style),
                    Paragraph(str(getattr(item, 'ITEM_NAME', '-')), td_style),
                    Paragraph('OK', td_center)  # Status default atau disesuaikan dengan hasil inputan
                ])
        else:
            # Baris fallback jika data template berdasarkan TYPE tidak ditemukan
            item_rows.append([
                Paragraph('1', td_center),
                Paragraph('General', td_style),
                Paragraph('Tidak ada item check sheet terdaftar untuk Equipment Type ini.', td_style),
                Paragraph('-', td_center)
            ])

        t_items = Table(item_rows, colWidths=[30, 140, 260, 92])
        t_items.setStyle(TableStyle([
            ('BACKGROUND', (0,0), (-1,0), colors.HexColor('#003366')),
            ('ALIGN', (0,0), (-1,0), 'CENTER'),
            ('VALIGN', (0,0), (-1,-1), 'MIDDLE'),
            ('GRID', (0,0), (-1,-1), 0.5, colors.HexColor('#cccccc')),
            ('PADDING', (0,0), (-1,-1), 5),
            ('ROWBACKGROUNDS', (0,1), (-1,-1), [colors.white, colors.HexColor('#f9f9f9')])
        ]))

        elements.append(t_items)
        elements.append(Spacer(1, 20))

        # ── TANDA TANGAN & APPROVAL LOGIC ──
        uploader = getattr(instance, 'inspeksi_unit_uploaded_by', None) or getattr(instance, 'submitted_by', None)
        prep_name, prep_title, sig_image_file = "PIC Inspector", "Maintenance Staff", None
        appr_name, appr_title, sig_image_appr_file = "Plant Section Head", "Plant Section Head", None

        # 1. Data Pembuat / Uploader
        if uploader:
            prep_name = uploader.get_full_name() or uploader.username
            profile = getattr(uploader, 'userprofile', None)
            if profile:
                prep_title = getattr(profile, 'jabatan_nama_resmi', None) or getattr(profile, 'jabatan', None) or "Senior Officer"
                sig_image_file = profile.tanda_tangan

        # 2. Data Atasan yang Approve (Mendukung hasil approval inspeksi)
        is_approved = (getattr(instance, 'inspeksi_status', '') == 'APPROVED' or getattr(instance, 'status_approval', '') == 'APPROVED')
        
        if is_approved:
            # Cek apakah model menyimpan relasi khusus approver inspeksi, jika tidak gunakan atasan dari uploader/profile
            approver_user = getattr(instance, 'inspeksi_approver', None)
            
            if approver_user and hasattr(approver_user, 'userprofile'):
                appr_profile = approver_user.userprofile
                appr_name = approver_user.get_full_name() or approver_user.username
                appr_title = getattr(appr_profile, 'jabatan_nama_resmi', None) or getattr(appr_profile, 'jabatan', None) or "Plant Section Head"
                sig_image_appr_file = appr_profile.tanda_tangan
            elif uploader and hasattr(uploader, 'userprofile') and uploader.userprofile.atasan_langsung:
                atasan_profile = uploader.userprofile.atasan_langsung
                if atasan_profile and atasan_profile.user:
                    appr_name = atasan_profile.user.get_full_name() or atasan_profile.user.username
                    appr_title = getattr(atasan_profile, 'jabatan_nama_resmi', None) or atasan_profile.get_jabatan_level_display()
                    sig_image_appr_file = atasan_profile.tanda_tangan

        submitted_date_str = ""
        active_submit_time = getattr(instance, 'submitted_at', None) or getattr(instance, 'inspeksi_unit_uploaded_at', None)
        if active_submit_time:
            submitted_date_str = timezone.localtime(active_submit_time).strftime('%d %b %Y %H:%M')

        approved_date_str = ""
        active_approved_time = getattr(instance, 'inspeksi_approved_at', None) or getattr(instance, 'approved_at', None)
        if active_approved_time and is_approved:
            approved_date_str = timezone.localtime(active_approved_time).strftime('%d %b %Y %H:%M')

        sig_style_left = ParagraphStyle('SigLeft', parent=styles['Normal'], alignment=0, fontSize=9, leading=13)
        sig_style_right = ParagraphStyle('SigRight', parent=styles['Normal'], alignment=2, fontSize=9, leading=13)
        
        img_prep = Image(sig_image_file.path, width=100, height=40) if (sig_image_file and hasattr(sig_image_file, 'path') and os.path.exists(sig_image_file.path)) else Spacer(1, 40)
        
        if sig_image_appr_file and hasattr(sig_image_appr_file, 'path') and os.path.exists(sig_image_appr_file.path):
            img_appr_raw = Image(sig_image_appr_file.path, width=100, height=40)
            t_nested_appr = Table([[img_appr_raw]], colWidths=[210])
            t_nested_appr.setStyle(TableStyle([('ALIGN', (0,0), (-1,-1), 'RIGHT'), ('LEFTPADDING', (0,0), (-1,-1), 0), ('RIGHTPADDING', (0,0), (-1,-1), 0), ('TOPPADDING', (0,0), (-1,-1), 0), ('BOTTOMPADDING', (0,0), (-1,-1), 0)]))
            img_appr = t_nested_appr
        else:
            img_appr = Spacer(1, 40)

        sig_data = [
            [Paragraph('Diajukan oleh,', sig_style_left), Paragraph('Disetujui oleh,', sig_style_right)],
            [Paragraph(f'<font color="#555555" size="8">Tanggal: {submitted_date_str}</font>' if submitted_date_str else '', sig_style_left),
             Paragraph(f'<font color="#555555" size="8">Tanggal: {approved_date_str}</font>' if approved_date_str else '', sig_style_right)],
            [img_prep, img_appr],
            [Paragraph(f'<b><u>{prep_name}</u></b><br/>{prep_title}', sig_style_left),
             Paragraph(f'<b><u>{appr_name}</u></b><br/>{appr_title}', sig_style_right)]
        ]

        t_sig = Table(sig_data, colWidths=[240, 240])
        t_sig.setStyle(TableStyle([
            ('VALIGN', (0,0), (-1,-1), 'MIDDLE'),
            ('LEFTPADDING', (0,0), (-1,-1), 15),
            ('RIGHTPADDING', (0,0), (-1,-1), 15),
            ('BOTTOMPADDING', (0,0), (-1,-1), 2),
            ('TOPPADDING', (0,0), (-1,-1), 2),
        ]))

        elements.append(t_sig)
        doc.build(elements)

        if os.path.exists(pdf_output_path):
            return pdf_output_path
            
    except Exception as e:
        print(f" --> [ERROR] Gagal generate PDF file fisik inspeksi unit: {str(e)}")
        
    return None