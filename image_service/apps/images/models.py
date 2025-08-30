from django.db import models

class Movie(models.Model):
    title = models.CharField(max_length=255)
    year = models.IntegerField(null=True, blank=True)

    class Meta:
        ordering = ['-year', 'title']
        verbose_name = "Movie"
        verbose_name_plural = "Movies"

    def __str__(self):
        return self.title

class Tag(models.Model):
    name = models.CharField(max_length=100, unique=True)

    class Meta:
        ordering = ['name']
        verbose_name = "Tag"
        verbose_name_plural = "Tags"
    
    def __str__(self):
        return self.name

class Image(models.Model):
    class MediaType(models.TextChoices):
        MOVIE = 'movie', 'Movie'
        COMMERCIAL = 'commercial', 'Commercial'
        MUSIC_VIDEO = 'music_video', 'Music Video'
        SHORT_FILM = 'short_film', 'Short Film'
        TV = 'tv', 'TV'

    class Genre(models.TextChoices):
        ACTION = 'action', 'Action'
        DRAMA = 'drama', 'Drama'
        COMEDY = 'comedy', 'Comedy'
        HORROR = 'horror', 'Horror'
        SCI_FI = 'sci_fi', 'Sci-Fi'
        DOCUMENTARY = 'documentary', 'Documentary'
        HIP_HOP = 'hip_hop', 'Hip Hop'
        CAR = 'car', 'Car'

    class Color(models.TextChoices):
        WARM = 'warm', 'Warm'
        COOL = 'cool', 'Cool'
        NEUTRAL = 'neutral', 'Neutral'
        MONOCHROME = 'monochrome', 'Monochrome'
        VIBRANT = 'vibrant', 'Vibrant'

    class AspectRatio(models.TextChoices):
        RATIO_1_33 = '1.33', '1.33'
        RATIO_1_78 = '1.78', '1.78'
        RATIO_2_39 = '2.39', '2.39'
        RATIO_1_1 = '1:1', '1:1'

    class OpticalFormat(models.TextChoices):
        ANAMORPHIC = 'anamorphic', 'Anamorphic'
        SPHERICAL = 'spherical', 'Spherical'
        SUPER_35 = 'super_35', 'Super 35'

    class Format(models.TextChoices):
        FILM_35MM = 'film_35mm', 'Film 35mm'
        FILM_16MM = 'film_16mm', 'Film 16mm'
        DIGITAL = 'digital', 'Digital'

    class InteriorExterior(models.TextChoices):
        INTERIOR = 'interior', 'Interior'
        EXTERIOR = 'exterior', 'Exterior'

    class TimeOfDay(models.TextChoices):
        DAY = 'day', 'Day'
        NIGHT = 'night', 'Night'
        DUSK = 'dusk', 'Dusk'
        DAWN = 'dawn', 'Dawn'

    class NumberOfPeople(models.TextChoices):
        NONE = 'none', 'None'
        ONE = 'one', 'One'
        FEW = 'few', 'Few'
        CROWD = 'crowd', 'Crowd'

    class Gender(models.TextChoices):
        MALE = 'male', 'Male'
        FEMALE = 'female', 'Female'
        MIXED = 'mixed', 'Mixed'

    class Age(models.TextChoices):
        CHILD = 'child', 'Child'
        TEEN = 'teen', 'Teen'
        ADULT = 'adult', 'Adult'
        ELDERLY = 'elderly', 'Elderly'

    class Ethnicity(models.TextChoices):
        CAUCASIAN = 'caucasian', 'Caucasian'
        AFRICAN = 'african', 'African'
        ASIAN = 'asian', 'Asian'
        LATINO = 'latino', 'Latino'
        MIDDLE_EASTERN = 'middle_eastern', 'Middle Eastern'

    class FrameSize(models.TextChoices):
        CLOSE = 'close', 'Close'
        MEDIUM = 'medium', 'Medium'
        WIDE = 'wide', 'Wide'

    class ShotType(models.TextChoices):
        AERIAL = 'aerial', 'Aerial'
        HIGH_ANGLE = 'high_angle', 'High Angle'
        LOW_ANGLE = 'low_angle', 'Low Angle'
        EYE_LEVEL = 'eye_level', 'Eye Level'

    class Composition(models.TextChoices):
        SYMMETRICAL = 'symmetrical', 'Symmetrical'
        ASYMMETRICAL = 'asymmetrical', 'Asymmetrical'
        RULE_OF_THIRDS = 'rule_of_thirds', 'Rule of Thirds'

    class LensSize(models.TextChoices):
        WIDE = 'wide', 'Wide'
        NORMAL = 'normal', 'Normal'
        TELEPHOTO = 'telephoto', 'Telephoto'

    class LensType(models.TextChoices):
        PRIME = 'prime', 'Prime'
        ZOOM = 'zoom', 'Zoom'

    class Lighting(models.TextChoices):
        SOFT_LIGHT = 'soft_light', 'Soft Light'
        HARD_LIGHT = 'hard_light', 'Hard Light'
        SILHOUETTE = 'silhouette', 'Silhouette'

    class LightingType(models.TextChoices):
        NATURAL = 'natural', 'Natural'
        ARTIFICIAL = 'artificial', 'Artificial'

    class CameraType(models.TextChoices):
        DSLR = 'dslr', 'DSLR'
        MIRRORLESS = 'mirrorless', 'Mirrorless'
        FILM = 'film', 'Film'

    class Resolution(models.TextChoices):
        HD = '720p', '720p'
        FULL_HD = '1080p', '1080p'
        FOUR_K = '4k', '4k'

    class FrameRate(models.TextChoices):
        FPS_24 = '24fps', '24fps'
        FPS_30 = '30fps', '30fps'
        FPS_60 = '60fps', '60fps'

    title = models.CharField(max_length=255)
    description = models.TextField(blank=True, null=True)
    image_url = models.URLField(max_length=500)
    movie = models.ForeignKey(Movie, on_delete=models.SET_NULL, related_name='images', null=True, blank=True)
    tags = models.ManyToManyField(Tag, related_name='images', blank=True)
    release_year = models.IntegerField(null=True, blank=True)
    media_type = models.CharField(max_length=20, choices=MediaType.choices, blank=True, null=True)
    genre = models.CharField(max_length=20, choices=Genre.choices, blank=True, null=True)
    color = models.CharField(max_length=20, choices=Color.choices, blank=True, null=True)
    aspect_ratio = models.CharField(max_length=10, choices=AspectRatio.choices, blank=True, null=True)
    optical_format = models.CharField(max_length=20, choices=OpticalFormat.choices, blank=True, null=True)
    format = models.CharField(max_length=20, choices=Format.choices, blank=True, null=True)
    interior_exterior = models.CharField(max_length=20, choices=InteriorExterior.choices, blank=True, null=True)
    time_of_day = models.CharField(max_length=20, choices=TimeOfDay.choices, blank=True, null=True)
    number_of_people = models.CharField(max_length=20, choices=NumberOfPeople.choices, blank=True, null=True)
    gender = models.CharField(max_length=20, choices=Gender.choices, blank=True, null=True)
    age = models.CharField(max_length=20, choices=Age.choices, blank=True, null=True)
    ethnicity = models.CharField(max_length=20, choices=Ethnicity.choices, blank=True, null=True)
    frame_size = models.CharField(max_length=20, choices=FrameSize.choices, blank=True, null=True)
    shot_type = models.CharField(max_length=20, choices=ShotType.choices, blank=True, null=True)
    composition = models.CharField(max_length=20, choices=Composition.choices, blank=True, null=True)
    lens_size = models.CharField(max_length=20, choices=LensSize.choices, blank=True, null=True)
    lens_type = models.CharField(max_length=20, choices=LensType.choices, blank=True, null=True)
    lighting = models.CharField(max_length=20, choices=Lighting.choices, blank=True, null=True)
    lighting_type = models.CharField(max_length=20, choices=LightingType.choices, blank=True, null=True)
    camera_type = models.CharField(max_length=20, choices=CameraType.choices, blank=True, null=True)
    resolution = models.CharField(max_length=10, choices=Resolution.choices, blank=True, null=True)
    frame_rate = models.CharField(max_length=10, choices=FrameRate.choices, blank=True, null=True)
    exclude_nudity = models.BooleanField(default=False)
    exclude_violence = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['-created_at']
        verbose_name = "Image"
        verbose_name_plural = "Images"

    def __str__(self):
        return self.title