# مسیر: /home/mdk/Documents/shotdeck-main/image_service/apps/images/admin.py
from django.contrib import admin
from .models import Image, Movie, Tag

@admin.register(Movie)
class MovieAdmin(admin.ModelAdmin): # <-- اصلاح شد
    list_display = ('id', 'title', 'year')
    search_fields = ('title',)

@admin.register(Tag)
class TagAdmin(admin.ModelAdmin): # <-- اصلاح شد
    list_display = ('id', 'name')
    search_fields = ('name',)

@admin.register(Image)
class ImageAdmin(admin.ModelAdmin): # <-- اصلاح شد
    list_display = ('id', 'title', 'movie', 'release_year', 'created_at')
    list_filter = ('genre', 'color', 'time_of_day', 'tags')
    search_fields = ('title', 'description', 'movie__title')
    filter_horizontal = ('tags',)
    date_hierarchy = 'created_at'