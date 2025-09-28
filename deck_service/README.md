# Deck Service

این میکروسرویس مسئولیت مدیریت "Deck" ها (مجموعه‌های تصاویر) و داده‌های مربوط به کاربران در پلتفرم Shotdeck را بر عهده دارد. هر کاربر می‌تواند چندین Deck داشته باشد و در هر Deck، لیستی از ID تصاویر مورد علاقه خود را ذخیره کند.  

## وظایف اصلی
- ارائه API های CRUD برای ایجاد، خواندن، به‌روزرسانی و حذف Deck ها.
- مدیریت مالکیت هر Deck و اطمینان از اینکه هر کاربر فقط به Deck های خود دسترسی دارد.
- گوش دادن به رویدادهای Kafka (مانند `image_deleted`) برای همگام‌سازی و حذف ID تصاویر حذف شده از تمام Deck ها.

## تکنولوژی‌ها
- **Framework:** Django, Django REST Framework
- **Database:** PostgreSQL (اختصاصی)
- **Messaging:** Kafka (Consumer)
- **API Docs:** drf-spectacular (Swagger/ReDoc)

---  

## راه‌اندازی (محیط توسعه)

### پیش‌نیازها
- Docker & Docker Compose
- یک شبکه داکر به نام `shotdeck_platform_network` باید از قبل وجود داشته باشد (`docker network create shotdeck_platform_network`).

### مراحل اجرا

1.  **راه‌اندازی Kafka و Zookeeper:**
    این سرویس مسئول راه‌اندازی زیرساخت Kafka برای کل پلتفرم است.  
    ```bash  
    docker-compose up --build -d  
    ```  
    این دستور تمام اجزای مورد نیاز این سرویس (Kafka, Zookeeper, PostgreSQL DB, و خود سرویس) را راه‌اندازی می‌کند.  

2.  **ایجاد و اعمال مایگریشن‌ها:**
    ```bash  
    docker-compose exec deck_service python manage.py makemigrations decks  
    docker-compose exec deck_service python manage.py migrate  
    ```  

3.  **ایجاد کاربر ادمین:**
    ```bash  
    docker-compose exec deck_service python manage.py createsuperuser  
    ```  

### دسترسی‌ها
- **API Swagger UI:** `http://localhost:12700/api/schema/swagger-ui/`
- **پنل ادمین:** `http://localhost:12700/admin/`

### تست API
1.  با `POST /api/v1/api-token-auth/` یک توکن دریافت کنید.
2.  توکن را در Swagger با دکمه "Authorize" تنظیم کنید (`Token <your_token>`).
3.  با `POST /api/v1/decks/` یک Deck جدید با Body زیر ایجاد کنید:
    ```json  
    {  
      "title": "Inception Dream Sequence",  
      "description": "Shots from the Paris folding scene.",  
      "image_ids": [101, 205, 308]  
    }  
    ```  