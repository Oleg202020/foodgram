from django.contrib import admin

from . import models


class TagAdmin(admin.ModelAdmin):
    list_display = ('name', 'slug',)


class IngredientAdmin(admin.ModelAdmin):
    list_display = ('name', 'measurement_unit')
    search_fields = ('name',)


class RecipeAdmin(admin.ModelAdmin):
    list_display = ('name', 'author', 'favorited_counts')
    search_fields = ('name', 'author')
    list_filter = ('tags',)
    filter_horizontal = ('tags',)

    def favorited_counts(self, obj):
        return obj.favorite_recipes.count()

    favorited_counts.short_description = 'Количество в избранном'


admin.site.register(models.Tag, TagAdmin)
admin.site.register(models.Ingredient, IngredientAdmin)
admin.site.register(models.Recipe, RecipeAdmin)
