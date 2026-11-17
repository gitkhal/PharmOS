from datetime import timedelta
from decimal import Decimal

from django.contrib import messages
from django.db import transaction
from django.db.models import F, Q
from django.shortcuts import redirect, render
from django.utils import timezone

from .forms import MedicineForm
from .models import Medicine, Sale, SaleItem


def dashboard(request):
    today = timezone.localdate()

    low_stock = Medicine.objects.filter(
        quantity__lte=F("low_stock_threshold")
    ).order_by("quantity")

    near_expiry = Medicine.objects.filter(
        expiry_date__gte=today,
        expiry_date__lte=today + timedelta(days=60),
    ).order_by("expiry_date")

    recent_sales = Sale.objects.order_by("-created_at")[:5]

    return render(
        request,
        "core/dashboard.html",
        {
            "medicine_count": Medicine.objects.count(),
            "low_stock": low_stock,
            "near_expiry": near_expiry,
            "recent_sales": recent_sales,
        },
    )


def inventory(request):
    medicines = Medicine.objects.all().order_by("name")

    query = request.GET.get("q", "").strip()
    filter_type = request.GET.get("filter", "")

    if query:
        medicines = medicines.filter(
            Q(name__icontains=query)
            | Q(barcode__icontains=query)
            | Q(batch_number__icontains=query)
        )

    if filter_type == "low":
        medicines = medicines.filter(
            quantity__lte=F("low_stock_threshold")
        )

    elif filter_type == "expiry":
        today = timezone.localdate()

        medicines = medicines.filter(
            expiry_date__gte=today,
            expiry_date__lte=today + timedelta(days=60),
        )

    return render(
        request,
        "core/inventory.html",
        {
            "medicines": medicines,
            "query": query,
        },
    )


def medicine_add(request):
    if request.method == "POST":
        form = MedicineForm(request.POST)

        if form.is_valid():
            medicine = form.save()

            messages.success(
                request,
                f"{medicine.name} added to inventory.",
            )

            return redirect("inventory")

    else:
        form = MedicineForm()

    return render(
        request,
        "core/medicine_form.html",
        {"form": form},
    )


def pos(request):
    cart = request.session.get("cart", {})

    if request.method == "POST":
        action = request.POST.get("action")

        if action == "add":
            search = request.POST.get("search", "").strip()

            try:
                quantity = int(request.POST.get("quantity", 1))
            except ValueError:
                quantity = 0

            medicine = Medicine.objects.filter(barcode=search).first()

            if medicine is None:
                medicine = Medicine.objects.filter(
                    name__icontains=search
                ).first()

            if medicine is None:
                messages.error(request, "Medicine not found.")

            elif quantity <= 0:
                messages.error(request, "Quantity must be at least 1.")

            else:
                current_quantity = int(
                    cart.get(str(medicine.id), 0)
                )

                if current_quantity + quantity > medicine.quantity:
                    messages.error(
                        request,
                        f"Only {medicine.quantity} units available.",
                    )
                else:
                    cart[str(medicine.id)] = current_quantity + quantity

                    request.session["cart"] = cart
                    request.session.modified = True

            return redirect("pos")

        if action == "remove":
            medicine_id = request.POST.get("medicine_id")

            cart.pop(str(medicine_id), None)

            request.session["cart"] = cart
            request.session.modified = True

            return redirect("pos")

        if action == "clear":
            request.session["cart"] = {}
            return redirect("pos")

        if action == "complete":
            if not cart:
                messages.error(request, "The sale is empty.")
                return redirect("pos")

            try:
                with transaction.atomic():
                    sale = Sale.objects.create(total=0)
                    total = Decimal("0")

                    for medicine_id, quantity in cart.items():
                        medicine = (
                            Medicine.objects
                            .select_for_update()
                            .get(pk=int(medicine_id))
                        )

                        quantity = int(quantity)

                        if medicine.quantity < quantity:
                            raise ValueError(
                                f"Not enough stock for {medicine.name}."
                            )

                        SaleItem.objects.create(
                            sale=sale,
                            medicine=medicine,
                            quantity=quantity,
                            unit_price=medicine.price,
                        )

                        medicine.quantity -= quantity
                        medicine.save(update_fields=["quantity"])

                        total += medicine.price * quantity

                    sale.total = total
                    sale.save(update_fields=["total"])

                request.session["cart"] = {}

                messages.success(
                    request,
                    f"Sale #{sale.id} completed. "
                    f"Total: ${sale.total:.2f}. "
                    f"Inventory updated.",
                )

            except (Medicine.DoesNotExist, ValueError) as error:
                messages.error(request, str(error))

            return redirect("pos")

    cart_rows = []
    total = Decimal("0")

    for medicine_id, quantity in cart.items():
        medicine = Medicine.objects.filter(
            pk=int(medicine_id)
        ).first()

        if medicine:
            quantity = int(quantity)
            subtotal = medicine.price * quantity

            cart_rows.append(
                {
                    "medicine": medicine,
                    "quantity": quantity,
                    "subtotal": subtotal,
                }
            )

            total += subtotal

    return render(
        request,
        "core/pos.html",
        {
            "cart_rows": cart_rows,
            "total": total,
        },
    )