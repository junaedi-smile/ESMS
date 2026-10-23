from .models import AssetEquipment
from django import forms
from .models import AssetMonthlyStatus


class AssetEquipmentForm(forms.ModelForm):  # perbaikan nama class
    class Meta:
        model = AssetEquipment
        fields = [  # perbaikan dari 'field' ke 'fields'
            "No_Asset", "CN_SAP", "CN_ELLIPSE", "EGI", "FOTO", "TYPE", "GROUP",
            "OWNERSHIP", "LOCATION", "SUB_SITE", "BRAND", "SN", "HM_SMR",
            "HM_DATE", "SPO_EQUIPMENT", "PERSENTASE_SPO", "EQUIPMENT_CONDITION",
            "STATUS_EQUIPMENT", "STATUS_EQUIPMENT_DISPOSED", "REFERENSI_NO_PDE"
        ]

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # Tambahan opsional: Styling untuk semua field
        for field in self.fields.values():
            field.widget.attrs['class'] = 'form-control'

class AssetMonthlyStatusForm(forms.ModelForm):
    class Meta:
        model = AssetMonthlyStatus
        fields = ['No_Asset', 'MONTH', 'YEAR', 'STATUS_EQUIPMENT', 'HM_SMR', 'LOCATION']

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        for field in self.fields.values():
            field.widget.attrs['class'] = 'form-control'

