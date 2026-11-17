from django import forms
from .models import Medicine


class MedicineForm(forms.ModelForm):
    class Meta:
        model = Medicine

        fields = [
            "name",
            "barcode",
            "quantity",
            "price",
            "batch_number",
            "expiry_date",
            "low_stock_threshold",
        ]

        widgets = {
            "expiry_date": forms.DateInput(attrs={"type": "date"}),
        }