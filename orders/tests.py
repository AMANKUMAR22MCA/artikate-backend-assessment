from django.test import TestCase, Client
from django.db import connection, reset_queries
from django.test.utils import override_settings
from .models import Customer, Product, Order
import random


@override_settings(DEBUG=True)
class OrderSummaryQueryTest(TestCase):

    def setUp(self):
        random.seed(42)
        customers = [
            Customer.objects.create(name=f"Customer {i}", email=f"c{i}@test.com")
            for i in range(10)
        ]
        products = [
            Product.objects.create(name=f"Product {i}", price=10.00 * (i + 1))
            for i in range(3)
        ]
        for _ in range(200):
            Order.objects.create(
                customer=random.choice(customers),
                product=random.choice(products),
                quantity=random.randint(1, 5),
            )

    def test_broken_view_has_n_plus_1_queries(self):
        reset_queries()
        response = self.client.get('/api/orders/summary/broken/')
        query_count = len(connection.queries)
        print(f"\n[BROKEN] Query count: {query_count}")
        self.assertEqual(response.status_code, 200)
        self.assertGreater(query_count, 100)  # expect ~401

    def test_fixed_view_uses_minimal_queries(self):
        reset_queries()
        response = self.client.get('/api/orders/summary/')
        query_count = len(connection.queries)
        print(f"\n[FIXED]  Query count: {query_count}")
        self.assertEqual(response.status_code, 200)
        self.assertLess(query_count, 50)  # 1 real query + silk overhead

    def test_fixed_view_returns_correct_data(self):
        response = self.client.get('/api/orders/summary/')
        data = response.json()
        self.assertEqual(len(data['orders']), 200)
        first = data['orders'][0]
        for field in ['order_id', 'customer', 'product', 'quantity', 'status']:
            self.assertIn(field, first)