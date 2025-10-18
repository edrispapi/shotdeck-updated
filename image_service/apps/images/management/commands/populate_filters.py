from django.core.management.base import BaseCommand
from django.db import transaction
from apps.images.models import (
    Image,
    MediaTypeOption,
    GenreOption,
    ColorOption,
    AspectRatioOption,
    OpticalFormatOption,
    FormatOption,
    LabProcessOption,
    TimePeriodOption,
    InteriorExteriorOption,
    TimeOfDayOption,
    NumberOfPeopleOption,
    GenderOption,
    AgeOption,
    EthnicityOption,
    FrameSizeOption,
    ShotTypeOption,
    CompositionOption,
    LensSizeOption,
    LensTypeOption,
    LightingOption,
    LightingTypeOption,
    CameraTypeOption,
    ResolutionOption,
    FrameRateOption,
    ActorOption,
    CameraOption,
    LensOption,
    LocationOption,
    SettingOption,
    FilmStockOption,
    ShotTimeOption,
    DescriptionOption,
    VfxBackingOption,
    DirectorOption,
    CinematographerOption,
    EditorOption,
    ColoristOption,
    CostumeDesignerOption,
    ProductionDesignerOption,
    ShadeOption,
    ArtistOption,
    FilmingLocationOption,
    LocationTypeOption,
    YearOption,
)


class Command(BaseCommand):
    help = "Populate all filter options from existing Image data"

    def add_arguments(self, parser):
        parser.add_argument('--dry-run', action='store_true', help='Only show what would be created')
        parser.add_argument('--force', action='store_true', help='Clear existing options before populating')

    def handle(self, *args, **options):
        dry_run = options['dry_run']
        force = options['force']

        if force and not dry_run:
            self.stdout.write("Clearing existing filter options...")
            self._clear_all_options()

        # Define field mappings
        field_mappings = [
            ('media_type', MediaTypeOption),
            ('color', ColorOption),
            ('aspect_ratio', AspectRatioOption),
            ('optical_format', OpticalFormatOption),
            ('format', FormatOption),
            ('lab_process', LabProcessOption),
            ('time_period', TimePeriodOption),
            ('interior_exterior', InteriorExteriorOption),
            ('time_of_day', TimeOfDayOption),
            ('number_of_people', NumberOfPeopleOption),
            ('gender', GenderOption),
            ('age', AgeOption),
            ('ethnicity', EthnicityOption),
            ('frame_size', FrameSizeOption),
            ('shot_type', ShotTypeOption),
            ('composition', CompositionOption),
            ('lens_size', LensSizeOption),
            ('lens_type', LensTypeOption),
            ('lighting', LightingOption),
            ('lighting_type', LightingTypeOption),
            ('camera_type', CameraTypeOption),
            ('resolution', ResolutionOption),
            ('frame_rate', FrameRateOption),
            ('actor', ActorOption),
            ('camera', CameraOption),
            ('lens', LensOption),
            ('location', LocationOption),
            ('setting', SettingOption),
            ('film_stock', FilmStockOption),
            ('shot_time', ShotTimeOption),
            ('description_filter', DescriptionOption),
            ('vfx_backing', VfxBackingOption),
            ('director', DirectorOption),
            ('cinematographer', CinematographerOption),
            ('editor', EditorOption),
            ('colorist', ColoristOption),
            ('costume_designer', CostumeDesignerOption),
            ('production_designer', ProductionDesignerOption),
            ('shade', ShadeOption),
            ('artist', ArtistOption),
            ('filming_location', FilmingLocationOption),
            ('location_type', LocationTypeOption),
            ('year', YearOption),
        ]

        total_created = 0

        with transaction.atomic():
            # Process single-value foreign key fields
            for field_name, model_class in field_mappings:
                created = self._populate_single_field(field_name, model_class, dry_run)
                total_created += created
                self.stdout.write(f"{field_name}: {created} options")

            # Process many-to-many fields
            created = self._populate_genre_field(dry_run)
            total_created += created
            self.stdout.write(f"genre: {created} options")

            if dry_run:
                raise transaction.TransactionManagementError("Dry run rollback")

        if dry_run:
            self.stdout.write(self.style.WARNING(f"Dry run complete. Would create {total_created} filter options."))
        else:
            self.stdout.write(self.style.SUCCESS(f"Filter population complete. Created {total_created} options."))

    def _clear_all_options(self):
        """Clear all existing filter options"""
        models_to_clear = [
            MediaTypeOption, ColorOption, AspectRatioOption, OpticalFormatOption,
            FormatOption, LabProcessOption, TimePeriodOption, InteriorExteriorOption,
            TimeOfDayOption, NumberOfPeopleOption, GenderOption, AgeOption,
            EthnicityOption, FrameSizeOption, ShotTypeOption, CompositionOption,
            LensSizeOption, LensTypeOption, LightingOption, LightingTypeOption,
            CameraTypeOption, ResolutionOption, FrameRateOption, ActorOption,
            CameraOption, LensOption, LocationOption, SettingOption,
            FilmStockOption, ShotTimeOption, DescriptionOption, VfxBackingOption,
            DirectorOption, CinematographerOption, EditorOption, ColoristOption,
            CostumeDesignerOption, ProductionDesignerOption, ShadeOption,
            ArtistOption, FilmingLocationOption, LocationTypeOption, YearOption,
            GenreOption
        ]

        for model in models_to_clear:
            count = model.objects.count()
            model.objects.all().delete()
            self.stdout.write(f"Cleared {count} {model.__name__} records")

    def _populate_single_field(self, field_name, model_class, dry_run):
        """Populate options for a single foreign key field"""
        created = 0
        
        # Get all unique non-null values for this field
        values = Image.objects.filter(
            **{f"{field_name}__isnull": False}
        ).values_list(field_name, flat=True).distinct()

        for value in values:
            if value and str(value).strip():
                if not dry_run:
                    obj, created_flag = model_class.objects.get_or_create(
                        value=str(value).strip()
                    )
                    if created_flag:
                        created += 1
                else:
                    if not model_class.objects.filter(value=str(value).strip()).exists():
                        created += 1

        return created

    def _populate_genre_field(self, dry_run):
        """Populate genre options from many-to-many field"""
        created = 0
        
        # Get all unique genre values from the many-to-many relationship
        genres = GenreOption.objects.values_list('value', flat=True).distinct()
        existing_genres = set(genres)

        # Also check for any genres that might be in the Image.genre field
        image_genres = set()
        for image in Image.objects.prefetch_related('genre').all():
            for genre in image.genre.all():
                image_genres.add(genre.value)

        all_genres = existing_genres.union(image_genres)

        for genre_value in all_genres:
            if genre_value and str(genre_value).strip():
                if not dry_run:
                    obj, created_flag = GenreOption.objects.get_or_create(
                        value=str(genre_value).strip()
                    )
                    if created_flag:
                        created += 1
                else:
                    if not GenreOption.objects.filter(value=str(genre_value).strip()).exists():
                        created += 1

        return created
