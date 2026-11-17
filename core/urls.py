from django.urls import path
from . import views


urlpatterns = [
    path("", views.dashboard, name="dashboard"),
    path("inventory/", views.inventory, name="inventory"),
    path("inventory/add/", views.medicine_add, name="medicine_add"),
    path("pos/", views.pos, name="pos"),
]