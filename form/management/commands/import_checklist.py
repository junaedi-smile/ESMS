# form/management/commands/import_checklist.py

import pandas as pd
from django.core.management.base import BaseCommand
from django.conf import settings
import os
from form.models import InspectionItem

class Command(BaseCommand):
    help = 'Import checklist items from Excel into InspectionItem'

    def handle(self, *args, **kwargs):
        # Tentukan path file relatif ke BASE_DIR
        file_path = os.path.join(settings.BASE_DIR, "data", "checklist_HD785-7.xlsx")

        if not os.path.exists(file_path):
            self.stdout.write(self.style.ERROR(f"File tidak ditemukan: {file_path}"))
            return

        df = pd.read_excel(file_path)

        # Asumsi kolom di Excel: Section, Item, Standard, EGI
        for _, row in df.iterrows():
            InspectionItem.objects.create(
                egi=row.get("egi", "egi"),
                category=row.get("category", "category"),
                name=row.get("name", "name"),
                order=row.get("order", "order"),
            )

        self.stdout.write(self.style.SUCCESS("Checklist berhasil diimport"))
