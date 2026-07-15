# 🛠️ Artikate Backend Assessment

> Python · Django · Redis · Celery · Systems Engineering

---

## ⚡ Quick Start

```bash
# Clone
git clone https://github.com/AMANKUMAR22MCA/artikate-backend-assessment.git
cd artikate-backend-assessment

# Setup
python -m venv venv
venv\Scripts\activate        # Windows
pip install -r requirements.txt

# Start Redis
docker run -d --name redis-assessment -p 6379:6379 redis

# Run
python manage.py migrate
python manage.py runserver
```

---

## 🧪 Run All Tests

```bash
python manage.py test --verbosity=2
```

| Section | Command | Result |
|---|---|---|
| Section 1 | `python manage.py test orders` | ✅ 3 tests |
| Section 2 | `python manage.py test emails` | ✅ 3 tests |
| Section 3 | `python manage.py test tenants` | ✅ 4 tests |

---

## 📂 Project Structure
