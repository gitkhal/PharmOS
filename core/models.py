from datetime import timedelta

from django.db import models
from django.utils import timezone


class Medicine(models.Model):
    name = models.CharField(max_length=120)
    barcode = models.CharField(max_length=50, unique=True)
    quantity = models.PositiveIntegerField(default=0)
    price = models.DecimalField(max_digits=8, decimal_places=2)
    batch_number = models.CharField(max_length=50)
    expiry_date = models.DateField()
    low_stock_threshold = models.PositiveIntegerField(default=10)

    @property
    def is_low_stock(self):
        return self.quantity <= self.low_stock_threshold

    @property
    def is_near_expiry(self):
        today = timezone.localdate()
        return today <= self.expiry_date <= today + timedelta(days=60)

    def __str__(self):
        return self.name


class Sale(models.Model):
    created_at = models.DateTimeField(auto_now_add=True)
    total = models.DecimalField(max_digits=10, decimal_places=2, default=0)

    def __str__(self):
        return f"Sale #{self.id}"


class SaleItem(models.Model):
    sale = models.ForeignKey(
        Sale,
        related_name="items",
        on_delete=models.CASCADE,
    )
    medicine = models.ForeignKey(
        Medicine,
        on_delete=models.PROTECT,
    )
    quantity = models.PositiveIntegerField()
    unit_price = models.DecimalField(max_digits=8, decimal_places=2)

    def __str__(self):
        return f"{self.quantity} × {self.medicine.name}"