# /home/a/shotdeck-main/image_service/apps/images/models.py

from django.db import models
import uuid
from django.utils.text import slugify
from django.core.cache import cache
from django.db.models import Q, Count, Prefetch
from django.urls import reverse
from PIL import Image as PILImage
import requests
from io import BytesIO
import colorsys
from collections import Counter
import math
import logging

logger = logging.getLogger(__name__)

__all__ = [
    'BaseOption', 'DirectorOption', 'CinematographerOption', 'EditorOption',
    'GenreOption', 'ColorOption', 'MediaTypeOption', 'AspectRatioOption',
    'OpticalFormatOption', 'FormatOption', 'TimePeriodOption', 'LabProcessOption',
    'InteriorExteriorOption', 'TimeOfDayOption', 'NumberOfPeopleOption', 'GenderOption',
    'AgeOption', 'EthnicityOption', 'FrameSizeOption', 'ShotTypeOption', 'CompositionOption',
    'LensSizeOption', 'LensTypeOption', 'LightingOption', 'LightingTypeOption',
    'CameraTypeOption', 'ResolutionOption', 'FrameRateOption', 'MovieOption',
    'ActorOption', 'CameraOption', 'LensOption', 'LocationOption', 'SettingOption',
    'FilmStockOption', 'ShotTimeOption', 'DescriptionOption', 'VfxBackingOption',
    'ColoristOption', 'CostumeDesignerOption', 'ShadeOption', 'ArtistOption',
    'FilmingLocationOption', 'LocationTypeOption', 'YearOption', 'ProductionDesignerOption',
    'Movie', 'Tag', 'Image'
]


class BaseOption(models.Model):
    """Base model for all filter options with caching support"""
    value = models.TextField(help_text="Option value")
    display_order = models.IntegerField(blank=True, null=True, help_text="Display order")
    metadata = models.JSONField(blank=True, null=True, help_text="Additional metadata")
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        abstract = True

    def __str__(self):
        return self.value

    def save(self, *args, **kwargs):
        super().save(*args, **kwargs)
        # Invalidate cache on save
        self.invalidate_cache()

    def delete(self, *args, **kwargs):
        super().delete(*args, **kwargs)
        # Invalidate cache on delete
        self.invalidate_cache()

    @classmethod
    def invalidate_cache(cls):
        """Invalidate cache for this option type"""
        cache_key = f"{cls.__name__.lower()}_all"
        cache.delete(cache_key)

    @classmethod
    def get_all_cached(cls, timeout=3600):
        """Get all options with caching"""
        cache_key = f"{cls.__name__.lower()}_all"
        options = cache.get(cache_key)
        
        if options is None:
            options = list(cls.objects.all().order_by('display_order', 'value'))
            cache.set(cache_key, options, timeout)
        
        return options


# Crew Options with Slugs
class DirectorOption(BaseOption):
    slug = models.SlugField(max_length=255, unique=True, blank=True)

    class Meta:
        db_table = 'director_options'
        constraints = [models.UniqueConstraint(fields=['value'], name='uq_director_value')]
        ordering = ['display_order', 'value']
        verbose_name = "Director"
        verbose_name_plural = "Directors"
        indexes = [
            models.Index(fields=['slug'], name='director_slug_idx'),
            models.Index(fields=['value'], name='director_value_idx'),
        ]

    def save(self, *args, **kwargs):
        if not self.slug and self.value:
            base_slug = slugify(self.value)
            self.slug = base_slug
            counter = 1
            while DirectorOption.objects.filter(slug=self.slug).exclude(pk=self.pk).exists():
                self.slug = f"{base_slug}-{counter}"
                counter += 1
        super().save(*args, **kwargs)


class CinematographerOption(BaseOption):
    slug = models.SlugField(max_length=255, unique=True, blank=True)

    class Meta:
        db_table = 'cinematographer_options'
        constraints = [models.UniqueConstraint(fields=['value'], name='uq_cinematographer_value')]
        ordering = ['display_order', 'value']
        verbose_name = "Cinematographer"
        verbose_name_plural = "Cinematographers"
        indexes = [
            models.Index(fields=['slug'], name='cinematographer_slug_idx'),
            models.Index(fields=['value'], name='cinematographer_value_idx'),
        ]

    def save(self, *args, **kwargs):
        if not self.slug and self.value:
            base_slug = slugify(self.value)
            self.slug = base_slug
            counter = 1
            while CinematographerOption.objects.filter(slug=self.slug).exclude(pk=self.pk).exists():
                self.slug = f"{base_slug}-{counter}"
                counter += 1
        super().save(*args, **kwargs)


class EditorOption(BaseOption):
    slug = models.SlugField(max_length=255, unique=True, blank=True)

    class Meta:
        db_table = 'editor_options'
        constraints = [models.UniqueConstraint(fields=['value'], name='uq_editor_value')]
        ordering = ['display_order', 'value']
        verbose_name = "Editor"
        verbose_name_plural = "Editors"
        indexes = [
            models.Index(fields=['slug'], name='editor_slug_idx'),
            models.Index(fields=['value'], name='editor_value_idx'),
        ]

    def save(self, *args, **kwargs):
        if not self.slug and self.value:
            base_slug = slugify(self.value)
            self.slug = base_slug
            counter = 1
            while EditorOption.objects.filter(slug=self.slug).exclude(pk=self.pk).exists():
                self.slug = f"{base_slug}-{counter}"
                counter += 1
        super().save(*args, **kwargs)


# Standard Options (without slugs)
class GenreOption(BaseOption):
    class Meta:
        db_table = 'genre_options'
        constraints = [models.UniqueConstraint(fields=['value'], name='uq_genre_value')]
        ordering = ['display_order', 'value']
        verbose_name = "Genre"
        verbose_name_plural = "Genres"


class ColorOption(BaseOption):
    hex_code = models.CharField(max_length=7, blank=True, null=True, help_text="Hex color code")

    class Meta:
        db_table = 'color_options'
        constraints = [models.UniqueConstraint(fields=['value'], name='uq_color_value')]
        ordering = ['display_order', 'value']
        verbose_name = "Color"
        verbose_name_plural = "Colors"


class MediaTypeOption(BaseOption):
    class Meta:
        db_table = 'media_type_options'
        constraints = [models.UniqueConstraint(fields=['value'], name='uq_media_type_value')]
        ordering = ['display_order', 'value']
        verbose_name = "Media Type"
        verbose_name_plural = "Media Types"


class AspectRatioOption(BaseOption):
    class Meta:
        db_table = 'aspect_ratio_options'
        constraints = [models.UniqueConstraint(fields=['value'], name='uq_aspect_ratio_value')]
        ordering = ['display_order', 'value']
        verbose_name = "Aspect Ratio"
        verbose_name_plural = "Aspect Ratios"


class OpticalFormatOption(BaseOption):
    class Meta:
        db_table = 'optical_format_options'
        constraints = [models.UniqueConstraint(fields=['value'], name='uq_optical_format_value')]
        ordering = ['display_order', 'value']
        verbose_name = "Optical Format"
        verbose_name_plural = "Optical Formats"


class FormatOption(BaseOption):
    class Meta:
        db_table = 'format_options'
        constraints = [models.UniqueConstraint(fields=['value'], name='uq_format_value')]
        ordering = ['display_order', 'value']
        verbose_name = "Format"
        verbose_name_plural = "Formats"


class TimePeriodOption(BaseOption):
    class Meta:
        db_table = 'time_period_options'
        constraints = [models.UniqueConstraint(fields=['value'], name='uq_time_period_value')]
        ordering = ['display_order', 'value']
        verbose_name = "Time Period"
        verbose_name_plural = "Time Periods"


class LabProcessOption(BaseOption):
    class Meta:
        db_table = 'lab_process_options'
        constraints = [models.UniqueConstraint(fields=['value'], name='uq_lab_process_value')]
        ordering = ['display_order', 'value']
        verbose_name = "Lab Process"
        verbose_name_plural = "Lab Processes"


class InteriorExteriorOption(BaseOption):
    class Meta:
        db_table = 'interior_exterior_options'
        constraints = [models.UniqueConstraint(fields=['value'], name='uq_interior_exterior_value')]
        ordering = ['display_order', 'value']
        verbose_name = "Interior/Exterior"
        verbose_name_plural = "Interior/Exterior"


class TimeOfDayOption(BaseOption):
    class Meta:
        db_table = 'time_of_day_options'
        constraints = [models.UniqueConstraint(fields=['value'], name='uq_time_of_day_value')]
        ordering = ['display_order', 'value']
        verbose_name = "Time of Day"
        verbose_name_plural = "Time of Day"


class NumberOfPeopleOption(BaseOption):
    class Meta:
        db_table = 'number_of_people_options'
        constraints = [models.UniqueConstraint(fields=['value'], name='uq_number_of_people_value')]
        ordering = ['display_order', 'value']
        verbose_name = "Number of People"
        verbose_name_plural = "Number of People"


class GenderOption(BaseOption):
    class Meta:
        db_table = 'gender_options'
        constraints = [models.UniqueConstraint(fields=['value'], name='uq_gender_value')]
        ordering = ['display_order', 'value']
        verbose_name = "Gender"
        verbose_name_plural = "Genders"


class AgeOption(BaseOption):
    class Meta:
        db_table = 'age_options'
        constraints = [models.UniqueConstraint(fields=['value'], name='uq_age_value')]
        ordering = ['display_order', 'value']
        verbose_name = "Age"
        verbose_name_plural = "Ages"


class EthnicityOption(BaseOption):
    class Meta:
        db_table = 'ethnicity_options'
        constraints = [models.UniqueConstraint(fields=['value'], name='uq_ethnicity_value')]
        ordering = ['display_order', 'value']
        verbose_name = "Ethnicity"
        verbose_name_plural = "Ethnicities"


class FrameSizeOption(BaseOption):
    class Meta:
        db_table = 'frame_size_options'
        constraints = [models.UniqueConstraint(fields=['value'], name='uq_frame_size_value')]
        ordering = ['display_order', 'value']
        verbose_name = "Frame Size"
        verbose_name_plural = "Frame Sizes"


class ShotTypeOption(BaseOption):
    class Meta:
        db_table = 'shot_type_options'
        constraints = [models.UniqueConstraint(fields=['value'], name='uq_shot_type_value')]
        ordering = ['display_order', 'value']
        verbose_name = "Shot Type"
        verbose_name_plural = "Shot Types"


class CompositionOption(BaseOption):
    class Meta:
        db_table = 'composition_options'
        constraints = [models.UniqueConstraint(fields=['value'], name='uq_composition_value')]
        ordering = ['display_order', 'value']
        verbose_name = "Composition"
        verbose_name_plural = "Compositions"


class LensSizeOption(BaseOption):
    class Meta:
        db_table = 'lens_size_options'
        constraints = [models.UniqueConstraint(fields=['value'], name='uq_lens_size_value')]
        ordering = ['display_order', 'value']
        verbose_name = "Lens Size"
        verbose_name_plural = "Lens Sizes"


class LensTypeOption(BaseOption):
    class Meta:
        db_table = 'lens_type_options'
        constraints = [models.UniqueConstraint(fields=['value'], name='uq_lens_type_value')]
        ordering = ['display_order', 'value']
        verbose_name = "Lens Type"
        verbose_name_plural = "Lens Types"


class LightingOption(BaseOption):
    class Meta:
        db_table = 'lighting_options'
        constraints = [models.UniqueConstraint(fields=['value'], name='uq_lighting_value')]
        ordering = ['display_order', 'value']
        verbose_name = "Lighting"
        verbose_name_plural = "Lighting"


class LightingTypeOption(BaseOption):
    class Meta:
        db_table = 'lighting_type_options'
        constraints = [models.UniqueConstraint(fields=['value'], name='uq_lighting_type_value')]
        ordering = ['display_order', 'value']
        verbose_name = "Lighting Type"
        verbose_name_plural = "Lighting Types"


class CameraTypeOption(BaseOption):
    class Meta:
        db_table = 'camera_type_options'
        constraints = [models.UniqueConstraint(fields=['value'], name='uq_camera_type_value')]
        ordering = ['display_order', 'value']
        verbose_name = "Camera Type"
        verbose_name_plural = "Camera Types"


class ResolutionOption(BaseOption):
    class Meta:
        db_table = 'resolution_options'
        constraints = [models.UniqueConstraint(fields=['value'], name='uq_resolution_value')]
        ordering = ['display_order', 'value']
        verbose_name = "Resolution"
        verbose_name_plural = "Resolutions"


class FrameRateOption(BaseOption):
    class Meta:
        db_table = 'frame_rate_options'
        constraints = [models.UniqueConstraint(fields=['value'], name='uq_frame_rate_value')]
        ordering = ['display_order', 'value']
        verbose_name = "Frame Rate"
        verbose_name_plural = "Frame Rates"


class MovieOption(BaseOption):
    slug = models.SlugField(max_length=255, unique=True, blank=True)

    class Meta:
        db_table = 'movie_options'
        constraints = [models.UniqueConstraint(fields=['value'], name='uq_movie_value')]
        ordering = ['display_order', 'value']
        verbose_name = "Movie"
        verbose_name_plural = "Movies"
        indexes = [
            models.Index(fields=['slug'], name='movie_opt_slug_idx'),
        ]

    def save(self, *args, **kwargs):
        if not self.slug and self.value:
            base_slug = slugify(self.value)
            self.slug = base_slug
            counter = 1
            while MovieOption.objects.filter(slug=self.slug).exclude(pk=self.pk).exists():
                self.slug = f"{base_slug}-{counter}"
                counter += 1
        super().save(*args, **kwargs)


class ActorOption(BaseOption):
    slug = models.SlugField(max_length=255, unique=True, blank=True)

    class Meta:
        db_table = 'actor_options'
        constraints = [models.UniqueConstraint(fields=['value'], name='uq_actor_value')]
        ordering = ['display_order', 'value']
        verbose_name = "Actor"
        verbose_name_plural = "Actors"
        indexes = [
            models.Index(fields=['slug'], name='actor_slug_idx'),
        ]

    def save(self, *args, **kwargs):
        if not self.slug and self.value:
            base_slug = slugify(self.value)
            self.slug = base_slug
            counter = 1
            while ActorOption.objects.filter(slug=self.slug).exclude(pk=self.pk).exists():
                self.slug = f"{base_slug}-{counter}"
                counter += 1
        super().save(*args, **kwargs)


class CameraOption(BaseOption):
    class Meta:
        db_table = 'camera_options'
        constraints = [models.UniqueConstraint(fields=['value'], name='uq_camera_value')]
        ordering = ['display_order', 'value']
        verbose_name = "Camera"
        verbose_name_plural = "Cameras"


class LensOption(BaseOption):
    class Meta:
        db_table = 'lens_options'
        constraints = [models.UniqueConstraint(fields=['value'], name='uq_lens_value')]
        ordering = ['display_order', 'value']
        verbose_name = "Lens"
        verbose_name_plural = "Lenses"


class LocationOption(BaseOption):
    class Meta:
        db_table = 'location_options'
        constraints = [models.UniqueConstraint(fields=['value'], name='uq_location_value')]
        ordering = ['display_order', 'value']
        verbose_name = "Location"
        verbose_name_plural = "Locations"


class SettingOption(BaseOption):
    class Meta:
        db_table = 'setting_options'
        constraints = [models.UniqueConstraint(fields=['value'], name='uq_setting_value')]
        ordering = ['display_order', 'value']
        verbose_name = "Setting"
        verbose_name_plural = "Settings"


class FilmStockOption(BaseOption):
    class Meta:
        db_table = 'film_stock_options'
        constraints = [models.UniqueConstraint(fields=['value'], name='uq_film_stock_value')]
        ordering = ['display_order', 'value']
        verbose_name = "Film Stock"
        verbose_name_plural = "Film Stocks"


class ShotTimeOption(BaseOption):
    class Meta:
        db_table = 'shot_time_options'
        constraints = [models.UniqueConstraint(fields=['value'], name='uq_shot_time_value')]
        ordering = ['display_order', 'value']
        verbose_name = "Shot Time"
        verbose_name_plural = "Shot Times"


class DescriptionOption(BaseOption):
    class Meta:
        db_table = 'description_options'
        constraints = [models.UniqueConstraint(fields=['value'], name='uq_description_value')]
        ordering = ['display_order', 'value']
        verbose_name = "Description"
        verbose_name_plural = "Descriptions"


class VfxBackingOption(BaseOption):
    class Meta:
        db_table = 'vfx_backing_options'
        constraints = [models.UniqueConstraint(fields=['value'], name='uq_vfx_backing_value')]
        ordering = ['display_order', 'value']
        verbose_name = "VFX Backing"
        verbose_name_plural = "VFX Backings"


class ColoristOption(BaseOption):
    class Meta:
        db_table = 'colorist_options'
        constraints = [models.UniqueConstraint(fields=['value'], name='uq_colorist_value')]
        ordering = ['display_order', 'value']
        verbose_name = "Colorist"
        verbose_name_plural = "Colorists"


class CostumeDesignerOption(BaseOption):
    class Meta:
        db_table = 'costume_designer_options'
        constraints = [models.UniqueConstraint(fields=['value'], name='uq_costume_designer_value')]
        ordering = ['display_order', 'value']
        verbose_name = "Costume Designer"
        verbose_name_plural = "Costume Designers"


class ProductionDesignerOption(BaseOption):
    class Meta:
        db_table = 'production_designer_options'
        constraints = [models.UniqueConstraint(fields=['value'], name='uq_production_designer_value')]
        ordering = ['display_order', 'value']
        verbose_name = "Production Designer"
        verbose_name_plural = "Production Designers"


class ShadeOption(BaseOption):
    class Meta:
        db_table = 'shade_options'
        constraints = [models.UniqueConstraint(fields=['value'], name='uq_shade_value')]
        ordering = ['display_order', 'value']
        verbose_name = "Shade"
        verbose_name_plural = "Shades"


class ArtistOption(BaseOption):
    slug = models.SlugField(max_length=255, unique=True, blank=True)

    class Meta:
        db_table = 'artist_options'
        constraints = [models.UniqueConstraint(fields=['value'], name='uq_artist_value')]
        ordering = ['display_order', 'value']
        verbose_name = "Artist"
        verbose_name_plural = "Artists"
        indexes = [
            models.Index(fields=['slug'], name='artist_slug_idx'),
        ]

    def save(self, *args, **kwargs):
        if not self.slug and self.value:
            base_slug = slugify(self.value)
            self.slug = base_slug
            counter = 1
            while ArtistOption.objects.filter(slug=self.slug).exclude(pk=self.pk).exists():
                self.slug = f"{base_slug}-{counter}"
                counter += 1
        super().save(*args, **kwargs)


class FilmingLocationOption(BaseOption):
    class Meta:
        db_table = 'filming_location_options'
        constraints = [models.UniqueConstraint(fields=['value'], name='uq_filming_location_value')]
        ordering = ['display_order', 'value']
        verbose_name = "Filming Location"
        verbose_name_plural = "Filming Locations"


class LocationTypeOption(BaseOption):
    class Meta:
        db_table = 'location_type_options'
        constraints = [models.UniqueConstraint(fields=['value'], name='uq_location_type_value')]
        ordering = ['display_order', 'value']
        verbose_name = "Location Type"
        verbose_name_plural = "Location Types"


class YearOption(BaseOption):
    class Meta:
        db_table = 'year_options'
        constraints = [models.UniqueConstraint(fields=['value'], name='uq_year_value')]
        ordering = ['display_order', 'value']
        verbose_name = "Year"
        verbose_name_plural = "Years"


# Manager for optimized queries
class MovieManager(models.Manager):
    def with_images(self):
        """Prefetch related images for efficient queries"""
        return self.prefetch_related('image_set')

    def with_full_details(self):
        """Select all related fields for movie detail pages"""
        return self.select_related(
            'director', 'cinematographer', 'editor'
        ).prefetch_related('image_set')

    def popular(self, limit=10):
        """Get most popular movies by image count"""
        return self.annotate(
            num_images=Count('image_set')
        ).filter(num_images__gt=0).order_by('-num_images')[:limit]


class Movie(models.Model):
    title = models.CharField(max_length=255, db_index=True)
    year = models.IntegerField(null=True, blank=True, db_index=True)
    slug = models.SlugField(max_length=255, unique=True, blank=True)

    # Enhanced movie details
    genre = models.CharField(max_length=500, blank=True, null=True)
    director = models.ForeignKey(DirectorOption, on_delete=models.SET_NULL, related_name='movies_as_director', null=True, blank=True)
    cinematographer = models.ForeignKey(CinematographerOption, on_delete=models.SET_NULL, related_name='movies_as_cinematographer', null=True, blank=True)
    editor = models.ForeignKey(EditorOption, on_delete=models.SET_NULL, related_name='movies_as_editor', null=True, blank=True)
    colorist = models.CharField(max_length=500, blank=True, null=True)
    production_designer = models.CharField(max_length=500, blank=True, null=True)
    costume_designer = models.CharField(max_length=500, blank=True, null=True)
    cast = models.TextField(blank=True, null=True)

    # Metadata
    description = models.TextField(blank=True, null=True)
    duration = models.IntegerField(null=True, blank=True)
    country = models.CharField(max_length=200, blank=True, null=True)
    language = models.CharField(max_length=200, blank=True, null=True)

    # Computed fields
    image_count = models.IntegerField(default=0, editable=False, db_index=True)

    # Custom manager
    objects = MovieManager()

    class Meta:
        ordering = ['-year', 'title']
        verbose_name = "Movie"
        verbose_name_plural = "Movies"
        indexes = [
            models.Index(fields=['title', 'year'], name='movie_title_year_idx'),
            models.Index(fields=['-image_count'], name='movie_img_count_idx'),
        ]
        constraints = [
            models.UniqueConstraint(fields=['title', 'year'], name='movie_title_year_unique'),
        ]

    def __str__(self):
        return f"{self.title} ({self.year})" if self.year else self.title

    def save(self, *args, **kwargs):
        if not self.slug:
            base_slug = slugify(self.title)
            self.slug = f"{base_slug}-{self.year}" if self.year else base_slug
            counter = 1
            while Movie.objects.filter(slug=self.slug).exclude(pk=self.pk).exists():
                self.slug = f"{base_slug}-{self.year}-{counter}" if self.year else f"{base_slug}-{counter}"
                counter += 1
        super().save(*args, **kwargs)
        # Invalidate cache
        self.invalidate_cache()

    def invalidate_cache(self):
        """Invalidate movie-related caches"""
        cache.delete(f"movie_{self.pk}")
        cache.delete(f"movie_slug_{self.slug}")
        cache.delete("movie_list_popular")

    @classmethod
    def get_by_slug_cached(cls, slug, timeout=3600):
        """Get movie by slug with caching"""
        cache_key = f"movie_slug_{slug}"
        movie = cache.get(cache_key)
        
        if movie is None:
            try:
                movie = cls.objects.select_related(
                    'director', 'cinematographer', 'editor'
                ).get(slug=slug)
                cache.set(cache_key, movie, timeout)
            except cls.DoesNotExist:
                return None
        
        return movie

    def update_image_count(self):
        """Update cached image count"""
        self.image_count = self.image_set.count()
        self.save(update_fields=['image_count'])

    def get_cast_list(self):
        """Return cast as a list"""
        if not self.cast:
            return []
        return [actor.strip() for actor in self.cast.split(',') if actor.strip()]

    def get_main_crew(self):
        """Return main crew information"""
        return {
            'director': self.director,
            'cinematographer': self.cinematographer,
            'editor': self.editor,
            'colorist': self.colorist,
            'production_designer': self.production_designer,
            'costume_designer': self.costume_designer,
        }


class Tag(models.Model):
    name = models.CharField(max_length=200, unique=True)
    slug = models.SlugField(max_length=200, unique=True, blank=True)
    usage_count = models.IntegerField(default=0, editable=False)

    class Meta:
        ordering = ['name']
        verbose_name = "Tag"
        verbose_name_plural = "Tags"
        indexes = [
            models.Index(fields=['slug'], name='tag_slug_idx'),
            models.Index(fields=['-usage_count'], name='tag_usage_idx'),
        ]

    def __str__(self):
        return self.name

    def save(self, *args, **kwargs):
        # Ensure unique slug, adding a numeric suffix on conflicts
        if not self.slug and self.name:
            base_slug = slugify(self.name)
            self.slug = base_slug
            counter = 1
            while Tag.objects.filter(slug=self.slug).exclude(pk=self.pk).exists():
                self.slug = f"{base_slug}-{counter}"
                counter += 1
        super().save(*args, **kwargs)

    def update_usage_count(self):
        """Update usage count based on image associations"""
        self.usage_count = self.images.count()
        self.save(update_fields=['usage_count'])


# Manager for optimized Image queries
class ImageManager(models.Manager):
    def with_all_relations(self):
        """Select all related fields for detail views"""
        return self.select_related(
            'movie', 'actor', 'camera', 'cinematographer', 'director', 'lens',
            'film_stock', 'setting', 'location', 'filming_location', 'aspect_ratio',
            'time_period', 'time_of_day', 'interior_exterior', 'number_of_people',
            'gender', 'age', 'ethnicity', 'frame_size', 'shot_type', 'composition',
            'lens_type', 'lighting', 'lighting_type', 'camera_type', 'resolution',
            'frame_rate', 'vfx_backing', 'shade', 'artist', 'location_type',
            'media_type', 'color', 'optical_format', 'format', 'lab_process'
        ).prefetch_related('tags', 'genre')

    def for_list(self):
        """Optimized queryset for list views"""
        return self.select_related(
            'movie', 'director', 'cinematographer', 'shot_type', 'lighting', 'color'
        ).only(
            'uuid', 'slug', 'title', 'image_url', 'created_at',
            'movie__title', 'movie__year', 'director__value', 'cinematographer__value'
        )

    def recent(self, limit=20):
        """Get recent images"""
        return self.for_list().order_by('-created_at')[:limit]

    def by_color(self, color_hex, tolerance=30):
        """Find images by similar color"""
        # This would need custom SQL or ElasticSearch for production
        return self.filter(primary_color_hex__isnull=False)


class Image(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    title = models.CharField(max_length=255, db_index=True)
    slug = models.SlugField(max_length=255, unique=True, blank=True, db_index=True)
    description = models.TextField(blank=True, null=True)
    image_url = models.URLField(max_length=500)
    
    # Relationships
    movie = models.ForeignKey(Movie, on_delete=models.CASCADE, related_name='images')
    tags = models.ManyToManyField(Tag, related_name='images', blank=True)
    
    # Basic fields
    release_year = models.IntegerField(null=True, blank=True, db_index=True)
    media_type = models.ForeignKey(MediaTypeOption, on_delete=models.SET_NULL, related_name='images', null=True, blank=True)
    genre = models.ManyToManyField(GenreOption, related_name='images', blank=True)
    color = models.ForeignKey(ColorOption, on_delete=models.SET_NULL, related_name='images', null=True, blank=True)

    # Enhanced color analysis
    dominant_colors = models.JSONField(blank=True, null=True)
    primary_color_hex = models.CharField(max_length=7, blank=True, null=True, db_index=True)
    primary_colors = models.JSONField(blank=True, null=True)
    secondary_color_hex = models.CharField(max_length=7, blank=True, null=True)
    color_palette = models.JSONField(blank=True, null=True)
    color_samples = models.JSONField(blank=True, null=True)
    color_histogram = models.JSONField(blank=True, null=True)
    color_search_terms = models.JSONField(blank=True, null=True)
    color_temperature = models.CharField(max_length=20, blank=True, null=True)
    hue_range = models.CharField(max_length=20, blank=True, null=True)
    
    # Technical fields
    aspect_ratio = models.ForeignKey(AspectRatioOption, on_delete=models.SET_NULL, related_name='images', null=True, blank=True)
    optical_format = models.ForeignKey(OpticalFormatOption, on_delete=models.SET_NULL, related_name='images', null=True, blank=True)
    format = models.ForeignKey(FormatOption, on_delete=models.SET_NULL, related_name='images', null=True, blank=True)
    lab_process = models.ForeignKey(LabProcessOption, on_delete=models.SET_NULL, related_name='images', null=True, blank=True)
    
    # Context fields
    time_period = models.ForeignKey(TimePeriodOption, on_delete=models.SET_NULL, related_name='images', null=True, blank=True)
    interior_exterior = models.ForeignKey(InteriorExteriorOption, on_delete=models.SET_NULL, related_name='images', null=True, blank=True)
    time_of_day = models.ForeignKey(TimeOfDayOption, on_delete=models.SET_NULL, related_name='images', null=True, blank=True)
    
    # Subject fields
    number_of_people = models.ForeignKey(NumberOfPeopleOption, on_delete=models.SET_NULL, related_name='images', null=True, blank=True)
    gender = models.ForeignKey(GenderOption, on_delete=models.SET_NULL, related_name='images', null=True, blank=True)
    age = models.ForeignKey(AgeOption, on_delete=models.SET_NULL, related_name='images', null=True, blank=True)
    ethnicity = models.ForeignKey(EthnicityOption, on_delete=models.SET_NULL, related_name='images', null=True, blank=True)
    
    # Camera fields
    frame_size = models.ForeignKey(FrameSizeOption, on_delete=models.SET_NULL, related_name='images', null=True, blank=True)
    shot_type = models.ForeignKey(ShotTypeOption, on_delete=models.SET_NULL, related_name='images', null=True, blank=True)
    composition = models.ForeignKey(CompositionOption, on_delete=models.SET_NULL, related_name='images', null=True, blank=True)
    lens_size = models.ForeignKey(LensSizeOption, on_delete=models.SET_NULL, related_name='images', null=True, blank=True)
    lens_type = models.ForeignKey(LensTypeOption, on_delete=models.SET_NULL, related_name='images', null=True, blank=True)
    
    # Lighting fields
    lighting = models.ForeignKey(LightingOption, on_delete=models.SET_NULL, related_name='images', null=True, blank=True)
    lighting_type = models.ForeignKey(LightingTypeOption, on_delete=models.SET_NULL, related_name='images', null=True, blank=True)
    
    # Equipment fields
    camera_type = models.ForeignKey(CameraTypeOption, on_delete=models.SET_NULL, related_name='images', null=True, blank=True)
    camera = models.ForeignKey(CameraOption, on_delete=models.SET_NULL, related_name='images', null=True, blank=True)
    lens = models.ForeignKey(LensOption, on_delete=models.SET_NULL, related_name='images', null=True, blank=True)
    film_stock = models.ForeignKey(FilmStockOption, on_delete=models.SET_NULL, related_name='images', null=True, blank=True)
    resolution = models.ForeignKey(ResolutionOption, on_delete=models.SET_NULL, related_name='images', null=True, blank=True)
    frame_rate = models.ForeignKey(FrameRateOption, on_delete=models.SET_NULL, related_name='images', null=True, blank=True)
    
    # Location fields
    location = models.ForeignKey(LocationOption, on_delete=models.SET_NULL, related_name='images', null=True, blank=True)
    setting = models.ForeignKey(SettingOption, on_delete=models.SET_NULL, related_name='images', null=True, blank=True)
    filming_location = models.ForeignKey(FilmingLocationOption, on_delete=models.SET_NULL, related_name='images', null=True, blank=True)
    location_type = models.ForeignKey(LocationTypeOption, on_delete=models.SET_NULL, related_name='images', null=True, blank=True)
    
    # People fields
    actor = models.ForeignKey(ActorOption, on_delete=models.SET_NULL, related_name='images', null=True, blank=True)
    director = models.ForeignKey(DirectorOption, on_delete=models.SET_NULL, related_name='images', null=True, blank=True)
    cinematographer = models.ForeignKey(CinematographerOption, on_delete=models.SET_NULL, related_name='images', null=True, blank=True)
    editor = models.ForeignKey(EditorOption, on_delete=models.SET_NULL, related_name='images', null=True, blank=True)
    colorist = models.ForeignKey(ColoristOption, on_delete=models.SET_NULL, related_name='images', null=True, blank=True)
    costume_designer = models.ForeignKey(CostumeDesignerOption, on_delete=models.SET_NULL, related_name='images', null=True, blank=True)
    production_designer = models.ForeignKey(ProductionDesignerOption, on_delete=models.SET_NULL, related_name='images', null=True, blank=True)
    artist = models.ForeignKey(ArtistOption, on_delete=models.SET_NULL, related_name='images', null=True, blank=True)
    
    # Additional fields
    shot_time = models.ForeignKey(ShotTimeOption, on_delete=models.SET_NULL, related_name='images', null=True, blank=True)
    description_filter = models.ForeignKey(DescriptionOption, on_delete=models.SET_NULL, related_name='images', null=True, blank=True)
    vfx_backing = models.ForeignKey(VfxBackingOption, on_delete=models.SET_NULL, related_name='images', null=True, blank=True)
    shade = models.ForeignKey(ShadeOption, on_delete=models.SET_NULL, related_name='images', null=True, blank=True)
    year = models.ForeignKey(YearOption, on_delete=models.SET_NULL, related_name='images', null=True, blank=True)
    
    # Flags
    prompt = models.TextField(blank=True)
    is_active = models.BooleanField(default=True, db_index=True)
    exclude_nudity = models.BooleanField(default=False)
    exclude_violence = models.BooleanField(default=False)
    
    # Timestamps
    created_at = models.DateTimeField(auto_now_add=True, db_index=True)
    updated_at = models.DateTimeField(auto_now=True)

    # Manager
    objects = ImageManager()

    class Meta:
        ordering = ['-created_at']
        verbose_name = "Image"
        verbose_name_plural = "Images"
        indexes = [
            models.Index(fields=['created_at'], name='image_created_idx'),
            models.Index(fields=['movie', 'created_at'], name='image_movie_created'),
            models.Index(fields=['shot_type', 'lighting'], name='image_shot_lighting'),
            models.Index(fields=['color', 'lighting'], name='image_color_lighting'),
            models.Index(fields=['primary_color_hex'], name='image_primary_color'),
            models.Index(fields=['is_active', 'created_at'], name='image_active_created'),
        ]

    def __str__(self):
        return self.title or str(self.id)

    def get_absolute_url(self):
        return reverse('image-detail', kwargs={'slug': self.slug})

    def save(self, *args, **kwargs):
        if not self.slug:
            if self.movie and self.image_url:
                import os
                filename = os.path.basename(self.image_url)
                shot_id = os.path.splitext(filename)[0]
                movie_slug = self.movie.slug
                self.slug = f"{movie_slug}-{shot_id.lower()}"
            else:
                base_slug = slugify(self.title) if self.title else str(self.id)[:12]
                self.slug = f"{base_slug}-{uuid.uuid4().hex[:8]}"
        
        is_new = self.pk is None
        super().save(*args, **kwargs)
        
        # Update movie image count if new
        if is_new and self.movie:
            self.movie.update_image_count()
        
        # Invalidate caches
        self.invalidate_cache()

    def invalidate_cache(self):
        """Invalidate image-related caches"""
        cache.delete(f"image_{self.pk}")
        cache.delete(f"image_slug_{self.slug}")
        if self.movie:
            self.movie.invalidate_cache()

    def analyze_colors(self, force=False):
        """
        Analyze image colors from URL
        Use force=True to re-analyze even if already analyzed
        """
        if not force and self.primary_color_hex:
            logger.info(f"Image {self.id} already has color analysis")
            return True

        try:
            response = requests.get(self.image_url, timeout=15, stream=True)
            response.raise_for_status()

            image = PILImage.open(BytesIO(response.content))
            if image.mode != 'RGB':
                image = image.convert('RGB')

            # Resize for performance
            image = image.resize((200, 200), PILImage.LANCZOS)
            pixels = list(image.getdata())

            # Analyze colors
            color_counts = Counter(pixels)
            dominant_colors_raw = color_counts.most_common(10)
            total_pixels = len(pixels)

            dominant_colors = []
            primary_colors_list = []
            search_terms = set()

            for i, (rgb, count) in enumerate(dominant_colors_raw[:5]):
                percentage = (count / total_pixels) * 100
                hex_color = f"#{rgb[0]:02x}{rgb[1]:02x}{rgb[2]:02x}"
                color_name = self.get_color_name(rgb)
                hsl = self.rgb_to_hsl(rgb)

                color_data = {
                    'rgb': list(rgb),
                    'hex': hex_color,
                    'percentage': round(percentage, 2),
                    'color_name': color_name,
                    'hsl': hsl
                }
                dominant_colors.append(color_data)

                primary_color = {
                    'rank': i + 1,
                    'hex': hex_color,
                    'percentage': round(percentage, 2),
                    'rgb': list(rgb),
                    'color_name': color_name,
                    'hsl': hsl,
                    'is_main': i == 0
                }
                primary_colors_list.append(primary_color)

                search_terms.add(color_name.lower())
                search_terms.add(hex_color.lower())

                if i == 0:
                    self.primary_color_hex = hex_color

            # Generate samples
            color_samples = self.sample_image_colors(image)
            
            # Color temperature
            if dominant_colors:
                hue = dominant_colors[0]['hsl']['hue']
                if 0 <= hue <= 60 or hue >= 300:
                    self.color_temperature = 'warm'
                elif 180 <= hue <= 240:
                    self.color_temperature = 'cool'
                else:
                    self.color_temperature = 'neutral'
                
                self.hue_range = f"{max(0, hue-30)}-{min(360, hue+30)}"

            # Store results
            self.dominant_colors = dominant_colors
            self.primary_colors = primary_colors_list
            self.color_samples = color_samples
            self.color_search_terms = list(search_terms)
            self.color_palette = {
                'dominant': dominant_colors,
                'primary_colors': primary_colors_list,
                'samples': color_samples,
                'temperature': self.color_temperature,
                'hue_range': self.hue_range
            }

            self.save(update_fields=[
                'dominant_colors', 'primary_color_hex', 'primary_colors',
                'color_samples', 'color_search_terms', 'color_palette',
                'color_temperature', 'hue_range'
            ])

            logger.info(f"Successfully analyzed colors for image {self.id}")
            return True

        except Exception as e:
            logger.error(f"Error analyzing colors for {self.id}: {e}")
            return False

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

        if brightness < 40:
            return "black"
        elif brightness > 215:
            return "white"
        elif r > g + 50 and r > b + 50:
            return "red"
        elif g > r + 50 and g > b + 50:
            return "green"
        elif b > r + 50 and b > g + 50:
            return "blue"
        elif r > 150 and g > 150 and b < 100:
            return "yellow"
        elif r > 150 and b > 150 and g < 100:
            return "magenta"
        elif g > 150 and b > 150 and r < 100:
            return "cyan"
        elif r > g and r > b:
            return "orange" if g > b else "red"
        elif g > r and g > b:
            return "lime" if g > 200 else "green"
        elif b > r and b > g:
            return "blue"
        else:
            return "gray"

    @staticmethod
    def sample_image_colors(image):
        """Sample colors from different parts of the image"""
        width, height = image.size
        samples = []

        positions = [
            (width//4, height//4), (width//2, height//4), (3*width//4, height//4),
            (width//4, height//2), (width//2, height//2), (3*width//4, height//2),
            (width//4, 3*height//4), (width//2, 3*height//4), (3*width//4, 3*height//4),
            (width//3, height//3)
        ]

        for i, (x, y) in enumerate(positions):
            if x < width and y < height:
                try:
                    pixel = image.getpixel((x, y))
                    if isinstance(pixel, int):
                        pixel = (pixel, pixel, pixel)
                    
                    hex_color = f"#{pixel[0]:02x}{pixel[1]:02x}{pixel[2]:02x}"
                    samples.append({
                        'position': i + 1,
                        'hex': hex_color,
                        'rgb': list(pixel)
                    })
                except Exception as e:
                    logger.warning(f"Error sampling color at {x},{y}: {e}")

        return samples

    @staticmethod
    def hex_to_rgb(hex_color):
        """Convert hex color to RGB tuple"""
        hex_color = hex_color.lstrip('#')
        return tuple(int(hex_color[i:i+2], 16) for i in (0, 2, 4))

    @staticmethod
    def color_distance(hex1, hex2):
        """Calculate color distance (simple Euclidean)"""
        try:
            rgb1 = Image.hex_to_rgb(hex1)
            rgb2 = Image.hex_to_rgb(hex2)
            return math.sqrt(sum((a - b) ** 2 for a, b in zip(rgb1, rgb2)))
        except:
            return 999
