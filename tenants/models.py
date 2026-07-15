from django.db import models
import threading

# thread local storage — holds current tenant per request
_thread_locals = threading.local()


def get_current_tenant():
    return getattr(_thread_locals, 'tenant', None)


def set_current_tenant(tenant):
    _thread_locals.tenant = tenant


def clear_current_tenant():
    _thread_locals.tenant = None


class Tenant(models.Model):
    name = models.CharField(max_length=255)
    subdomain = models.CharField(max_length=100, unique=True)

    def __str__(self):
        return self.name


class TenantManager(models.Manager):
    def get_queryset(self):
        tenant = get_current_tenant()
        qs = super().get_queryset()
        if tenant is not None:
            return qs.filter(tenant=tenant)
        return qs


class TenantOrder(models.Model):
    tenant = models.ForeignKey(Tenant, on_delete=models.CASCADE)
    description = models.CharField(max_length=255)
    amount = models.DecimalField(max_digits=10, decimal_places=2)

    # scoped manager — always filters by current tenant
    objects = TenantManager()

    # unscoped manager — only use when you explicitly need all tenants
    unscoped = models.Manager()

    def __str__(self):
        return f"{self.tenant.name} - {self.description}"