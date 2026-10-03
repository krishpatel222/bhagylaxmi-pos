from django.contrib import admin
from .models import Category, Brand


@admin.register(Category)
class CategoryAdmin(admin.ModelAdmin):
    list_display = ('name', 'gujarati_name', 'slug', 'is_active', 'created_at')
    list_filter = ('is_active', 'created_at')
    search_fields = ('name', 'gujarati_name', 'slug')
    prepopulated_fields = {'slug': ('name',)}


@admin.register(Brand)
class BrandAdmin(admin.ModelAdmin):
    list_display = ('name', 'is_active', 'created_at')
    list_filter = ('is_active', 'created_at')
    search_fields = ('name',)
