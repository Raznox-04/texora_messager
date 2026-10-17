# تکسورا (Texora)

پلتفرم پیام‌رسان فارسی با نظارت هوشمند هوش مصنوعی (Gemini 2.5 Flash از طریق درگاه آروان‌کلاد).

## پیش‌نیازها

- Python 3.11 یا بالاتر
- PostgreSQL 14 یا بالاتر
- Linux / Windows / macOS

## نصب

### ۱. PostgreSQL

**Ubuntu/Debian:**
```bash
sudo apt install -y postgresql postgresql-contrib
sudo -u postgres psql -c "CREATE USER texora_user WITH PASSWORD 'texora_pass';"
sudo -u postgres psql -c "CREATE DATABASE texora_db OWNER texora_user;"
```

**Windows:** از [postgresql.org](https://www.postgresql.org/download/windows/) نصب کنید.

### ۲. محیط مجازی

```bash
python -m venv .venv
source .venv/bin/activate          # Linux
.venv\Scripts\activate             # Windows
```

### ۳. نصب وابستگی‌ها

```bash
pip install -r requirements.txt
```

### ۴. تنظیم `.env`

```bash
cp .env.example .env
# SECRET_KEY را تصادفی کنید
```

### ۵. Migration

```bash
alembic upgrade head
```

### ۶. مدیر

```bash
python -m scripts.create_admin --username admin --email admin@example.com --password "AdminPass123"
```

### ۷. اجرا

```bash
uvicorn app.main:app --reload
```

مرورگر: **http://localhost:8000**

## تست

```bash
pytest app/tests -v
```

## نکات امنیتی

- کلید API آروان‌کلاد فقط سمت سرور.
- `SECRET_KEY` تصادفی و امن.
- در تولید از HTTPS استفاده کنید.

## مجوز

پروژه تکسورا — تمامی حقوق محفوظ است.