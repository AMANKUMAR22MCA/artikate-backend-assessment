from .models import Tenant, set_current_tenant, clear_current_tenant


class TenantMiddleware:
    """
    Extracts tenant from subdomain or request header.
    Sets it for the full request lifecycle then cleans up.
    
    Example:
    companya.localhost → tenant = Company A
    Header X-Tenant-ID: 1 → tenant with id=1
    """
    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        tenant = None

        # Option 1 — get tenant from header (easier for testing)
        tenant_id = request.headers.get('X-Tenant-ID')
        if tenant_id:
            try:
                tenant = Tenant.objects.get(id=tenant_id)
            except Tenant.DoesNotExist:
                pass

        # Option 2 — get tenant from subdomain
        if tenant is None:
            host = request.get_host().split(':')[0]  # remove port
            subdomain = host.split('.')[0]
            if subdomain not in ('localhost', 'www', '127'):
                try:
                    tenant = Tenant.objects.get(subdomain=subdomain)
                except Tenant.DoesNotExist:
                    pass

        # set tenant for this request
        set_current_tenant(tenant)

        try:
            response = self.get_response(request)
        finally:
            # always clean up — critical so tenant doesn't leak
            # into next request on same thread
            clear_current_tenant()

        return response