from django_elasticsearch_dsl import Document, fields

# از آنجایی که سیگنال‌های خودکار و ثبت داکیومنت‌ها را در settings.py غیرفعال کردیم،
# دیگر نیازی به ایمپورت registry و استفاده از دکوراتور @registry.register_document نیست.

class ImageDocument(Document):
    """
    داکیومنت Elasticsearch برای مدل Image.
    این ساختار، نحوه ذخیره و ایندکس شدن داده‌های هر تصویر را در Elasticsearch مشخص می‌کند.
    """
    # فیلدهای اصلی
    id = fields.IntegerField(attr='id')
    title = fields.TextField(
        fields={'raw': fields.KeywordField()} # .raw برای مرتب‌سازی و aggregation دقیق
    )
    description = fields.TextField()
    image_url = fields.KeywordField()
    release_year = fields.IntegerField()

    # فیلدهای مرتبط به صورت آبجکت‌های تو در تو
    movie = fields.ObjectField(properties={
        'title': fields.TextField(fields={'raw': fields.KeywordField()}),
        'year': fields.IntegerField(),
    })
    
    tags = fields.NestedField(properties={
        'name': fields.KeywordField(),
    })

    # --- تمام فیلدهای فیلترینگ ---
    # از KeywordField برای فیلدهایی که نیاز به تطابق دقیق دارند استفاده می‌کنیم.
    media_type = fields.KeywordField()
    genre = fields.KeywordField()
    color = fields.KeywordField()
    aspect_ratio = fields.KeywordField()
    optical_format = fields.KeywordField()
    format = fields.KeywordField()
    interior_exterior = fields.KeywordField()
    time_of_day = fields.KeywordField()
    number_of_people = fields.KeywordField()
    gender = fields.KeywordField()
    age = fields.KeywordField()
    ethnicity = fields.KeywordField()
    frame_size = fields.KeywordField()
    shot_type = fields.KeywordField()
    composition = fields.KeywordField()
    lens_size = fields.KeywordField()
    lens_type = fields.KeywordField()
    lighting = fields.KeywordField()
    lighting_type = fields.KeywordField()
    camera_type = fields.KeywordField()
    resolution = fields.KeywordField()
    frame_rate = fields.KeywordField()
    
    # فیلدهای بولی
    exclude_nudity = fields.BooleanField()
    exclude_violence = fields.BooleanField()
    
    # فیلدهای تاریخ
    created_at = fields.DateField()
    updated_at = fields.DateField()

    class Index:
        # نام ایندکس در Elasticsearch
        name = 'images'
        # تنظیمات ایندکس: 1 shard و بدون replica (برای محیط توسعه مناسب است)
        settings = {
            'number_of_shards': 1,
            'number_of_replicas': 0
        }

    class Django:
        # این سرویس مدلی در دیتابیس خود ندارد و داده‌ها را از Kafka دریافت می‌کند،
        # بنابراین این بخش خالی است.
        model = None