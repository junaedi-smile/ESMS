import os
import django
import csv

# Setup Django
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "inside.settings")
django.setup()

from asset_tracking.models import tracking

def run():
    csv_path = "FOTO_UEA_2025_update.csv"  # Pastikan file ini berada di folder project
    with open(csv_path, newline='', encoding='utf-8') as csvfile:
        reader = csv.reader(csvfile)
        next(reader) 
        for row in reader:
            cn_sap = row[0].strip()
            pos_x = int(row[1])
            pos_y = int(row[2])

            # Update atau buat record baru
            obj, created = tracking.objects.update_or_create(
                CN_SAP=cn_sap,
                defaults={
                    'POS_X': pos_x,
                    'POS_Y': pos_y
                }
            )
            print(f"{'Created' if created else 'Updated'}: {cn_sap} (X: {pos_x}, Y: {pos_y})")

if __name__ == "__main__":
    run()
