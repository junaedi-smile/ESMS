document.addEventListener("DOMContentLoaded", function() {
    // Ambil semua elemen badge yang berstatus waiting atau yang perlu dipantau
    const badgeElements = document.querySelectorAll('.polling-status-waiting');
    
    badgeElements.forEach(badgeElement => {
        const cnSap = badgeElement.getAttribute('data-cn-sap');
        if (!cnSap) return;

        // Membuka koneksi WebSocket ke server Django untuk masing-masing CN_SAP
        const wsScheme = window.location.protocol === "https:" ? "wss" : "ws";
        const statusSocket = new WebSocket(`${wsScheme}://${window.location.host}/ws/status-asset/${cnSap}/`);

        statusSocket.onmessage = function(e) {
            const data = JSON.parse(e.data);
            
            // Jika status berubah, update tampilan badge secara mulus tanpa reload!
            if (data.status && data.status !== 'WAITING') {
                badgeElement.style.background = data.badge_bg;
                badgeElement.style.color = data.badge_color;
                badgeElement.innerText = data.status_text;
                
                // Halaman otomatis refresh bersih setelah status berubah (delay 1 detik)
                setTimeout(() => {
                    location.reload();
                }, 1000);
            }
        };

        statusSocket.onclose = function(e) {
            console.error(`WebSocket closed unexpectedly for asset ${cnSap}.`);
        };
    });
});