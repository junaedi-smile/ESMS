(function($){
    $(document).ready(function(){
        // Menggunakan selector yang lebih spesifik
        // #changelist-form mengacu pada form utama di halaman list
        var table = $('#changelist-form table');
        if (table.length) {
            // Inisialisasi pustaka colResizable pada tabel
            table.colResizable({
                liveDrag: true, // Untuk memperbarui ukuran saat diseret
                // Tambahkan opsi lain sesuai kebutuhan Anda
            });
        }
    });
})(django.jQuery);