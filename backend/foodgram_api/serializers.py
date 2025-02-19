"""
Файл содержит сериализаторы для обработки всего, что связано с рецептом:
    созданием и редактированием, а также мини сериализатор который также
    использыется в подписках.
    сериализаторы ингридиентов и тегов.
все сериализаторы с пользователем содержатся в foodgram_users:
работа с аватаром, редактирование пароля, подписки на других пользователей
"""
import random
import string

from django.contrib.auth import get_user_model
from drf_extra_fields.fields import Base64ImageField
from foodgram_app.models import Ingredient, IngredientRecipe, Recipe, Tag
from foodgram_users.serializers import CorreсtAndSeeUserSerializer
from rest_framework import serializers
from rest_framework.exceptions import ValidationError

MIN_AMOUNT = 1        # г,мл, кг, капля (дробных значений не предусмотрено?)

User = get_user_model()


class TagSerializer(serializers.ModelSerializer):
    """
    Сериалайзер используется в запросах:
    список тегов api/tags/
    метка тегов присутсвует на:
            Главной страницы,
            Страница пользователя, Избранное, создание рецепта - все
            и для редактирования рецепта(
                состояния выбора тега должно быть сохранено(
                    множественный выбор
                )
            )
    обращение к определённому тегу api/tags/{id}/
    фильтрация тега рецепта, может быть выбрано несколько
            одновременное совпадение для поиска по условиям выбора
        используется для:
            отображения на превью картинки:
                в списке рецептов, Страница пользователя, избранное
            страница рецепта - отображение множественных тегов возможно.
            для редактирования рецепта - состояния тега должно быть сохранено.
    """
    class Meta:
        model = Tag
        fields = ['id', 'name', 'slug',]


class IngredientSerializer(serializers.ModelSerializer):
    """
    Сериалайзер ингридиентов, обрабатывает данные для ингридиентов
    с разными единицами систем измерения
    адреса обработки для вьюсета------- api/ingredients/; api/ingredients/{id}/
    Используется название ингридиента в форме
        Список покупок отображение - без количества и единиц измерения
    """
    class Meta:
        model = Ingredient
        fields = ['id', 'name', 'measurement_unit']


class IngredientCreateRecipeSerializer(serializers.Serializer):
    """
    Сериализатор промежуточной модели, связывающей рецепт и ингредиент
    и указывающей количество ингредиентов в рецепте.
    """
    id = serializers.IntegerField()
    amount = serializers.IntegerField(min_value=MIN_AMOUNT)

    class Meta:
        model = IngredientRecipe
        fields = ['id', 'amount']

    def validate_amount(self, value):
        """Проверка минимального количества ингредиентов"""
        if value < MIN_AMOUNT:
            raise serializers.ValidationError(
                'Количество ингредиента должно быть больше 0.'
            )
        return value


class IngredientRecipeSerializer(serializers.ModelSerializer):
    """
    Сериализатор промежуточной модели, связывающей рецепт и ингредиент
    и указывающей количество ингредиентов в рецепте.
    """
    id = serializers.ReadOnlyField(source='ingredient.id')
    name = serializers.ReadOnlyField(source='ingredient.name')
    measurement_unit = serializers.ReadOnlyField(
        source='ingredient.measurement_unit')

    class Meta:
        model = IngredientRecipe
        fields = ('id', 'name', 'measurement_unit', 'amount')


class CreateRecipeSerializer(serializers.ModelSerializer):
    """Сериализатор для создания, обновления и валидации о рецептов"""
    ingredients = IngredientCreateRecipeSerializer(
        many=True,
    )
    tags = serializers.PrimaryKeyRelatedField(
        queryset=Tag.objects.all(),
        many=True,
    )
    author = CorreсtAndSeeUserSerializer(read_only=True)
    image = Base64ImageField(required=True, allow_null=False)

    class Meta:
        model = Recipe
        fields = ['id', 'ingredients', 'tags', 'image', 'name', 'author',
                  'text', 'cooking_time']

    def tags_and_ingredients_set(self, recipe, tags, ingredients):
        recipe.tags.set(tags)
        IngredientRecipe.objects.bulk_create(
            [IngredientRecipe(
                recipe=recipe,
                ingredient=Ingredient.objects.get(pk=ingredient['id']),
                amount=ingredient['amount']
            ) for ingredient in ingredients]
        )

    def validate(self, data):
        """
        Валидация полей (проверка ingredients, tags).
        Если ингредиентов нет или amount < 1, ---> 400 Bad Request.
        """
        if not data.get('image'):
            raise serializers.ValidationError(
                {'image': 'Нужно добавить файл с изображением.'})
        ingredients = data.get('ingredients')
        if not ingredients:
            raise ValidationError(
                {'ingredients':
                 'В рецепт надо добавить хотя бы один ингредиент.'}
            )
        ingredients_list = []
        for ingredient in ingredients:
            if ingredient['amount'] < MIN_AMOUNT:
                raise ValidationError(
                    {'ingredients':
                     'Количество каждого ингредиента должно быть >= 1.'}
                )
            ingredient_id = ingredient.get('id')
            if not Ingredient.objects.filter(pk=ingredient_id).exists():
                raise ValidationError(
                    {'ingredients': f'Ингредиента с id={ingredient_id} \
                     не существует.'}
                )
            if ingredient not in ingredients_list:
                ingredients_list.append(ingredient)
            else:
                raise ValidationError({
                    'ingredients': 'Ингридиенты не могут повторяться!'
                })
        data['ingredients'] = ingredients

        tags = data.get('tags')
        if not tags:
            raise serializers.ValidationError(
                "Проверьте, что в рецепт добавлен хотя бы один тег"
            )
        if len(tags) != len(set(tags)):
            raise serializers.ValidationError("Теги должны быть уникальными")
        data['tags'] = tags
        return data

    def create(self, validated_data):
        """Создание нового рецепта с привязкой тегов и ингредиентов."""
        tags = validated_data.pop('tags')
        ingredients = validated_data.pop('ingredients')
        recipe = Recipe.objects.create(
            author=self.context['request'].user,
            **validated_data
        )
        self.tags_and_ingredients_set(recipe, tags, ingredients)
        return recipe

    def update(self, instance, validated_data):
        """
        Обновляет поля рецепта и заново привязывает ингредиенты и теги.
        """
        tags = validated_data.pop('tags', None)
        ingredients = validated_data.pop('ingredients', None)
        instance.image = validated_data.get('image', instance.image)
        instance.name = validated_data.get('name', instance.name)
        instance.text = validated_data.get('text', instance.text)
        instance.cooking_time = validated_data.get('cooking_time',
                                                   instance.cooking_time)
        IngredientRecipe.objects.filter(recipe=instance).delete()
        self.tags_and_ingredients_set(instance, tags, ingredients)

        instance.save()
        return instance

    def bulk_create_ingredients(self, ingredients, instance):
        """Вспомогательный метод для заполнения IngredientRecipe."""
        IngredientRecipe.objects.bulk_create([
            IngredientRecipe(
                recipe=instance,
                ingredient=Ingredient.objects.get(pk=ingredient['id']),
                amount=ingredient['amount']
            )
            for ingredient in ingredients
        ])

    def to_representation(self, instance):
        return RecipeSerializer(instance, context=self.context).data


class RecipeSerializer(serializers.ModelSerializer):
    tags = TagSerializer(read_only=True, many=True,)
    author = CorreсtAndSeeUserSerializer(read_only=True)
    image = Base64ImageField(required=True)
    ingredients = IngredientRecipeSerializer(many=True, read_only=True,
                                             source='ingredient_recipe')
    is_favorited = serializers.SerializerMethodField()
    is_in_shopping_cart = serializers.SerializerMethodField()

    class Meta:
        model = Recipe
        fields = [
            'id', 'tags', 'author', 'ingredients', 'is_favorited',
            'is_in_shopping_cart', 'name', 'image', 'text', 'cooking_time'
        ]

    def get_is_favorited(self, obj):
        """
        Проверяет, находится ли текущий рецепт в избранном у пользователя.
        """
        user = self.context['request'].user
        if user.is_anonymous:
            return False
        return user.favorite_recipes.filter(recipe=obj).exists()

    def get_is_in_shopping_cart(self, obj):
        """Проверяет, есть ли текущий рецепт в корзине у пользователя."""
        user = self.context['request'].user
        if user.is_anonymous:
            return False
        return user.shoppingcart_recipes.filter(recipe=obj).exists()


class ListRecipeSerializer(serializers.ModelSerializer):
    """
    Сериалайзер для страницы мои подписки. Импортируюется в Users.
    мини карточка рецепта в списке авторов
    """
    image = Base64ImageField()

    class Meta:
        model = Recipe
        fields = ['id', 'name', 'image', 'cooking_time']
