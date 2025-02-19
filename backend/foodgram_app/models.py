import random
import string

from django.contrib.auth import get_user_model
from django.core.validators import MinValueValidator
from django.db import models

User = get_user_model()

MIN_AMOUNT = 1        # г,мл, кг, капля (дробных значений не предусмотрено?)
MIN_COOKING_TIME = 1  # минута


def generate_short_code(length=3):
    """
    Генерирует случайную строку из символов [a-zA-Z0-9] длиной length.
    """
    letters_digits = string.ascii_letters + string.digits
    return ''.join(random.choice(letters_digits) for _ in range(length))


def generate_unique_short_code(length=3):
    """
    Генерирует короткую ссылку, гарантированно уникальную в модели Recipe.
    """
    while True:
        code = generate_short_code(length)
        if not Recipe.objects.filter(short_link=code).exists():
            return code


class Tag(models.Model):
    """Дополнительная модель для сортировки."""
    name = models.CharField('Название тега', max_length=50, unique=True)
    slug = models.SlugField('Слаг', unique=True,)

    class Meta:
        ordering = ['name']
        verbose_name = 'Тег'
        verbose_name_plural = 'Теги'

    def __str__(self):
        return self.name


class Ingredient(models.Model):
    """Модель списка ингридиентов и единиц измерения."""
    name = models.CharField('Название ингридиента',
                            max_length=100, unique=True)
    measurement_unit = models.CharField('Единица измерения',
                                        max_length=50)
    # возможно через выпадающий список, но вроде нет

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
        related_name='recipe_ingredient',
        verbose_name='Ингридиенты рецепта')
    name = models.CharField(
        max_length=256,
        verbose_name='Название рецепта')
    image = models.ImageField(
        upload_to='foodgram_app/images/',
        blank=False,
        verbose_name='Фото еды по рецепту', )
    text = models.TextField(
        verbose_name='Описание рецепта')
    cooking_time = models.PositiveSmallIntegerField(
        # может прикрутить с полем времени в
        # сериалайзере для валидации? но вроде нет
        verbose_name='Время приготовления',
        validators=[MinValueValidator(
            MIN_COOKING_TIME,
            'Время приготовления должено быть больше 0')
        ]
    )
    pub_date = models.DateTimeField(
        verbose_name='Дата создания', auto_now_add=True)
    short_link = models.URLField(
        verbose_name='Короткая ссылка',
        unique=True,
        blank=True,)

    class Meta:
        verbose_name = 'Рецепт'
        verbose_name_plural = 'Рецепты'
        ordering = ['-pub_date']

    def save(self, *args, **kwargs):
        """
        Если поле short_link пустое, генерируем новую уникальную
        короткую ссылку.
        """
        if not self.short_link:
            self.short_link = generate_unique_short_code(3)
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
        validators=[MinValueValidator(
            MIN_AMOUNT,
            'Ингиридиентов должен быть больше 0'),
        ]
    )

    def __str__(self):
        return f'рецепт {self.recipe} содержит ингридиент{self.ingredient}\
            количество {self.amount}'


class Favorite(models.Model):
    """Модель связывает избранный рецепт и пользователя."""
    recipe = models.ForeignKey(
        Recipe, on_delete=models.CASCADE,
        related_name='favorite_recipes',  # для доступа к объектам модели
        verbose_name='Рецепт')
    user = models.ForeignKey(
        User, on_delete=models.CASCADE,
        related_name='favorite_recipes',
        verbose_name='Пользователь'
    )

    class Meta:
        verbose_name = 'Выбранный рецепт'
        verbose_name_plural = 'Выбранные рецепты'
        ordering = ['recipe', 'user']
        constraints = [
            models.UniqueConstraint(
                fields=['recipe', 'user'],
                name='%(app_label)s_%(class)s_unique_favorite'
            ),
            models.CheckConstraint(
                name='%(app_label)s_%(class)s_prevent_self_favorite',
                check=~models.Q(recipe=models.F('user'))
            )
        ]

    def __str__(self):
        return f'{self.user} выбрал люимым рецептом {self.recipe}'

# модели ShoppingCart одинаковые с Favorite, но думаю с двумя моделями
# код будет наглянее


class ShoppingCart(models.Model):
    """ Модель связывает рецепт в корзине и пользователя."""
    recipe = models.ForeignKey(
        Recipe, on_delete=models.CASCADE,
        related_name='shoppingcart_recipes',
        verbose_name='Рецепт')
    user = models.ForeignKey(
        User, on_delete=models.CASCADE,
        related_name='shoppingcart_recipes',
        verbose_name='Пользователь'
    )

    class Meta:
        verbose_name = 'Выбранный рецепт'
        verbose_name_plural = 'Выбранные рецепты'
        ordering = ['recipe', 'user']
        constraints = [
            models.UniqueConstraint(
                fields=['recipe', 'user'],
                name='%(app_label)s_%(class)s_unique_shoppingcart'
            ),
            models.CheckConstraint(
                name='%(app_label)s_%(class)s_prevent_self_shoppingcart',
                check=~models.Q(recipe=models.F('user'))
            )
        ]

    def __str__(self):
        return f'{self.user} выбрал рецепт для покупки {self.recipe}'
