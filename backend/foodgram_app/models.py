import random
import string

from django.apps import apps
from django.contrib.auth import get_user_model
from django.core.validators import MaxValueValidator, MinValueValidator
from django.db import models
from django.shortcuts import redirect

from rest_framework import generics

from .constants import (
    INGR_MAX_LENGTH,
    MAX_AMOUNT,
    MAX_COOKING_TIME,
    MEASUREMENT_MAX_LENGTH,
    MIN_AMOUNT,
    MIN_COOKING_TIME,
    RECIPE_NAME_MAX_LENGTH,
    TAG_MAX_LENGTH,
)

User = get_user_model()


class RecipeShortLinkView(generics.GenericAPIView):
    """ Позволяет открыть рецепт по короткой ссылке:
    https://foodgramlar.viewdns.net/s/<short_link>
    Позволяет перейти на рецепт по короткой ссылке `/s/<short_link>/`.
    """
    def get(self, request, short_link):
        try:
            recipe = Recipe.objects.get(short_link=short_link)
        except Recipe.DoesNotExist:
            return redirect('/404')
        frontend_url = f"/recipes/{recipe.id}/"
        return redirect(frontend_url)


class Tag(models.Model):
    """Дополнительная модель для сортировки."""
    name = models.CharField('Название тега',
                            max_length=TAG_MAX_LENGTH, unique=True)
    slug = models.SlugField('Slug',
                            max_length=TAG_MAX_LENGTH, unique=True,)

    class Meta:
        ordering = ('name',)
        verbose_name = 'Тег'
        verbose_name_plural = 'Теги'

    def __str__(self):
        return self.name


class Ingredient(models.Model):
    """Модель списка ингридиентов и единиц измерения."""
    name = models.CharField(
        'Название ингридиента', max_length=INGR_MAX_LENGTH, unique=True
    )
    measurement_unit = models.CharField(
        'Единица измерения', max_length=MEASUREMENT_MAX_LENGTH
    )

    class Meta:
        ordering = ['name']
        verbose_name = 'Ингридиент'
        verbose_name_plural = 'Ингридиенты'
        constraints = [
            models.UniqueConstraint(
                fields=['name', 'measurement_unit'],
                name='%(app_label)s_%(class)s_unique_ingredient'
            )
        ]

    def __str__(self):
        return self.name


class Recipe(models.Model):
    """Модель для отображения рецепта."""
    tags = models.ManyToManyField(
        Tag,
        related_name='recipe',
        verbose_name='Теги')
    author = models.ForeignKey(
        User, on_delete=models.CASCADE,
        related_name='recipe',
        verbose_name='Автор')    # user-author-создатель рецепта
    ingredients = models.ManyToManyField(
        Ingredient,
        through='IngredientRecipe',
        related_name='recipes',
        verbose_name='Ингридиенты рецепта')
    name = models.CharField(
        max_length=RECIPE_NAME_MAX_LENGTH,
        verbose_name='Название рецепта')
    image = models.ImageField(
        upload_to='foodgram_app/images/',
        blank=False,
        verbose_name='Фото еды по рецепту', )
    text = models.TextField(
        verbose_name='Описание рецепта')
    cooking_time = models.PositiveSmallIntegerField(
        verbose_name='Время приготовления',
        validators=[
            MinValueValidator(
                MIN_COOKING_TIME,
                message='Время приготовления должно быть >= 1'),
            MaxValueValidator(
                MAX_COOKING_TIME,
                message='Слишком большое время приготовления.'),
        ],
    )
    pub_date = models.DateTimeField(
        verbose_name='Дата создания', auto_now_add=True)
    short_link = models.URLField(
        verbose_name='Короткая ссылка',
        unique=True
    )

    class Meta:
        verbose_name = 'Рецепт'
        verbose_name_plural = 'Рецепты'
        ordering = ('-pub_date',)

    @staticmethod
    def generate_short_code(length=3):
        """
        Генерирует случайную строку из символов a-z, A-Z, 0-9.
        """
        letters_digits = string.ascii_letters + string.digits
        return ''.join(random.choice(letters_digits) for _ in range(length))

    @staticmethod
    def generate_unique_short_code(length=3):
        """
        Генерирует короткую ссылку, уникальную для модели Recipe,
        проверяя, что такой short_link не существует в БД.
        """
        RecipeModel = apps.get_model('foodgram_app', 'Recipe')
        while True:
            code = Recipe.generate_short_code(length)
            if not RecipeModel.objects.filter(short_link=code).exists():
                return code

    def save(self, *args, **kwargs):
        """
        Переопределяет метод сохранения,
        если поле short_link пустое (blank), генерируем
        новую уникальную короткую ссылку.
        """
        if not self.short_link:
            self.short_link = self.generate_unique_short_code(3)
        super().save(*args, **kwargs)

    def __str__(self):
        return self.name


class IngredientRecipe(models.Model):
    """
    Промежуточная модель связывает рецепт и ингредиент,
    добавляет количество ингридиентов в рецепт.
    """
    recipe = models.ForeignKey(
        Recipe, on_delete=models.CASCADE,
        related_name='ingredient_recipe',
        verbose_name='Название рецепта')
    ingredient = models.ForeignKey(
        Ingredient, on_delete=models.CASCADE,
        related_name='ingredient_recipe',
        verbose_name='Ингридиент')
    amount = models.PositiveSmallIntegerField(
        verbose_name='Количество',
        validators=[
            MinValueValidator(
                MIN_AMOUNT, 'Ингиридиентов должен быть больше 0'),
            MaxValueValidator(
                MAX_AMOUNT, 'Слишком много ингридиентов'),
        ],
    )

    class Meta:
        verbose_name = 'Связь Рецепт-Ингредиент'
        verbose_name_plural = 'Связи Рецепт-Ингредиент'
        constraints = [
            models.UniqueConstraint(
                fields=['recipe', 'ingredient'],
                name='unique_recipe_ingredient'
            )
        ]

    def __str__(self):
        return f'{self.recipe} связан {self.ingredient} - {self.amount}'


class UserRecipeRelation(models.Model):
    """
    Абстрактная модель для связи "пользователь - рецепт".
    Повторяющиеся поля и настройки.
    """
    user = models.ForeignKey('foodgram_users.User', on_delete=models.CASCADE)
    recipe = models.ForeignKey('Recipe', on_delete=models.CASCADE)

    class Meta:
        abstract = True
        constraints = [
            models.UniqueConstraint(
                fields=['recipe', 'user'],
                name='%(app_label)s_%(class)s_unique'
            )
        ]
        ordering = ('recipe', 'user',)

    def __str__(self):
        return f'{self.user} — {self.recipe}'


class Favorite(UserRecipeRelation):
    """
    Модель "Избранное". Общая часть вынесена в модель UserRecipeRelation,
    чтобы не дублировать поля recipe и user.
    """
    class Meta(UserRecipeRelation.Meta):
        default_related_name = 'favorite_recipes'
        verbose_name = 'Избранный рецепт'
        verbose_name_plural = 'Избранные рецепты'


class ShoppingCart(UserRecipeRelation):
    """
    Модель "Список покупок". Общая часть вынесена в модель UserRecipeRelation,
    чтобы не дублировать поля recipe и user.
    """
    class Meta(UserRecipeRelation.Meta):
        default_related_name = 'shoppingcart_recipes'
        verbose_name = 'Рецепт в корзине'
        verbose_name_plural = 'Рецепты в корзине'
