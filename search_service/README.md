# Search Service

این میکروسرویس به عنوان موتور جستجوی مرکزی برای پلتفرم Shotdeck عمل می‌کند. این سرویس به طور کامل از **Elasticsearch** برای ارائه جستجوهای سریع، پیشرفته و تمام‌متن (full-text) استفاده می‌کند و هیچ ارتباط مستقیمی با دیتابیس PostgreSQL ندارد.  

## وظایف اصلی
- **مصرف رویدادهای Kafka** (`image_created`, `image_updated`, `image_deleted`) برای به‌روزرسانی خودکار ایندکس Elasticsearch.
- ارائه API های قدرتمند برای جستجو و فیلتر کردن تصاویر بر اساس ده‌ها پارامتر.
- ارائه API برای پیدا کردن تصاویر مشابه.

## تکنولوژی‌ها
- **Framework:** Django, Django REST Framework
- **Search Engine:** Elasticsearch
- **Messaging:** Kafka (Consumer)
- **API Docs:** drf-spectacular (Swagger/ReDoc)

---  

## راه‌اندازی (محیط توسعه)

### پیش‌نیازها
- Docker & Docker Compose
- یک شبکه داکر به نام `shotdeck_platform_network` باید از قبل وجود داشته باشد.
- سرویس Kafka باید در حال اجرا باشد.

### مراحل اجرا

1.  **راه‌اندازی سرویس:**
    ```bash  
    # مطمئن شوید که Kafka در حال اجراست، سپس:
    docker-compose up --build -d  
    ```  
    این دستور `search_service` و وابستگی مستقیم آن یعنی `elasticsearch` را راه‌اندازی می‌کند.  

2.  **ایندکس کردن داده‌ها (برای اولین بار):**
    پس از اینکه داده‌های تستی در `image_service` ایجاد شدند، آنها را به صورت دستی در Elasticsearch ایندکس کنید.  
    ```bash  
    docker-compose exec search_service python manage.py search_index --rebuild -f  
    ```  
    **توجه:** پس از این مرحله، هر تصویر جدیدی که در `image_service` ایجاد شود، به طور خودکار توسط Kafka Consumer در اینجا ایندکس خواهد شد.  

### دسترسی‌ها
- **API Swagger UI:** `http://localhost:12703/api/schema/swagger-ui/`
- **Elasticsearch API:** `http://localhost:12200/`

### تست API
1.  به Swagger UI در آدرس `http://localhost:8503` بروید.
2.  اندپوینت `GET /api/v1/search/images/` را باز کنید.
3.  روی **"Try it out"** کلیک کرده و با ترکیب فیلترهای مختلف (مانند `q`, `tags`, `genre`) جستجو را امتحان کنید.
4.  برای تست Kafka، یک تصویر در `image_service` ایجاد کرده و بلافاصله آن را در `search_service` جستجو کنید. باید در نتایج ظاهر شود.