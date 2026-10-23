document.addEventListener('DOMContentLoaded', function() {
    // Menangkap ID field input bawaan Django Admin Django Form
    const lokasiField = document.querySelector('#id_userprofile-0-lokasi');
    const sectionField = document.querySelector('#id_userprofile-0-section');

    const mapping = {
        'ADMO': [
            'MINING - PDW', 'MINING - PHW', 'MINING - PLD', 'MINING - PSU',
            'HAULING - KLANIS', 'HAULING - PFT', 'HAULING - PPM', 'HAULING - PTS', 'HAULING - PVE'
        ],
        'SERA': ['PLANT-SERA'],
        'MACO': ['MACO - HAULING', 'MACO - MINING']
    };

    if (lokasiField && sectionField) {
        lokasiField.addEventListener('change', function() {
            const selectedLokasi = this.value;
            sectionField.innerHTML = '<option value="">---------</option>';
            
            if (mapping[selectedLokasi]) {
                mapping[selectedLokasi].forEach(function(sec) {
                    const opt = document.createElement('option');
                    opt.value = sec;
                    opt.innerHTML = sec;
                    sectionField.appendChild(opt);
                });
            }
        });
    }
});