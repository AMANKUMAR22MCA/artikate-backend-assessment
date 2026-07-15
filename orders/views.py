from django.http import JsonResponse
from .models import Order


# BROKEN VIEW — N+1 Query Problem
# For 200 orders: 1 + 200 + 200 = 401 queries → timeout
def orders_summary_broken(request):
    orders = Order.objects.all()  # Query 1: fetch orders only

    data = []
    for order in orders:
        data.append({
            "order_id": order.id,
            "customer": order.customer.name,  # hits DB once per order
            "product": order.product.name,    # hits DB once per order
            "quantity": order.quantity,
            "status": order.status,
        })

    return JsonResponse({"orders": data})


# FIXED VIEW — select_related does a SQL JOIN
# All data fetched in 1 query regardless of order count
def orders_summary_fixed(request):
    orders = Order.objects.select_related('customer', 'product').all()

    data = []
    for order in orders:
        data.append({
            "order_id": order.id,
            "customer": order.customer.name,  # already in memory, no DB hit
            "product": order.product.name,    # already in memory, no DB hit
            "quantity": order.quantity,
            "status": order.status,
        })

    return JsonResponse({"orders": data})