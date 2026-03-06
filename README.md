# 🏥 صيدلية الحلول العالمية — دليل التثبيت والتشغيل الكامل

## 📋 البنية التقنية

```
┌─────────────────────────────────────────────────────┐
│                   المستخدمون                         │
│  (متصفح / جوال / جهاز لوحي)                         │
└─────────────────┬───────────────────────────────────┘
                  │ HTTPS
┌─────────────────▼───────────────────────────────────┐
│              Nginx (Reverse Proxy)                   │
│  • SSL/TLS تشفير                                     │
│  • Rate limiting حماية من الهجمات                   │
│  • ضغط الملفات                                      │
└────────┬──────────────────────┬────────────────────-┘
         │                      │
┌────────▼────────┐    ┌────────▼────────┐
│  React Frontend │    │  FastAPI Backend│
│  (الواجهة)      │    │  (الخادم)       │
└─────────────────┘    └────────┬────────┘
                                │
                    ┌───────────▼──────────┐
                    │   PostgreSQL         │
                    │   (قاعدة البيانات)  │
                    └──────────────────────┘
```

---

## 🖥️ متطلبات الخادم

| المكون | الحد الأدنى | الموصى به |
|--------|------------|-----------|
| CPU | 2 cores | 4 cores |
| RAM | 2 GB | 4 GB |
| Storage | 20 GB | 50 GB SSD |
| OS | Ubuntu 20.04+ / Windows Server | Ubuntu 22.04 LTS |

---

## 🚀 خطوات التثبيت

### الخطوة 1 — تثبيت Docker

**على Ubuntu/Linux:**
```bash
# تثبيت Docker
curl -fsSL https://get.docker.com -o get-docker.sh
sudo sh get-docker.sh

# تثبيت Docker Compose
sudo apt install docker-compose-plugin -y

# تشغيل Docker عند الإقلاع
sudo systemctl enable docker
sudo systemctl start docker

# إضافة المستخدم لمجموعة docker (لتجنب sudo)
sudo usermod -aG docker $USER
newgrp docker
```

**على Windows:**
- حمّل [Docker Desktop](https://www.docker.com/products/docker-desktop/)
- ثبّته وشغّله
- افتح PowerShell أو CMD

---

### الخطوة 2 — إعداد الملفات

```bash
# انسخ المشروع إلى جهازك
cd pharmacy_pro

# انسخ ملف الإعدادات
cp .env.example .env

# عدّل الإعدادات (مهم جداً!)
nano .env   # أو notepad .env على Windows
```

**الإعدادات الإلزامية في .env:**
```env
POSTGRES_PASSWORD=كلمة_مرور_قوية_هنا_123
SECRET_KEY=سلسلة_عشوائية_طويلة_64_حرف_على_الأقل
ALLOWED_ORIGINS=https://نطاقك.com,http://localhost
```

---

### الخطوة 3 — تشغيل النظام

```bash
# بناء وتشغيل جميع الخدمات
docker compose up -d --build

# مراقبة السجلات
docker compose logs -f

# التحقق من حالة الخدمات
docker compose ps
```

**النتيجة المتوقعة:**
```
NAME                 STATUS
pharmacy_db          running (healthy)
pharmacy_backend     running
pharmacy_frontend    running
pharmacy_nginx       running
pharmacy_backup      running
```

---

### الخطوة 4 — الوصول للنظام

| الوصول | الرابط |
|--------|--------|
| **شبكة محلية (LAN)** | `http://IP_الجهاز:8080` |
| **عن بُعد (HTTPS)** | `https://pharmacy.yourdomain.com` |
| **API Documentation** | `http://IP:8000/api/docs` |

---

## 🌐 إعداد الوصول عن بُعد

### الخيار 1: استخدام Cloudflare Tunnel (مجاني وسهل) ⭐

```bash
# تثبيت cloudflared
curl -L https://github.com/cloudflare/cloudflared/releases/latest/download/cloudflared-linux-amd64 -o cloudflared
chmod +x cloudflared
sudo mv cloudflared /usr/local/bin/

# تسجيل الدخول
cloudflared tunnel login

# إنشاء نفق
cloudflared tunnel create pharmacy

# تشغيل النفق
cloudflared tunnel --url http://localhost:8080 run pharmacy
```
✅ ستحصل على رابط مجاني مثل: `https://pharmacy-abc123.trycloudflare.com`

---

### الخيار 2: نطاق خاص مع Let's Encrypt SSL

```bash
# تثبيت Certbot
sudo apt install certbot -y

# الحصول على شهادة SSL مجانية
sudo certbot certonly --standalone -d pharmacy.yourdomain.com

# نسخ الشهادات
sudo cp /etc/letsencrypt/live/pharmacy.yourdomain.com/fullchain.pem ./nginx/ssl/
sudo cp /etc/letsencrypt/live/pharmacy.yourdomain.com/privkey.pem ./nginx/ssl/

# تحديث nginx.conf باسم النطاق
sed -i 's/pharmacy.yourdomain.com/pharmacy.yourdomain.com/g' nginx/nginx.conf

# إعادة تشغيل nginx
docker compose restart nginx
```

---

### الخيار 3: VPN داخلي (الأكثر أماناً للصيدلية)

```bash
# تثبيت WireGuard
sudo apt install wireguard -y

# إنشاء مفاتيح
wg genkey | tee /etc/wireguard/private.key | wg pubkey > /etc/wireguard/public.key

# الإعداد في /etc/wireguard/wg0.conf
[Interface]
PrivateKey = <private_key>
Address = 10.0.0.1/24
ListenPort = 51820

[Peer]
# لكل جهاز موظف
PublicKey = <device_public_key>
AllowedIPs = 10.0.0.2/32
```

---

## 👤 بيانات الدخول الافتراضية

> ⚠️ **غيّر كلمات المرور فور التثبيت!**

| المستخدم | كلمة المرور | الصلاحيات |
|----------|------------|-----------|
| `admin` | `admin123` | كاملة |
| `pharmacist` | `ph1234` | مبيعات + عملاء |
| `warehouse` | `wh2222` | مخزون + مشتريات |

---

## 🔒 تغيير كلمات المرور (مهم!)

```bash
# عبر API
curl -X POST http://localhost:8000/api/auth/change-password \
  -H "Authorization: Bearer <token>" \
  -H "Content-Type: application/json" \
  -d '{"current_password": "admin123", "new_password": "كلمة_مرور_قوية_جديدة"}'
```

---

## 💾 النسخ الاحتياطي

```bash
# نسخة يدوية فورية
docker exec pharmacy_db pg_dump -U pharmacy_user pharmacy_db > backup_$(date +%Y%m%d).sql

# استعادة نسخة
docker exec -i pharmacy_db psql -U pharmacy_user pharmacy_db < backup_20240101.sql

# النسخ التلقائية: كل يوم منتصف الليل في /backups/
docker exec pharmacy_backup ls /backups/
```

---

## 🔄 التحديث

```bash
# سحب آخر تحديث
git pull

# إعادة البناء
docker compose up -d --build

# لا تضيع البيانات (محفوظة في volumes منفصل)
```

---

## 🛠️ أوامر مفيدة

```bash
# إيقاف النظام
docker compose down

# إعادة تشغيل سريعة
docker compose restart

# حذف كل شيء (تحذير: يحذف البيانات!)
docker compose down -v

# فتح shell في قاعدة البيانات
docker exec -it pharmacy_db psql -U pharmacy_user pharmacy_db

# مراقبة الأداء
docker stats
```

---

## 📊 مؤشرات الأداء المتوقعة

| المقياس | القيمة |
|---------|--------|
| وقت استجابة API | < 100ms |
| عدد المستخدمين المتزامنين | حتى 50 |
| حجم قاعدة البيانات (سنة) | ~500MB |
| سرعة البحث في 100,000 منتج | < 50ms |

---

## 📞 هيكل API الكامل

```
POST   /api/auth/login              ← تسجيل الدخول
GET    /api/auth/me                 ← بيانات المستخدم الحالي

GET    /api/products/               ← قائمة المنتجات
POST   /api/products/               ← إضافة منتج
PUT    /api/products/{id}           ← تعديل منتج
PATCH  /api/products/{id}/stock     ← تعديل المخزون
DELETE /api/products/{id}           ← حذف منتج

POST   /api/sales/                  ← إتمام عملية بيع
GET    /api/sales/                  ← سجل المبيعات
GET    /api/sales/today-summary     ← ملخص اليوم

GET    /api/reports/dashboard       ← لوحة التحكم
GET    /api/reports/sales/monthly   ← تقرير شهري
GET    /api/reports/sales/yearly    ← تقرير سنوي
GET    /api/reports/profit/monthly  ← تقرير الربحية
GET    /api/reports/products/{id}/sales ← تقرير منتج

GET    /api/customers/              ← قائمة العملاء
GET    /api/companies/              ← قائمة الشركات
GET    /api/employees/              ← قائمة الموظفين
GET    /api/expenses/               ← المصروفات

GET    /api/docs                    ← توثيق API التفاعلي
```

---

*صيدلية الحلول العالمية — نظام الإدارة المتكامل v2.0*
