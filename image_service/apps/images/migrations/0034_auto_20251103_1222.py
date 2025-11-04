from django.db import migrations

class Migration(migrations.Migration):
    dependencies = [
        ('images', '0033_alter_actoroption_options_alter_ageoption_options_and_more'),
    ]

    operations = [
        migrations.RunSQL(
            sql="""
            ALTER TABLE images_image_tags 
            ALTER COLUMN image_id TYPE UUID USING image_id::text::uuid;
            """,
            reverse_sql="""
            ALTER TABLE images_image_tags 
            ALTER COLUMN image_id TYPE BIGINT USING image_id::text::bigint;
            """
        ),
    ]