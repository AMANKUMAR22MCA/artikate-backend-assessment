# 🛠️ Artikate Backend Assessment

> Python · Django · Redis · Celery · Systems Engineering

![Python](https://img.shields.io/badge/Python-3.11-blue?style=flat-square)
![Django](https://img.shields.io/badge/Django-5.2.16-green?style=flat-square)
![Celery](https://img.shields.io/badge/Celery-5.6.3-brightgreen?style=flat-square)
![Redis](https://img.shields.io/badge/Redis-8.0.1-red?style=flat-square)
![Docker](https://img.shields.io/badge/Docker-required-blue?style=flat-square)

---

## ⚡ Quick Start

```bash
# 1. Clone
git clone https://github.com/AMANKUMAR22MCA/artikate-backend-assessment.git
cd artikate-backend-assessment

# 2. Virtual environment
python -m venv venv
venv\Scripts\activate        # Windows
source venv/bin/activate     # Mac/Linux

# 3. Install dependencies
pip install -r requirements.txt

# 4. Start Redis
docker run -d --name redis-assessment -p 6379:6379 redis

# 5. Run
python manage.py migrate
python manage.py runserver
```

---

## 🧪 Run All Tests

```bash
python manage.py test --verbosity=2
```

| Section | Command | Tests |
|---------|---------|-------|
| Section 1 — N+1 Fix | `python manage.py test orders` | ✅ 3 passed |
| Section 2 — Job Queue | `python manage.py test emails` | ✅ 3 passed |
| Section 3 — Tenant Isolation | `python manage.py test tenants` | ✅ 4 passed |

---

## 📂 Project Structure

```
artikate-backend-assessment/
│
├── 📁 orders/                  # Section 1 — N+1 Query Fix
│   ├── models.py               # Customer, Product, Order
│   ├── views.py                # broken + fixed views
│   └── tests.py                # query count assertions
│
├── 📁 emails/                  # Section 2 — Async Job Queue
│   ├── tasks.py                # Celery task + Redis rate limiter
│   └── tests.py                # 500 jobs, rate limit, retry tests
│
├── 📁 tenants/                 # Section 3 — Multi Tenant Isolation
│   ├── models.py               # TenantManager + thread locals
│   ├── middleware.py           # auto tenant scoping per request
│   └── tests.py                # isolation + bypass prevention tests
│
├── 📁 artikate_project/        # Django project
│   ├── settings.py
│   ├── celery.py               # Celery config
│   └── urls.py
│
├── 📁 screenshots/             # Profiler evidence
│   ├── silk_comparison.png     # 501 queries → 1 query
│   └── celery_worker_live.png  # worker processing jobs live
│
├── 📄 DESIGN.md                # Section 2 architecture decisions
├── 📄 ANSWERS.md               # Written answers all sections
└── 📄 requirements.txt
```

---

## 🔍 Section 1 — N+1 Query Fix

Endpoint `/api/orders/summary/` was timing out for users with 200+ orders.
Root cause: Django lazy loading fired a separate SQL query per order for
`customer` and `product`. Fixed with `select_related`.

| Endpoint | Queries | Response Time |
|----------|---------|---------------|
| `/api/orders/summary/broken/` | 501 ❌ | 4021ms |
| `/api/orders/summary/` | 1 ✅ | 77ms |

**Seed DB and see it live:**

```bash
python manage.py shell
```

```python
from orders.models import Customer, Product, Order
import random

customers = [Customer.objects.create(name=f"Customer {i}", email=f"c{i}@test.com") for i in range(5)]
products = [Product.objects.create(name=f"Product {i}", price=10.00*(i+1)) for i in range(3)]
for i in range(250):
    Order.objects.create(
        customer=random.choice(customers),
        product=random.choice(products),
        quantity=random.randint(1, 5),
    )
```

> 📊 Silk dashboard → `http://127.0.0.1:8000/silk/`

---

## 📬 Section 2 — Async Job Queue

Handles 2000 email requests in 10 seconds while respecting 200 emails/minute provider limit. Built with Celery + Redis sliding window rate limiter.

**Run it live — open 2 terminals:**

```bash
# Terminal 1 — start worker
celery -A artikate_project worker --loglevel=info -P solo
```

```bash
# Terminal 2 — submit jobs
python manage.py shell
```

```python
from emails.tasks import send_email_task

for i in range(10):
    send_email_task.apply_async(
        args=[f"user{i}@test.com", "Order Confirmed", "Hello!"]
    )
```

Watch Terminal 1 — jobs processed in real time with retries and rate limiting.

---

## 🏢 Section 3 — Multi Tenant Isolation

Automatic tenant scoping at ORM level. Even if a developer writes
`TenantOrder.objects.all()` the manager silently adds
`.filter(tenant=current_tenant)`. Impossible to accidentally bypass.

```python
# developer writes this
orders = TenantOrder.objects.all()

# ORM silently does this
orders = TenantOrder.objects.filter(tenant=current_tenant)
```

Tenant extracted from `X-Tenant-ID` header or subdomain via middleware.

---

## 📸 Profiler Evidence

| Screenshot | What it shows |
|------------|---------------|
| `screenshots/silk_comparison.png` | 501 queries → 1 query |
| `screenshots/celery_worker_live.png` | Worker processing jobs in real time |

---

## 📄 Written Answers

All written answers in `ANSWERS.md`:

- **Section 1** — Investigation log, root cause, fix explanation
- **Section 2** — SIGKILL answer, test results
- **Section 3** — Async failure modes, contextvars explanation
- **Section 4** — Django admin performance, pagination trade-offs

---

> Built as part of Artikate Studio Backend Developer Assessment
