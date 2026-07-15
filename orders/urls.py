from django.urls import path
from . import views

urlpatterns = [
    path('api/orders/summary/broken/', views.orders_summary_broken),
    path('api/orders/summary/', views.orders_summary_fixed),
]