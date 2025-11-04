from django.db import migrations

class Migration(migrations.Migration):
    dependencies = [
        ('images', '0036_alter_actoroption_options_alter_ageoption_options_and_more'),  # ← Confirm this is your previous migration!
    ]

    operations = [
        # Step 1: Drop foreign key constraint (required before altering column type)
        migrations.RunSQL(
            sql="""
            ALTER TABLE images_image_tags 
            DROP CONSTRAINT IF EXISTS images_image_tags_image_id_82763d4a_fk_images_image_id;
            """,
            reverse_sql="""
            ALTER TABLE images_image_tags 
            ADD CONSTRAINT images_image_tags_image_id_82763d4a_fk_images_image_id 
            FOREIGN KEY (image_id) REFERENCES images_image(id) DEFERRABLE INITIALLY DEFERRED;
            """
        ),

        # Step 2: Alter column from bigint → UUID
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

        # Step 3: Re-add foreign key constraint
        migrations.RunSQL(
            sql="""
            ALTER TABLE images_image_tags 
            ADD CONSTRAINT images_image_tags_image_id_82763d4a_fk_images_image_id 
            FOREIGN KEY (image_id) REFERENCES images_image(id) DEFERRABLE INITIALLY DEFERRED;
            """,
            reverse_sql="""
            ALTER TABLE images_image_tags 
            DROP CONSTRAINT IF EXISTS images_image_tags_image_id_82763d4a_fk_images_image_id;
            """
        ),
    ]