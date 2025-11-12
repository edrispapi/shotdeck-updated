from django.db import models
from django.utils.text import slugify
import uuid
from PIL import Image as PILImage
import requests
from io import BytesIO
import colorsys
from collections import Counter
import math


class BaseOption(models.Model):
    """
    مدل پایه برای همه گزینه‌های فیلتر
    """
    value = models.TextField(help_text="مقدار گزینه")
    display_order = models.IntegerField(blank=True, null=True, help_text="ترتیب نمایش")
    metadata = models.JSONField(blank=True, null=True, help_text="متادیتای اضافی")
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        managed = False  # Shared model - don't create migrations
        abstract = True  # This is a base class

    def __str__(self):
        return self.value


# Crew options with slugs
class DirectorOption(BaseOption):
    slug = models.SlugField(max_length=255, unique=True, blank=True, help_text="URL-friendly slug for the director")

    class Meta:
        managed = False  # Shared model - don't create migrations
        db_table = 'director_options'
        constraints = [
            models.UniqueConstraint(fields=['value'], name='uq_director_value')
        ]
        ordering = ['display_order', 'value']
        verbose_name = "Director Option"
        verbose_name_plural = "Director Options"

    def save(self, *args, **kwargs):
        if not self.slug and self.value:
            self.slug = slugify(self.value)
            if DirectorOption.objects.filter(slug=self.slug).exclude(pk=self.pk).exists():
                self.slug = f"{self.slug}-{uuid.uuid4().hex[:4]}"
        super().save(*args, **kwargs)


class CinematographerOption(BaseOption):
    slug = models.SlugField(max_length=255, unique=True, blank=True, help_text="URL-friendly slug for the cinematographer")

    class Meta:
        managed = False  # Shared model - don't create migrations
        db_table = 'cinematographer_options'
        constraints = [
            models.UniqueConstraint(fields=['value'], name='uq_cinematographer_value')
        ]
        ordering = ['display_order', 'value']
        verbose_name = "Cinematographer Option"
        verbose_name_plural = "Cinematographer Options"

    def save(self, *args, **kwargs):
        if not self.slug and self.value:
            self.slug = slugify(self.value)
            if CinematographerOption.objects.filter(slug=self.slug).exclude(pk=self.pk).exists():
                self.slug = f"{self.slug}-{uuid.uuid4().hex[:4]}"
        super().save(*args, **kwargs)


class EditorOption(BaseOption):
    slug = models.SlugField(max_length=255, unique=True, blank=True, help_text="URL-friendly slug for the editor")

    class Meta:
        managed = False  # Shared model - don't create migrations
        db_table = 'editor_options'
        constraints = [
            models.UniqueConstraint(fields=['value'], name='uq_editor_value')
        ]
        ordering = ['display_order', 'value']
        verbose_name = "Editor Option"
        verbose_name_plural = "Editor Options"

    def save(self, *args, **kwargs):
        if not self.slug and self.value:
            self.slug = slugify(self.value)
            if EditorOption.objects.filter(slug=self.slug).exclude(pk=self.pk).exists():
                self.slug = f"{self.slug}-{uuid.uuid4().hex[:4]}"
        super().save(*args, **kwargs)


class GenreOption(BaseOption):
    class Meta:
        managed = False  # Shared model - don't create migrations
        db_table = 'genre_options'
        constraints = [
            models.UniqueConstraint(fields=['value'], name='uq_genre_value')
        ]
        ordering = ['display_order', 'value']
        verbose_name = "Genre Option"
        verbose_name_plural = "Genre Options"


class ColorOption(BaseOption):
    class Meta:
        managed = False  # Shared model - don't create migrations
        db_table = 'color_options'
        constraints = [
            models.UniqueConstraint(fields=['value'], name='uq_color_value')
        ]
        ordering = ['display_order', 'value']
        verbose_name = "Color Option"
        verbose_name_plural = "Color Options"


class MediaTypeOption(BaseOption):
    class Meta:
        managed = False  # Shared model - don't create migrations
        db_table = 'media_type_options'
        constraints = [
            models.UniqueConstraint(fields=['value'], name='uq_media_type_value')
        ]
        ordering = ['display_order', 'value']
        verbose_name = "Media Type Option"
        verbose_name_plural = "Media Type Options"


class AspectRatioOption(BaseOption):
    class Meta:
        managed = False  # Shared model - don't create migrations
        db_table = 'aspect_ratio_options'
        constraints = [
            models.UniqueConstraint(fields=['value'], name='uq_aspect_ratio_value')
        ]
        ordering = ['display_order', 'value']
        verbose_name = "Aspect Ratio Option"
        verbose_name_plural = "Aspect Ratio Options"


class OpticalFormatOption(BaseOption):
    class Meta:
        managed = False  # Shared model - don't create migrations
        db_table = 'optical_format_options'
        constraints = [
            models.UniqueConstraint(fields=['value'], name='uq_optical_format_value')
        ]
        ordering = ['display_order', 'value']
        verbose_name = "Optical Format Option"
        verbose_name_plural = "Optical Format Options"


class FormatOption(BaseOption):
    class Meta:
        managed = False  # Shared model - don't create migrations
        db_table = 'format_options'
        constraints = [
            models.UniqueConstraint(fields=['value'], name='uq_format_value')
        ]
        ordering = ['display_order', 'value']
        verbose_name = "Format Option"
        verbose_name_plural = "Format Options"


class TimePeriodOption(BaseOption):
    class Meta:
        managed = False  # Shared model - don't create migrations
        db_table = 'time_period_options'
        constraints = [
            models.UniqueConstraint(fields=['value'], name='uq_time_period_value')
        ]
        ordering = ['display_order', 'value']
        verbose_name = "Time Period Option"
        verbose_name_plural = "Time Period Options"


class LabProcessOption(BaseOption):
    class Meta:
        managed = False  # Shared model - don't create migrations
        db_table = 'lab_process_options'
        constraints = [
            models.UniqueConstraint(fields=['value'], name='uq_lab_process_value')
        ]
        ordering = ['display_order', 'value']
        verbose_name = "Lab Process Option"
        verbose_name_plural = "Lab Process Options"


class InteriorExteriorOption(BaseOption):
    class Meta:
        managed = False  # Shared model - don't create migrations
        db_table = 'interior_exterior_options'
        constraints = [
            models.UniqueConstraint(fields=['value'], name='uq_interior_exterior_value')
        ]
        ordering = ['display_order', 'value']
        verbose_name = "Interior/Exterior Option"
        verbose_name_plural = "Interior/Exterior Options"


class TimeOfDayOption(BaseOption):
    class Meta:
        managed = False  # Shared model - don't create migrations
        db_table = 'time_of_day_options'
        constraints = [
            models.UniqueConstraint(fields=['value'], name='uq_time_of_day_value')
        ]
        ordering = ['display_order', 'value']
        verbose_name = "Time of Day Option"
        verbose_name_plural = "Time of Day Options"


class NumberOfPeopleOption(BaseOption):
    class Meta:
        managed = False  # Shared model - don't create migrations
        db_table = 'number_of_people_options'
        constraints = [
            models.UniqueConstraint(fields=['value'], name='uq_number_of_people_value')
        ]
        ordering = ['display_order', 'value']
        verbose_name = "Number of People Option"
        verbose_name_plural = "Number of People Options"


class GenderOption(BaseOption):
    class Meta:
        managed = False  # Shared model - don't create migrations
        db_table = 'gender_options'
        constraints = [
            models.UniqueConstraint(fields=['value'], name='uq_gender_value')
        ]
        ordering = ['display_order', 'value']
        verbose_name = "Gender Option"
        verbose_name_plural = "Gender Options"


class AgeOption(BaseOption):
    class Meta:
        managed = False  # Shared model - don't create migrations
        db_table = 'age_options'
        constraints = [
            models.UniqueConstraint(fields=['value'], name='uq_age_value')
        ]
        ordering = ['display_order', 'value']
        verbose_name = "Age Option"
        verbose_name_plural = "Age Options"


class EthnicityOption(BaseOption):
    class Meta:
        managed = False  # Shared model - don't create migrations
        db_table = 'ethnicity_options'
        constraints = [
            models.UniqueConstraint(fields=['value'], name='uq_ethnicity_value')
        ]
        ordering = ['display_order', 'value']
        verbose_name = "Ethnicity Option"
        verbose_name_plural = "Ethnicity Options"


class FrameSizeOption(BaseOption):
    class Meta:
        managed = False  # Shared model - don't create migrations
        db_table = 'frame_size_options'
        constraints = [
            models.UniqueConstraint(fields=['value'], name='uq_frame_size_value')
        ]
        ordering = ['display_order', 'value']
        verbose_name = "Frame Size Option"
        verbose_name_plural = "Frame Size Options"


class ShotTypeOption(BaseOption):
    class Meta:
        managed = False  # Shared model - don't create migrations
        db_table = 'shot_type_options'
        constraints = [
            models.UniqueConstraint(fields=['value'], name='uq_shot_type_value')
        ]
        ordering = ['display_order', 'value']
        verbose_name = "Shot Type Option"
        verbose_name_plural = "Shot Type Options"


class CompositionOption(BaseOption):
    class Meta:
        managed = False  # Shared model - don't create migrations
        db_table = 'composition_options'
        constraints = [
            models.UniqueConstraint(fields=['value'], name='uq_composition_value')
        ]
        ordering = ['display_order', 'value']
        verbose_name = "Composition Option"
        verbose_name_plural = "Composition Options"


class LensSizeOption(BaseOption):
    class Meta:
        managed = False  # Shared model - don't create migrations
        db_table = 'lens_size_options'
        constraints = [
            models.UniqueConstraint(fields=['value'], name='uq_lens_size_value')
        ]
        ordering = ['display_order', 'value']
        verbose_name = "Lens Size Option"
        verbose_name_plural = "Lens Size Options"


class LensTypeOption(BaseOption):
    class Meta:
        managed = False  # Shared model - don't create migrations
        db_table = 'lens_type_options'
        constraints = [
            models.UniqueConstraint(fields=['value'], name='uq_lens_type_value')
        ]
        ordering = ['display_order', 'value']
        verbose_name = "Lens Type Option"
        verbose_name_plural = "Lens Type Options"


class LightingOption(BaseOption):
    class Meta:
        managed = False  # Shared model - don't create migrations
        db_table = 'lighting_options'
        constraints = [
            models.UniqueConstraint(fields=['value'], name='uq_lighting_value')
        ]
        ordering = ['display_order', 'value']
        verbose_name = "Lighting Option"
        verbose_name_plural = "Lighting Options"


class LightingTypeOption(BaseOption):
    class Meta:
        managed = False  # Shared model - don't create migrations
        db_table = 'lighting_type_options'
        constraints = [
            models.UniqueConstraint(fields=['value'], name='uq_lighting_type_value')
        ]
        ordering = ['display_order', 'value']
        verbose_name = "Lighting Type Option"
        verbose_name_plural = "Lighting Type Options"


class CameraTypeOption(BaseOption):
    class Meta:
        managed = False  # Shared model - don't create migrations
        db_table = 'camera_type_options'
        constraints = [
            models.UniqueConstraint(fields=['value'], name='uq_camera_type_value')
        ]
        ordering = ['display_order', 'value']
        verbose_name = "Camera Type Option"
        verbose_name_plural = "Camera Type Options"


class ResolutionOption(BaseOption):
    class Meta:
        managed = False  # Shared model - don't create migrations
        db_table = 'resolution_options'
        constraints = [
            models.UniqueConstraint(fields=['value'], name='uq_resolution_value')
        ]
        ordering = ['display_order', 'value']
        verbose_name = "Resolution Option"
        verbose_name_plural = "Resolution Options"


class FrameRateOption(BaseOption):
    class Meta:
        managed = False  # Shared model - don't create migrations
        db_table = 'frame_rate_options'
        constraints = [
            models.UniqueConstraint(fields=['value'], name='uq_frame_rate_value')
        ]
        ordering = ['display_order', 'value']
        verbose_name = "Frame Rate Option"
        verbose_name_plural = "Frame Rate Options"


class MovieOption(BaseOption):
    slug = models.SlugField(max_length=255, unique=True, blank=True, help_text="URL-friendly slug for the movie")

    class Meta:
        managed = False  # Shared model - don't create migrations
        db_table = 'movie_options'
        constraints = [
            models.UniqueConstraint(fields=['value'], name='uq_movie_value')
        ]
        ordering = ['display_order', 'value']
        verbose_name = "Movie Option"
        verbose_name_plural = "Movie Options"

    def save(self, *args, **kwargs):
        if not self.slug and self.value:
            self.slug = slugify(self.value)
            if MovieOption.objects.filter(slug=self.slug).exclude(pk=self.pk).exists():
                self.slug = f"{self.slug}-{uuid.uuid4().hex[:4]}"
        super().save(*args, **kwargs)


class ActorOption(BaseOption):
    slug = models.SlugField(max_length=255, unique=True, blank=True, help_text="URL-friendly slug for the actor")

    class Meta:
        managed = False  # Shared model - don't create migrations
        db_table = 'actor_options'
        constraints = [
            models.UniqueConstraint(fields=['value'], name='uq_actor_value')
        ]
        ordering = ['display_order', 'value']
        verbose_name = "Actor Option"
        verbose_name_plural = "Actor Options"

    def save(self, *args, **kwargs):
        if not self.slug and self.value:
            self.slug = slugify(self.value)
            if ActorOption.objects.filter(slug=self.slug).exclude(pk=self.pk).exists():
                self.slug = f"{self.slug}-{uuid.uuid4().hex[:4]}"
        super().save(*args, **kwargs)


class CameraOption(BaseOption):
    class Meta:
        managed = False  # Shared model - don't create migrations
        db_table = 'camera_options'
        constraints = [
            models.UniqueConstraint(fields=['value'], name='uq_camera_value')
        ]
        ordering = ['display_order', 'value']
        verbose_name = "Camera Option"
        verbose_name_plural = "Camera Options"


class LensOption(BaseOption):
    class Meta:
        managed = False  # Shared model - don't create migrations
        db_table = 'lens_options'
        constraints = [
            models.UniqueConstraint(fields=['value'], name='uq_lens_value')
        ]
        ordering = ['display_order', 'value']
        verbose_name = "Lens Option"
        verbose_name_plural = "Lens Options"


class LocationOption(BaseOption):
    class Meta:
        managed = False  # Shared model - don't create migrations
        db_table = 'location_options'
        constraints = [
            models.UniqueConstraint(fields=['value'], name='uq_location_value')
        ]
        ordering = ['display_order', 'value']
        verbose_name = "Location Option"
        verbose_name_plural = "Location Options"


class SettingOption(BaseOption):
    class Meta:
        managed = False  # Shared model - don't create migrations
        db_table = 'setting_options'
        constraints = [
            models.UniqueConstraint(fields=['value'], name='uq_setting_value')
        ]
        ordering = ['display_order', 'value']
        verbose_name = "Setting Option"
        verbose_name_plural = "Setting Options"


class FilmStockOption(BaseOption):
    class Meta:
        managed = False  # Shared model - don't create migrations
        db_table = 'film_stock_options'
        constraints = [
            models.UniqueConstraint(fields=['value'], name='uq_film_stock_value')
        ]
        ordering = ['display_order', 'value']
        verbose_name = "Film Stock Option"
        verbose_name_plural = "Film Stock Options"


class ShotTimeOption(BaseOption):
    class Meta:
        managed = False  # Shared model - don't create migrations
        db_table = 'shot_time_options'
        constraints = [
            models.UniqueConstraint(fields=['value'], name='uq_shot_time_value')
        ]
        ordering = ['display_order', 'value']
        verbose_name = "Shot Time Option"
        verbose_name_plural = "Shot Time Options"


class DescriptionOption(BaseOption):
    class Meta:
        managed = False  # Shared model - don't create migrations
        db_table = 'description_options'
        constraints = [
            models.UniqueConstraint(fields=['value'], name='uq_description_value')
        ]
        ordering = ['display_order', 'value']
        verbose_name = "Description Option"
        verbose_name_plural = "Description Options"


class VfxBackingOption(BaseOption):
    class Meta:
        managed = False  # Shared model - don't create migrations
        db_table = 'vfx_backing_options'
        constraints = [
            models.UniqueConstraint(fields=['value'], name='uq_vfx_backing_value')
        ]
        ordering = ['display_order', 'value']
        verbose_name = "VFX Backing Option"
        verbose_name_plural = "VFX Backing Options"


class ColoristOption(BaseOption):
    class Meta:
        managed = False  # Shared model - don't create migrations
        db_table = 'colorist_options'
        constraints = [
            models.UniqueConstraint(fields=['value'], name='uq_colorist_value')
        ]
        ordering = ['display_order', 'value']
        verbose_name = "Colorist Option"
        verbose_name_plural = "Colorist Options"


class CostumeDesignerOption(BaseOption):
    class Meta:
        managed = False  # Shared model - don't create migrations
        db_table = 'costume_designer_options'
        constraints = [
            models.UniqueConstraint(fields=['value'], name='uq_costume_designer_value')
        ]
        ordering = ['display_order', 'value']
        verbose_name = "Costume Designer Option"
        verbose_name_plural = "Costume Designer Options"


class ShadeOption(BaseOption):
    class Meta:
        managed = False  # Shared model - don't create migrations
        db_table = 'shade_options'
        constraints = [
            models.UniqueConstraint(fields=['value'], name='uq_shade_value')
        ]
        ordering = ['display_order', 'value']
        verbose_name = "Shade Option"
        verbose_name_plural = "Shade Options"


class ArtistOption(BaseOption):
    slug = models.SlugField(max_length=255, unique=True, blank=True, help_text="URL-friendly slug for the artist")

    class Meta:
        managed = False  # Shared model - don't create migrations
        db_table = 'artist_options'
        constraints = [
            models.UniqueConstraint(fields=['value'], name='uq_artist_value')
        ]
        ordering = ['display_order', 'value']
        verbose_name = "Artist Option"
        verbose_name_plural = "Artist Options"

    def save(self, *args, **kwargs):
        if not self.slug and self.value:
            self.slug = slugify(self.value)
            if ArtistOption.objects.filter(slug=self.slug).exclude(pk=self.pk).exists():
                self.slug = f"{self.slug}-{uuid.uuid4().hex[:4]}"
        super().save(*args, **kwargs)


class FilmingLocationOption(BaseOption):
    class Meta:
        managed = False  # Shared model - don't create migrations
        db_table = 'filming_location_options'
        constraints = [
            models.UniqueConstraint(fields=['value'], name='uq_filming_location_value')
        ]
        ordering = ['display_order', 'value']
        verbose_name = "Filming Location Option"
        verbose_name_plural = "Filming Location Options"


class LocationTypeOption(BaseOption):
    class Meta:
        managed = False  # Shared model - don't create migrations
        db_table = 'location_type_options'
        constraints = [
            models.UniqueConstraint(fields=['value'], name='uq_location_type_value')
        ]
        ordering = ['display_order', 'value']
        verbose_name = "Location Type Option"
        verbose_name_plural = "Location Type Options"


class YearOption(BaseOption):
    class Meta:
        managed = False  # Shared model - don't create migrations
        db_table = 'year_options'
        constraints = [
            models.UniqueConstraint(fields=['value'], name='uq_year_value')
        ]
        ordering = ['display_order', 'value']
        verbose_name = "Year Option"
        verbose_name_plural = "Year Options"


class ProductionDesignerOption(BaseOption):
    class Meta:
        managed = False  # Shared model - don't create migrations
        db_table = 'production_designer_options'
        constraints = [
            models.UniqueConstraint(fields=['value'], name='uq_production_designer_value')
        ]
        ordering = ['display_order', 'value']
        verbose_name = "Production Designer Option"
        verbose_name_plural = "Production Designer Options"


class Movie(models.Model):
    title = models.CharField(max_length=255)
    year = models.IntegerField(null=True, blank=True)
    slug = models.SlugField(max_length=255, unique=True, blank=True)

    genre = models.CharField(max_length=500, blank=True, null=True, help_text="Movie genre")
    director = models.ForeignKey(DirectorOption, on_delete=models.SET_NULL, related_name='movies_as_director', null=True, blank=True)
    cinematographer = models.ForeignKey(CinematographerOption, on_delete=models.SET_NULL, related_name='movies_as_cinematographer', null=True, blank=True)
    editor = models.ForeignKey(EditorOption, on_delete=models.SET_NULL, related_name='movies_as_editor', null=True, blank=True)
    colorist = models.CharField(max_length=500, blank=True, null=True)
    production_designer = models.CharField(max_length=500, blank=True, null=True)
    costume_designer = models.CharField(max_length=500, blank=True, null=True)
    cast = models.TextField(blank=True, null=True)

    description = models.TextField(blank=True, null=True)
    duration = models.IntegerField(null=True, blank=True)
    country = models.CharField(max_length=200, blank=True, null=True)
    language = models.CharField(max_length=200, blank=True, null=True)

    image_count = models.IntegerField(default=0, editable=False)

    class Meta:
        managed = False  # Shared model - don't create migrations
        db_table = 'images_movie'
        ordering = ['-year', 'title']
        verbose_name = "Movie"
        verbose_name_plural = "Movies"

    def __str__(self):
        if self.year:
            return f"{self.title} ({self.year})"
        return self.title

    def save(self, *args, **kwargs):
        if not self.slug:
            base_slug = slugify(self.title)
            if self.year:
                self.slug = f"{base_slug}-{self.year}"
            else:
                self.slug = base_slug

            original_slug = self.slug
            counter = 1
            while Movie.objects.filter(slug=self.slug).exists():
                self.slug = f"{original_slug}-{counter}"
                counter += 1
        super().save(*args, **kwargs)


class Tag(models.Model):
    name = models.CharField(max_length=200, unique=True)
    slug = models.SlugField(max_length=200, unique=True, blank=True)

    class Meta:
        managed = False  # Shared model - don't create migrations
        db_table = 'images_tag'
        ordering = ['name']
        verbose_name = "Tag"
        verbose_name_plural = "Tags"
    
    def __str__(self):
        return self.name

    def save(self, *args, **kwargs):
        if not self.slug:
            self.slug = slugify(self.name)
        super().save(*args, **kwargs)


class Image(models.Model):
    id = models.UUIDField(primary_key=True, editable=False, db_column='id')
    title = models.CharField(max_length=255)
    slug = models.SlugField(max_length=255, unique=True, blank=True)
    description = models.TextField(blank=True, null=True)
    image_url = models.URLField(max_length=500)
    movie = models.ForeignKey(Movie, on_delete=models.SET_NULL, related_name='images', null=True, blank=True)
    tags = models.ManyToManyField(Tag, related_name='images', blank=True)
    release_year = models.IntegerField(null=True, blank=True)
    media_type = models.ForeignKey(MediaTypeOption, on_delete=models.SET_NULL, related_name='images', null=True, blank=True)
    genre = models.ManyToManyField(GenreOption, related_name='images', blank=True)
    color = models.ForeignKey(ColorOption, on_delete=models.SET_NULL, related_name='images', null=True, blank=True)

    # Color analysis fields
    dominant_colors = models.JSONField(blank=True, null=True)
    primary_color_hex = models.CharField(max_length=7, blank=True, null=True)
    primary_colors = models.JSONField(blank=True, null=True)
    secondary_color_hex = models.CharField(max_length=7, blank=True, null=True)
    color_palette = models.JSONField(blank=True, null=True)
    color_samples = models.JSONField(blank=True, null=True)
    color_histogram = models.JSONField(blank=True, null=True)
    color_search_terms = models.JSONField(blank=True, null=True)
    color_temperature = models.CharField(max_length=20, blank=True, null=True)
    hue_range = models.CharField(max_length=20, blank=True, null=True)

    aspect_ratio = models.ForeignKey(AspectRatioOption, on_delete=models.SET_NULL, related_name='images', null=True, blank=True)
    optical_format = models.ForeignKey(OpticalFormatOption, on_delete=models.SET_NULL, related_name='images', null=True, blank=True)
    format = models.ForeignKey(FormatOption, on_delete=models.SET_NULL, related_name='images', null=True, blank=True)
    lab_process = models.ForeignKey(LabProcessOption, on_delete=models.SET_NULL, related_name='images', null=True, blank=True)
    time_period = models.ForeignKey(TimePeriodOption, on_delete=models.SET_NULL, related_name='images', null=True, blank=True)
    interior_exterior = models.ForeignKey(InteriorExteriorOption, on_delete=models.SET_NULL, related_name='images', null=True, blank=True)
    time_of_day = models.ForeignKey(TimeOfDayOption, on_delete=models.SET_NULL, related_name='images', null=True, blank=True)
    number_of_people = models.ForeignKey(NumberOfPeopleOption, on_delete=models.SET_NULL, related_name='images', null=True, blank=True)
    gender = models.ForeignKey(GenderOption, on_delete=models.SET_NULL, related_name='images', null=True, blank=True)
    age = models.ForeignKey(AgeOption, on_delete=models.SET_NULL, related_name='images', null=True, blank=True)
    ethnicity = models.ForeignKey(EthnicityOption, on_delete=models.SET_NULL, related_name='images', null=True, blank=True)
    frame_size = models.ForeignKey(FrameSizeOption, on_delete=models.SET_NULL, related_name='images', null=True, blank=True)
    shot_type = models.ForeignKey(ShotTypeOption, on_delete=models.SET_NULL, related_name='images', null=True, blank=True)
    composition = models.ForeignKey(CompositionOption, on_delete=models.SET_NULL, related_name='images', null=True, blank=True)
    lens_size = models.ForeignKey(LensSizeOption, on_delete=models.SET_NULL, related_name='images', null=True, blank=True)
    lens_type = models.ForeignKey(LensTypeOption, on_delete=models.SET_NULL, related_name='images', null=True, blank=True)
    lighting = models.ForeignKey(LightingOption, on_delete=models.SET_NULL, related_name='images', null=True, blank=True)
    lighting_type = models.ForeignKey(LightingTypeOption, on_delete=models.SET_NULL, related_name='images', null=True, blank=True)
    camera_type = models.ForeignKey(CameraTypeOption, on_delete=models.SET_NULL, related_name='images', null=True, blank=True)
    resolution = models.ForeignKey(ResolutionOption, on_delete=models.SET_NULL, related_name='images', null=True, blank=True)
    frame_rate = models.ForeignKey(FrameRateOption, on_delete=models.SET_NULL, related_name='images', null=True, blank=True)

    # New filter fields
    actor = models.ForeignKey(ActorOption, on_delete=models.SET_NULL, related_name='images', null=True, blank=True)
    camera = models.ForeignKey(CameraOption, on_delete=models.SET_NULL, related_name='images', null=True, blank=True)
    lens = models.ForeignKey(LensOption, on_delete=models.SET_NULL, related_name='images', null=True, blank=True)
    location = models.ForeignKey(LocationOption, on_delete=models.SET_NULL, related_name='images', null=True, blank=True)
    setting = models.ForeignKey(SettingOption, on_delete=models.SET_NULL, related_name='images', null=True, blank=True)
    film_stock = models.ForeignKey(FilmStockOption, on_delete=models.SET_NULL, related_name='images', null=True, blank=True)
    shot_time = models.ForeignKey(ShotTimeOption, on_delete=models.SET_NULL, related_name='images', null=True, blank=True)
    description_filter = models.ForeignKey(DescriptionOption, on_delete=models.SET_NULL, related_name='images', null=True, blank=True)
    vfx_backing = models.ForeignKey(VfxBackingOption, on_delete=models.SET_NULL, related_name='images', null=True, blank=True)

    # Crew filters
    director = models.ForeignKey(DirectorOption, on_delete=models.SET_NULL, related_name='images', null=True, blank=True)
    cinematographer = models.ForeignKey(CinematographerOption, on_delete=models.SET_NULL, related_name='images', null=True, blank=True)
    editor = models.ForeignKey(EditorOption, on_delete=models.SET_NULL, related_name='images', null=True, blank=True)
    colorist = models.ForeignKey(ColoristOption, on_delete=models.SET_NULL, related_name='images', null=True, blank=True)
    costume_designer = models.ForeignKey(CostumeDesignerOption, on_delete=models.SET_NULL, related_name='images', null=True, blank=True)
    production_designer = models.ForeignKey(ProductionDesignerOption, on_delete=models.SET_NULL, related_name='images', null=True, blank=True)

    # Additional filters
    shade = models.ForeignKey(ShadeOption, on_delete=models.SET_NULL, related_name='images', null=True, blank=True)
    artist = models.ForeignKey(ArtistOption, on_delete=models.SET_NULL, related_name='images', null=True, blank=True)
    filming_location = models.ForeignKey(FilmingLocationOption, on_delete=models.SET_NULL, related_name='images', null=True, blank=True)
    location_type = models.ForeignKey(LocationTypeOption, on_delete=models.SET_NULL, related_name='images', null=True, blank=True)
    year = models.ForeignKey(YearOption, on_delete=models.SET_NULL, related_name='images', null=True, blank=True)

    exclude_nudity = models.BooleanField(default=False)
    exclude_violence = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        managed = False  # Shared model from image_service - don't create migrations
        db_table = 'images_image'
        ordering = ['-created_at']
        verbose_name = "Image"
        verbose_name_plural = "Images"
        indexes = [
            models.Index(fields=['created_at'], name='image_created_at_idx'),
            models.Index(fields=['movie'], name='image_movie_idx'),
            models.Index(fields=['release_year'], name='image_release_year_idx'),
            models.Index(fields=['media_type'], name='image_media_type_idx'),
            models.Index(fields=['color'], name='image_color_idx'),
            models.Index(fields=['shot_type'], name='image_shot_type_idx'),
            models.Index(fields=['lighting'], name='image_lighting_idx'),
            models.Index(fields=['camera_type'], name='image_camera_type_idx'),
            models.Index(fields=['time_of_day'], name='image_time_of_day_idx'),
            models.Index(fields=['interior_exterior'], name='image_interior_exterior_idx'),
            models.Index(fields=['gender'], name='image_gender_idx'),
            models.Index(fields=['age'], name='image_age_idx'),
            models.Index(fields=['ethnicity'], name='image_ethnicity_idx'),
            models.Index(fields=['frame_size'], name='image_frame_size_idx'),
            models.Index(fields=['aspect_ratio'], name='image_aspect_ratio_idx'),
            models.Index(fields=['optical_format'], name='image_optical_format_idx'),
            models.Index(fields=['format'], name='image_format_idx'),
            models.Index(fields=['lab_process'], name='image_lab_process_idx'),
            models.Index(fields=['time_period'], name='image_time_period_idx'),
            models.Index(fields=['number_of_people'], name='image_number_of_people_idx'),
            models.Index(fields=['composition'], name='image_composition_idx'),
            models.Index(fields=['lens_size'], name='image_lens_size_idx'),
            models.Index(fields=['lens_type'], name='image_lens_type_idx'),
            models.Index(fields=['lighting_type'], name='image_lighting_type_idx'),
            models.Index(fields=['resolution'], name='image_resolution_idx'),
            models.Index(fields=['frame_rate'], name='image_frame_rate_idx'),
            models.Index(fields=['actor'], name='image_actor_idx'),
            models.Index(fields=['camera'], name='image_camera_idx'),
            models.Index(fields=['lens'], name='image_lens_idx'),
            models.Index(fields=['location'], name='image_location_idx'),
            models.Index(fields=['setting'], name='image_setting_idx'),
            models.Index(fields=['film_stock'], name='image_film_stock_idx'),
            models.Index(fields=['shot_time'], name='image_shot_time_idx'),
            models.Index(fields=['description_filter'], name='image_description_filter_idx'),
            models.Index(fields=['vfx_backing'], name='image_vfx_backing_idx'),
            models.Index(fields=['director'], name='image_director_idx'),
            models.Index(fields=['cinematographer'], name='image_cinematographer_idx'),
            models.Index(fields=['editor'], name='image_editor_idx'),
            models.Index(fields=['colorist'], name='image_colorist_idx'),
            models.Index(fields=['costume_designer'], name='image_costume_designer_idx'),
            models.Index(fields=['production_designer'], name='image_production_designer_idx'),
            models.Index(fields=['shade'], name='image_shade_idx'),
            models.Index(fields=['artist'], name='image_artist_idx'),
            models.Index(fields=['filming_location'], name='image_filming_location_idx'),
            models.Index(fields=['location_type'], name='image_location_type_idx'),
            models.Index(fields=['year'], name='image_year_filter_idx'),
            models.Index(fields=['movie', 'created_at'], name='image_movie_created_idx'),
            models.Index(fields=['release_year', 'created_at'], name='image_year_created_idx'),
            models.Index(fields=['shot_type', 'lighting'], name='image_shot_lighting_idx'),
            models.Index(fields=['color', 'lighting'], name='image_color_lighting_idx'),
            models.Index(fields=['camera_type', 'lens_type'], name='image_camera_lens_idx'),
            models.Index(fields=['shot_type', 'time_of_day'], name='image_shot_time_of_day_idx'),
            models.Index(fields=['lighting', 'interior_exterior'], name='image_lighting_location_idx'),
            models.Index(fields=['camera_type', 'film_stock'], name='image_camera_film_idx'),
            models.Index(fields=['actor', 'movie'], name='image_actor_movie_idx'),
            models.Index(fields=['location', 'setting'], name='image_location_setting_idx'),
        ]

    def __str__(self):
        return self.title

    def save(self, *args, **kwargs):
        if not self.slug:
            if self.movie and self.image_url:
                import os
                filename = os.path.basename(self.image_url)
                shot_id = os.path.splitext(filename)[0]
                movie_slug = self.movie.slug
                self.slug = f"{movie_slug}-{shot_id.lower()}"
            else:
                base_slug = slugify(self.title)
                unique_part = uuid.uuid4().hex[:12]
                self.slug = f"{base_slug}-{unique_part}"
        super().save(*args, **kwargs)

    @staticmethod
    def rgb_to_hsl(rgb):
        """Convert RGB to HSL"""
        r, g, b = rgb[0]/255.0, rgb[1]/255.0, rgb[2]/255.0
        h, l, s = colorsys.rgb_to_hls(r, g, b)
        return {
            'hue': round(h * 360, 1),
            'saturation': round(s * 100, 1),
            'lightness': round(l * 100, 1)
        }

    @staticmethod
    def get_color_name(rgb):
        """Get approximate color name from RGB"""
        r, g, b = rgb
        brightness = (r + g + b) / 3

        if brightness < 64:
            return "black"
        elif brightness > 192:
            return "white"
        elif r > g + b:
            return "red"
        elif g > r + b:
            return "green"
        elif b > r + g:
            return "blue"
        elif r > 150 and g > 100:
            return "yellow"
        elif r > 100 and b > 100:
            return "purple"
        elif g > 100 and b > 100:
            return "cyan"
        else:
            return "gray"

    @staticmethod
    def hex_to_rgb(hex_color):
        """Convert hex color to RGB tuple"""
        hex_color = hex_color.lstrip('#')
        return tuple(int(hex_color[i:i+2], 16) for i in (0, 2, 4))