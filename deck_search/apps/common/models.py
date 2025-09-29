from django.db import models
from django.utils.translation import gettext_lazy as _


class Filter(models.Model):
    """
    Concrete base for all filters (name, type, format).
    بهبود: اضافه کردن index روی name و type برای کوئری‌های سریع‌تر.
    """
    name = models.CharField(max_length=255, verbose_name=_("Name"))
    type = models.CharField(max_length=50, verbose_name=_("Type"))
    format = models.TextField(verbose_name=_("Format"))
    created_at = models.DateTimeField(auto_now_add=True, verbose_name=_("Created At"))
    updated_at = models.DateTimeField(auto_now=True, verbose_name=_("Updated At"))

    class Meta:
        ordering = ['name']
        indexes = [
            models.Index(fields=['name']),
            models.Index(fields=['type']),
        ]
        verbose_name = _("Filter")
        verbose_name_plural = _("Filters")

    def __str__(self):
        return self.name

    def get_options(self, option_type=None):
        """
        متد کمکی: دریافت گزینه‌ها بر اساس نوع (اختیاری).
        """
        if option_type:
            # مثال: فیلتر بر اساس type فیلتر parent
            return self.generic_options.filter(filter__type=option_type)
        return self.generic_options.all()  # generic options (fallback)


class FilterOption(models.Model):
    """
    Abstract base for filter options.
    بهبود: index روی value؛ unique_together حفظ شد. related_name پیش‌فرض برای fallback.
    """
    filter = models.ForeignKey(
        'Filter', 
        on_delete=models.CASCADE, 
        related_name='generic_options',  # تغییر به generic برای جلوگیری از تداخل پیش‌فرض
        verbose_name=_("Filter")
    )
    value = models.CharField(max_length=255, verbose_name=_("Value"))
    label = models.CharField(max_length=255, verbose_name=_("Label"))
    slug = models.SlugField(max_length=255, blank=True, null=True, verbose_name=_("Slug"))
    created_at = models.DateTimeField(auto_now_add=True, verbose_name=_("Created At"))

    class Meta:
        abstract = True
        unique_together = ('filter', 'value')
        ordering = ['value']
        indexes = [
            models.Index(fields=['value']),
            models.Index(fields=['slug']),
        ]
        verbose_name = _("Filter Option")
        verbose_name_plural = _("Filter Options")
        # حذف constraints برای جلوگیری از تداخل نام (E032)

    def __str__(self):
        return f"{self.filter.name}: {self.label}"

    @classmethod
    def get_label_by_value(cls, filter_obj, value):
        """
        متد کلاس کمکی: دریافت label بر اساس value.
        """
        try:
            # جستجو در subclass مربوطه (نیاز به override در subclass اگر لازم باشد)
            return cls.objects.get(filter=filter_obj, value=value).label
        except cls.DoesNotExist:
            return value


# Concrete filter models (بدون تغییر، حفظ کامل)
class SearchFilter(Filter):
    class Meta:
        db_table = 'searchfilter'


class TagsFilter(Filter):
    class Meta:
        db_table = 'tagsfilter'


class MovieFilter(Filter):
    class Meta:
        db_table = 'moviefilter'


class ShadeFilter(Filter):
    class Meta:
        db_table = 'shadefilter'


# Concrete option models (رفع تداخل: تعریف دوباره filter با related_name منحصربه‌فرد؛ حفظ db_table)
class MediaTypeFilter(FilterOption):
    """
    بهبود: related_name منحصربه‌فرد برای رفع تداخل.
    """
    filter = models.ForeignKey('Filter', on_delete=models.CASCADE, related_name='media_type_options', verbose_name=_("Filter"))
    class Meta(FilterOption.Meta):
        db_table = 'filter_media_type_options'


class GenreFilter(FilterOption):
    filter = models.ForeignKey('Filter', on_delete=models.CASCADE, related_name='genre_options', verbose_name=_("Filter"))
    class Meta(FilterOption.Meta):
        db_table = 'filter_genre_options'


class TimePeriodFilter(FilterOption):
    filter = models.ForeignKey('Filter', on_delete=models.CASCADE, related_name='time_period_options', verbose_name=_("Filter"))
    class Meta(FilterOption.Meta):
        db_table = 'filter_time_period_options'


class ColorFilter(FilterOption):
    filter = models.ForeignKey('Filter', on_delete=models.CASCADE, related_name='color_options', verbose_name=_("Filter"))
    class Meta(FilterOption.Meta):
        db_table = 'filter_color_options'


class AspectRatioFilter(FilterOption):
    filter = models.ForeignKey('Filter', on_delete=models.CASCADE, related_name='aspect_ratio_options', verbose_name=_("Filter"))
    class Meta(FilterOption.Meta):
        db_table = 'filter_aspect_ratio_options'


class OpticalFormatFilter(FilterOption):
    filter = models.ForeignKey('Filter', on_delete=models.CASCADE, related_name='optical_format_options', verbose_name=_("Filter"))
    class Meta(FilterOption.Meta):
        db_table = 'filter_optical_format_options'


class LabProcessFilter(FilterOption):
    filter = models.ForeignKey('Filter', on_delete=models.CASCADE, related_name='lab_process_options', verbose_name=_("Filter"))
    class Meta(FilterOption.Meta):
        db_table = 'filter_lab_process_options'


class FormatFilter(FilterOption):
    filter = models.ForeignKey('Filter', on_delete=models.CASCADE, related_name='format_options', verbose_name=_("Filter"))
    class Meta(FilterOption.Meta):
        db_table = 'filter_format_options'


class IntExtFilter(FilterOption):
    filter = models.ForeignKey('Filter', on_delete=models.CASCADE, related_name='int_ext_options', verbose_name=_("Filter"))
    class Meta(FilterOption.Meta):
        db_table = 'filter_int_ext_options'


class TimeOfDayFilter(FilterOption):
    filter = models.ForeignKey('Filter', on_delete=models.CASCADE, related_name='time_of_day_options', verbose_name=_("Filter"))
    class Meta(FilterOption.Meta):
        db_table = 'filter_time_of_day_options'


class NumPeopleFilter(FilterOption):
    filter = models.ForeignKey('Filter', on_delete=models.CASCADE, related_name='num_people_options', verbose_name=_("Filter"))
    class Meta(FilterOption.Meta):
        db_table = 'filter_numpeople_options'


class GenderFilter(FilterOption):
    filter = models.ForeignKey('Filter', on_delete=models.CASCADE, related_name='gender_options', verbose_name=_("Filter"))
    class Meta(FilterOption.Meta):
        db_table = 'filter_gender_options'


class SubjectAgeFilter(FilterOption):
    filter = models.ForeignKey('Filter', on_delete=models.CASCADE, related_name='subject_age_options', verbose_name=_("Filter"))
    class Meta(FilterOption.Meta):
        db_table = 'filter_subject_age_options'


class SubjectEthnicityFilter(FilterOption):
    filter = models.ForeignKey('Filter', on_delete=models.CASCADE, related_name='subject_ethnicity_options', verbose_name=_("Filter"))
    class Meta(FilterOption.Meta):
        db_table = 'filter_subject_ethnicity_options'


class FrameSizeFilter(FilterOption):
    filter = models.ForeignKey('Filter', on_delete=models.CASCADE, related_name='frame_size_options', verbose_name=_("Filter"))
    class Meta(FilterOption.Meta):
        db_table = 'filter_frame_size_options'


class ShotTypeFilter(FilterOption):
    filter = models.ForeignKey('Filter', on_delete=models.CASCADE, related_name='shot_type_options', verbose_name=_("Filter"))
    class Meta(FilterOption.Meta):
        db_table = 'filter_shot_type_options'


class CompositionFilter(FilterOption):
    filter = models.ForeignKey('Filter', on_delete=models.CASCADE, related_name='composition_options', verbose_name=_("Filter"))
    class Meta(FilterOption.Meta):
        db_table = 'filter_composition_options'


class LensTypeFilter(FilterOption):
    filter = models.ForeignKey('Filter', on_delete=models.CASCADE, related_name='lens_type_options', verbose_name=_("Filter"))
    class Meta(FilterOption.Meta):
        db_table = 'filter_lens_type_options'


class LightingFilter(FilterOption):
    filter = models.ForeignKey('Filter', on_delete=models.CASCADE, related_name='lighting_options', verbose_name=_("Filter"))
    class Meta(FilterOption.Meta):
        db_table = 'filter_lighting_options'


class LightingTypeFilter(FilterOption):
    filter = models.ForeignKey('Filter', on_delete=models.CASCADE, related_name='lighting_type_options', verbose_name=_("Filter"))
    class Meta(FilterOption.Meta):
        db_table = 'filter_lighting_type_options'