from django.contrib import admin

from . import models


class IngredientRecipeInline(admin.TabularInline):
    """
    Inline-модель, которая позволит в админке добавлять
    ингредиенты к рецепту (через модель IngredientRecipe).
    """
    model = models.IngredientRecipe
    extra = 1


@admin.register(models.Tag)
class TagAdmin(admin.ModelAdmin):
    """Админ-модель для тегов."""
    list_display = ('id', 'name', 'slug')
    search_fields = ('name', 'slug')


@admin.register(models.Ingredient)
class IngredientAdmin(admin.ModelAdmin):
    """Админ-модель для ингредиентов."""
    list_display = ('id', 'name', 'measurement_unit')
    search_fields = ('name',)
    list_filter = ('measurement_unit',)


@admin.register(models.Recipe)
class RecipeAdmin(admin.ModelAdmin):
    list_display = ('name', 'author', 'favorited_counts')
    search_fields = ('name', 'author__username')
    list_filter = ('tags',)
    filter_horizontal = ('tags',)
    inlines = [IngredientRecipeInline]
    readonly_fields = ('short_link',)

    def favorited_counts(self, obj):
        """Подсчёт, сколько раз рецепт добавляли в избранное."""
        return obj.favorite_recipes.count()
    favorited_counts.short_description = 'Добавлений в избранное'
