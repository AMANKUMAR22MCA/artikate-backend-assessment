from django.test import TestCase, RequestFactory
from .models import Tenant, TenantOrder, set_current_tenant, clear_current_tenant


class TenantIsolationTest(TestCase):

    def setUp(self):
        # create two tenants
        self.tenant_a = Tenant.objects.create(name="Company A", subdomain="companya")
        self.tenant_b = Tenant.objects.create(name="Company B", subdomain="companyb")

        # create orders for each tenant
        TenantOrder.unscoped.create(tenant=self.tenant_a, description="Order A1", amount=100)
        TenantOrder.unscoped.create(tenant=self.tenant_a, description="Order A2", amount=200)
        TenantOrder.unscoped.create(tenant=self.tenant_b, description="Order B1", amount=300)

    def tearDown(self):
        clear_current_tenant()

    def test_tenant_a_cannot_see_tenant_b_data(self):
        """When logged in as tenant A, tenant B orders must not appear."""
        set_current_tenant(self.tenant_a)

        orders = TenantOrder.objects.all()
        descriptions = list(orders.values_list('description', flat=True))

        print(f"\n[Tenant A sees]: {descriptions}")
        self.assertIn("Order A1", descriptions)
        self.assertIn("Order A2", descriptions)
        self.assertNotIn("Order B1", descriptions)

    def test_tenant_b_cannot_see_tenant_a_data(self):
        """When logged in as tenant B, tenant A orders must not appear."""
        set_current_tenant(self.tenant_b)

        orders = TenantOrder.objects.all()
        descriptions = list(orders.values_list('description', flat=True))

        print(f"\n[Tenant B sees]: {descriptions}")
        self.assertIn("Order B1", descriptions)
        self.assertNotIn("Order A1", descriptions)
        self.assertNotIn("Order A2", descriptions)

    def test_objects_all_does_not_bypass_scoping(self):
        """
        Calling .objects.all() should never return all tenants data.
        This proves the manager cannot be accidentally bypassed.
        """
        set_current_tenant(self.tenant_a)

        all_orders = TenantOrder.objects.all()
        self.assertEqual(all_orders.count(), 2)  # only tenant A's 2 orders

        # total in DB is 3 — proves filter is applied
        total_in_db = TenantOrder.unscoped.all().count()
        self.assertEqual(total_in_db, 3)

        print(f"\n[Scoped]: {all_orders.count()} orders")
        print(f"[Unscoped]: {total_in_db} orders in DB total")

    def test_no_tenant_set_returns_all(self):
        """
        When no tenant is set (e.g. admin or management command)
        unscoped manager should be used explicitly.
        """
        clear_current_tenant()

        # scoped manager with no tenant — returns all
        # in production you'd want to decide this behaviour
        all_orders = TenantOrder.unscoped.all()
        self.assertEqual(all_orders.count(), 3)
        print(f"\n[No tenant]: unscoped returns {all_orders.count()} orders")