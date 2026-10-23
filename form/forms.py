from django import forms
from django.forms import ModelForm, inlineformset_factory
from .models import (
    FormPengajuanEquipmentDisposed, 
    FormLampiranCapex, 
    FormPengajuanDisposedSite, 
    FormRepairCostAnalisis, 
    FormFotoKonditionUnit,
    ChecksheetPI, 
    ChecksheetItem,
    CONDITION_CHOICES
)
from asset.models import AssetEquipmentDisposed, AssetEquipment

# ─── 1. FORM PENGAJUAN / UTILITY DISPOSED ─────────────────────────────────

class PengajuanEquipmentDisposedForm(forms.ModelForm):
    class Meta:
        model = FormPengajuanEquipmentDisposed
        exclude = ['diajukan_oleh', 'status', 'created_at', 'updated_at']

class PengajuanDisposedSiteForm(forms.ModelForm):
    class Meta:
        model = FormPengajuanDisposedSite
        exclude = ['diajukan_oleh', 'status', 'created_at', 'updated_at']

class RepairCostAnalisisForm(forms.ModelForm):
    class Meta:
        model = FormRepairCostAnalisis
        exclude = ['diajukan_oleh', 'status', 'created_at', 'updated_at']

class FotoKonditionUnitForm(forms.ModelForm):
    class Meta:
        model = FormFotoKonditionUnit
        exclude = ['diajukan_oleh', 'status', 'created_at', 'updated_at']


# ─── 2. FORM SELEKSI ASET (FIXED QUERYSET) ────────────────────────────────

class AssetSelectionForm(forms.Form):
    # Set queryset awal ke .none() untuk keamanan inisialisasi Django
    asset = forms.ModelChoiceField(
        queryset=AssetEquipmentDisposed.objects.none(),
        label="Pilih Aset (CN SAP)",
        to_field_name="CN_SAP" 
    )
    pic_inspector = forms.CharField(max_length=100, label="PIC Inspector")
    atasan_inspector = forms.CharField(max_length=100, label="Atasan Inspector")

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # ✅ Ambil data secara aman saat form dipanggil oleh view
        self.fields['asset'].queryset = AssetEquipmentDisposed.objects.all().order_by('asset__CN_SAP')
        self.fields['asset'].label_from_instance = lambda obj: f"{obj.CN_SAP}"


# ─── 3. CHECKSHEET FORM & FORMSET (DUPLIKASI DIHAPUS) ─────────────────────

class ChecksheetPIForm(ModelForm):
    """Form untuk Header Checksheet."""
    class Meta:
        model = ChecksheetPI
        fields = ['cn_sap', 'egi', 'hm_smr', 'pic_inspector', 'atasan_inspector']
        widgets = {
            'cn_sap': forms.TextInput(attrs={'readonly': 'readonly'}),
            'egi': forms.TextInput(attrs={'readonly': 'readonly'}),
            'hm_smr': forms.TextInput(attrs={'readonly': 'readonly'}),
            'pic_inspector': forms.TextInput(attrs={'readonly': 'readonly'}),
            'atasan_inspector': forms.TextInput(attrs={'readonly': 'readonly'}),
        }

class ChecksheetItemForm(ModelForm):
    """Form untuk satu baris Item Checksheet (Detail)."""
    condition = forms.ChoiceField(
        choices=CONDITION_CHOICES,
        widget=forms.RadioSelect, 
        required=True
    )
    class Meta:
        model = ChecksheetItem
        fields = ['category', 'item_name', 'qty', 'condition', 'remarks']
        widgets = {
            'category': forms.TextInput(attrs={'readonly': 'readonly'}),
            'item_name': forms.TextInput(attrs={'readonly': 'readonly'}),
            'qty': forms.TextInput(attrs={'readonly': 'readonly'}),
            'remarks': forms.Textarea(attrs={'rows': 2}),
        }

# Formset tunggal yang bersih
ChecksheetItemFormSet = inlineformset_factory(
    ChecksheetPI, 
    ChecksheetItem, 
    form=ChecksheetItemForm, 
    extra=0, 
    can_delete=False 
)


# ─── 4. LAMPIRAN CAPEX FORM ───────────────────────────────────────────────

class LampiranCapexForm(forms.ModelForm):
    class Meta:
        model = FormLampiranCapex
        exclude = [
            'diajukan_oleh', 'status', 'created_at',
            'updated_at', 'submitted_at', 'last_action_by',
        ]
        widgets = {
            'CN_SAP':         forms.HiddenInput(),
            'GROUP':          forms.HiddenInput(),
            'TYPE':           forms.HiddenInput(),
            'EGI':            forms.HiddenInput(),
            'HM_SMR':         forms.HiddenInput(),
            'SPO_EQUIPMENT':  forms.HiddenInput(),
            'PERSENTASE_SPO': forms.HiddenInput(),

            'NILAI_AKUISISI':           forms.NumberInput(attrs={'class': 'vTextField'}),
            'NBV':                      forms.NumberInput(attrs={'class': 'vTextField'}),
            'RV':                       forms.NumberInput(attrs={'class': 'vTextField'}),
            'NBV_STATUS':               forms.Select(attrs={'class': 'vTextField'}),
            'DATE_DELIVERY':            forms.DateInput(attrs={'class': 'vTextField', 'type': 'date'}),
            'LIFE_EQUIPMENT':           forms.NumberInput(attrs={'class': 'vTextField'}),
            'STANDAR_DEPRE_EQUIPMENT':  forms.NumberInput(attrs={'class': 'vTextField'}),
            'REPLACEMENT':              forms.TextInput(attrs={'class': 'vTextField'}),
            'KONDISI_BODY':             forms.TextInput(attrs={'class': 'vTextField'}),
            'KONDISI_FRAME':            forms.TextInput(attrs={'class': 'vTextField'}),
            'KONDISI_KOMKOMPONEN':       forms.TextInput(attrs={'class': 'vTextField'}),
            'PROSENTASE_LIFE_COMP_SPO': forms.NumberInput(attrs={'class': 'vTextField'}),
            'COST_REPAIR':              forms.NumberInput(attrs={'class': 'vTextField'}),
            'HARGA_NEW':                forms.NumberInput(attrs={'class': 'vTextField'}),
            'NILAI_SISA_COMP':          forms.NumberInput(attrs={'class': 'vTextField'}),
            'OBSOLETE':                 forms.Textarea(attrs={'rows': 3, 'class': 'vLargeTextField'}),
        }

    def __init__(self, *args, **kwargs):
        initial_cn_sap = kwargs.pop('initial_cn_sap', None)
        super().__init__(*args, **kwargs)

        if initial_cn_sap:
            self.fields['CN_SAP'].initial = initial_cn_sap