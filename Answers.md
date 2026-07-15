# ANSWERS.md

## Section 1 — Diagnose a Broken System

### Deliverable 1 — Investigation Log

So first thing I did was check if something changed on the infrastructure side —
server memory, CPU, anything like that. Nothing changed there so I moved on.

Then I checked if any migration ran during deployment that could have messed up
an index or changed a table structure. Nothing there either.

Then I actually looked at the view. It was doing Order.objects.all() and then
looping through every order and accessing order.customer.name and
order.product.name inside the loop. That's when it clicked — Django doesn't
fetch related objects automatically. It waits until you actually touch them.
So every time the loop hits order.customer it fires a fresh SQL query. Same for
order.product. With 250 orders that's 501 queries total.

The reason it wasn't showing before is probably because the data was small
earlier. Maybe 20-30 orders. At that size 60 queries is fast enough you don't
notice. But once real users started placing orders and the count crossed 200,
the query count exploded and the timeout started hitting.

---

### Deliverable 2 — Root Cause

N+1 query problem.

Django ORM lazy loads related objects by default. When you call
Order.objects.all() it only fetches the orders table. The moment you access
order.customer inside a loop, Django fires a separate SELECT for that customer.
Same for order.product. So for 250 orders you get:

1 query for orders + 250 for customers + 250 for products = 501 queries

No code change was needed to cause this. The view was always broken, the data
just wasn't big enough to show it before.

---

### Deliverable 3 — Broken View

```python
def orders_summary_broken(request):
    orders = Order.objects.all()  # only fetches orders table

    data = []
    for order in orders:
        data.append({
            "order_id": order.id,
            "customer": order.customer.name,  # separate DB query per order
            "product": order.product.name,    # separate DB query per order
            "quantity": order.quantity,
            "status": order.status,
        })

    return JsonResponse({"orders": data})
```

---

### Deliverable 4 — Fix and Why It Works

```python
def orders_summary_fixed(request):
    orders = Order.objects.select_related('customer', 'product').all()

    data = []
    for order in orders:
        data.append({
            "order_id": order.id,
            "customer": order.customer.name,  # reading from RAM, no DB hit
            "product": order.product.name,    # reading from RAM, no DB hit
            "quantity": order.quantity,
            "status": order.status,
        })

    return JsonResponse({"orders": data})
```

select_related tells Django to do a SQL JOIN instead of lazy loading. So the
actual query that runs looks like this:

SELECT orders.*, customers.*, products.*
FROM orders
JOIN customers ON orders.customer_id = customers.id
JOIN products ON orders.product_id = products.id

Everything comes back in one round trip. Django stores it all in Python objects
in RAM. So when the loop accesses order.customer.name it's just reading a
variable — not touching the database at all.

I used select_related here because customer and product are ForeignKey
relations. If they were ManyToMany or reverse FK I would have used
prefetch_related instead, which does 1 query per relation rather than a JOIN.

---

### Deliverable 5 — Profiler Evidence (django-silk)

Ran both endpoints and checked silk at /silk/

Before fix — /api/orders/summary/broken/
- Queries: 501
- Time on DB: 689ms
- Total response time: 4021ms

After fix — /api/orders/summary/
- Queries: 1
- Time on DB: 3ms
- Total response time: 77ms

501 queries down to 1. Response went from 4 seconds to 77ms. The silk
screenshot is included in the repo under /screenshots/silk_comparison.png


## Section 2 — Async Job Queue

### What happens if Celery worker is SIGKILL'd mid-task?

By default Celery acknowledges a task the moment it picks it up from
Redis. So if the worker is killed after receiving but before finishing,
the task is gone permanently.

We fixed this with acks_late=True. This tells Celery to only
acknowledge the task after it completes. So if the worker dies mid-task,
Redis still sees it as unacknowledged and redelivers it to another
worker.

We also added reject_on_worker_lost=True so the task goes back to the
queue immediately rather than waiting for a visibility timeout.

And CELERY_WORKER_PREFETCH_MULTIPLIER=1 so each worker holds only one
task at a time. Without this a worker could prefetch 4 tasks, get
killed, and lose all 4 even with acks_late=True.

### Test results

- 500 jobs submitted — all accepted into queue, none lost
- Rate limiter — exactly 200 allowed, 100 blocked out of 300 attempts
- Failed task retried 3 times with exponential backoff (2s, 4s, 8s)
  then moved to dead letter queue
- Worker ran live and processed jobs in real time — see
  screenshots/celery_worker_live.png
  

## Section 3 — Multi-Tenant Isolation

### Failure modes of thread-local tenant scoping in async views

Thread locals work by storing data per thread. In sync Django each
request gets its own thread so tenant never leaks between requests.

In async Django multiple coroutines run on the same thread. So if
request A sets the tenant then hits an await, the thread is free to
pick up request B which overwrites the tenant. When request A resumes
it's now running with the wrong tenant. That's a data leak.

The fix is Python's contextvars module. Instead of threading.local()
you use a ContextVar which is automatically scoped per coroutine not
per thread. Even when two coroutines share a thread they each have
their own context so the tenant never crosses over.

Change would be:

# instead of this
_thread_locals = threading.local()

# use this
from contextvars import ContextVar
_current_tenant = ContextVar('current_tenant', default=None)

# set it
_current_tenant.set(tenant)

# get it
_current_tenant.get()

This works safely in both sync and async views so it's the better
default even if you're not using async yet.  