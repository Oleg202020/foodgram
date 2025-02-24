"""
Файл содержит сериализаторы для обработки всего, что связано с рецептом:
    созданием и редактированием, а также мини сериализатор который также
    использыется в подписках.
    сериализаторы ингридиентов и тегов.
все сериализаторы с пользователем содержатся в foodgram_users:
работа с аватаром, редактирование пароля, подписки на других пользователей
"""
from drf_extra_fields.fields import Base64ImageField

from django.contrib.auth import get_user_model
from django.db import transaction
from rest_framework import serializers
from rest_framework.exceptions import ValidationError
from rest_framework.fields import SerializerMethodField
from rest_framework.validators import UniqueTogetherValidator

from foodgram_app.constants import MIN_AMOUNT
from foodgram_app.models import Ingredient, IngredientRecipe, Recipe, Tag
from foodgram_users.models import Follow

User = get_user_model()


class RegistrationUserSerializer(serializers.ModelSerializer):
    """
    Сериализатор для регистрации пользователя
    Используемые адреса:
        Регистрация пользователя   api/users/  POST
    """
    class Meta:
        model = User
        fields = [
            'id',
            'email',
            'username',
            'first_name',
            'last_name',
            'password',
        ]
        extra_kwargs = {
            'password': {'write_only': True}
        }

    def create(self, validated_data):
        return User.objects.create_user(**validated_data)


class UserAvatarSerializer(serializers.ModelSerializer):
    """Сериализатор для работы с аватаром."""
    avatar = Base64ImageField(required=True)

    class Meta:
        model = User
        fields = ('avatar', )

    def validate(self, attrs):
        if not attrs.get('avatar'):
            raise serializers.ValidationError('Нет фото для аватара!')
        return attrs


class UserDetailSerializer(serializers.ModelSerializer):
    """
    Сериализатор для просмотра и редактирования данных пользователя.
    Используемые адреса:
        Получение списка пользователей   /users/         GET
        Регистрация пользователя         /users/         POST
        Профиль текущего пользователя    /users/me/      GET/PUT/PATCH
        Отдельный пользователь           /users/{id}/    GET/PUT/PATCH/DELETE
    """
    is_subscribed = SerializerMethodField(read_only=True)

    class Meta:
        model = User
        fields = [
            'id',
            'email',
            'username',
            'first_name',
            'last_name',
            'is_subscribed',
            'avatar'
        ]
        read_only_fields = ('avatar',)

    def get_is_subscribed(self, obj):
        """Возвращает True если пользователь подписан на автора."""
        request = self.context.get('request')
        return (
            request
            and not request.user.is_anonymous
            and request.user.subscriptions.filter(author=obj).exists()
        )


class FollowSerializer(UserDetailSerializer):
    """Сериализатор для отображения информации о подписках."""
    recipes = SerializerMethodField()
    recipes_count = SerializerMethodField()

    class Meta:
        model = User
        fields = [
            'id',
            'username',
            'first_name',
            'last_name',
            'email',
            'is_subscribed',
            'avatar',
            'recipes_count',
            'recipes'
        ]

    def get_recipes(self, obj):
        """Возвращает сериализованные данные о рецептах автора.
        Параметр recipes_limit использовуется, для ограничения
        количества рецептов.
        """
        recipes_author = obj.recipes.all()
        request = self.context.get('request')
        if request is not None:
            limit_param = request.query_params.get('recipes_limit')
            if limit_param:
                try:
                    limit = int(limit_param)
                    recipes_author = recipes_author[:limit]
                except ValueError:
                    pass
        return ListRecipeSerializer(recipes_author, many=True,
                                    context={'request': request}).data

    def get_recipes_count(self, obj):
        """Определяет количество рецептов автора на которого подписан"""
        return obj.recipes.count()


class SubscribeCreateSerializer(serializers.ModelSerializer):
    """
    Сериализатор для создания подписки (POST).
    Валидация попытки подписаться на себя или повторную подписку.
    """

    class Meta:
        model = Follow
        fields = ('user', 'author')
        validators = [
            UniqueTogetherValidator(
                queryset=Follow.objects.all(),
                fields=('user', 'author'),
                message='Вы уже подписаны на этого пользователя!'
            )
        ]

    def validate_author(self, value):
        """Запрещает подписываться на самого себя."""
        user = self.context['request'].user
        if user == value:
            raise ValidationError('Нельзя подписываться на себя.')
        return value

    def create(self, validated_data):
        """
        Создаём запись в модели Follow.
        """
        return Follow.objects.create(**validated_data)


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
        fields = ['id', 'name', 'slug']


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
    id = serializers.PrimaryKeyRelatedField(queryset=Ingredient.objects.all())
    amount = serializers.IntegerField(min_value=MIN_AMOUNT)

    class Meta:
        model = IngredientRecipe
        fields = ['id', 'amount']


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
    author = UserDetailSerializer(read_only=True)
    image = Base64ImageField(required=False, allow_null=False)

    class Meta:
        model = Recipe
        fields = ['id', 'ingredients', 'tags', 'image', 'name', 'author',
                  'text', 'cooking_time']

    def validate_image(self, value):
        """
        Метод вызывается ТОЛЬКО, если поле 'image' присутствует в запросе.
        - При обновлении (self.instance есть) поле может не приходить совсем,
          но если пришло пустым (Base64 = ""), кидаем 400.
        """
        if not value:
            raise serializers.ValidationError(
                'Нельзя передавать пустую картинку при обновлении.'
            )
        return value

    def validate(self, data):
        """
        Валидация полей (проверка ingredients, tags).
        Если ингредиентов нет или amount < 1, ---> 400 Bad Request.
        """
        # Если убрать это условие отсюда то не будет проверки на пустое поле
        # Если image вообще не пришло, метод validate_image не вызовется
        if not self.instance and 'image' not in self.initial_data:
            raise ValidationError(
                {'image': 'Поле image обязательно при создании рецепта.'}
            )
        ingredients = data.get('ingredients')
        if not ingredients:
            raise ValidationError(
                {'ingredients':
                 'В рецепт надо добавить хотя бы один ингредиент.'}
            )
        seen_ingredients = set()
        for ingredient_data in ingredients:
            ingredient_id = ingredient_data['id']
            if ingredient_id in seen_ingredients:
                raise ValidationError({
                    'ingredients': 'Ингредиенты не могут повторяться!'
                })
            seen_ingredients.add(ingredient_id)

        tags = data.get('tags')
        if not tags:
            raise serializers.ValidationError(
                "Проверьте, что в рецепт добавлен хотя бы один тег"
            )
        if len(tags) != len(set(tags)):
            raise serializers.ValidationError("Теги должны быть уникальными")
        data['tags'] = tags
        return data

    def create_ingredients(self, ingredients_data, recipe):
        """Добавление ингредиентов в промежуточную таблицу IngredientRecipe."""
        IngredientRecipe.objects.bulk_create([
            IngredientRecipe(
                recipe=recipe,
                ingredient=ingredient_dict["id"],    # берём 'id'
                amount=ingredient_dict["amount"]     # берём 'amount'
            )
            for ingredient_dict in ingredients_data
        ])

    @transaction.atomic
    def create(self, validated_data):
        """Создание нового рецепта с привязкой тегов и ингредиентов."""
        tags = validated_data.pop('tags')
        ingredients_data = validated_data.pop('ingredients')
        validated_data['author'] = self.context['request'].user
        recipe = Recipe.objects.create(**validated_data)
        recipe.tags.set(tags)
        self.create_ingredients(ingredients_data, recipe)
        return recipe

    @transaction.atomic
    def update(self, instance, validated_data):
        """
        Обновляет поля рецепта и заново привязывает ингредиенты и теги.
        """
        tags = validated_data.pop('tags', None)
        ingredients_data = validated_data.pop('ingredients', None)
        instance = super().update(instance, validated_data)
        instance.tags.set(tags)
        instance.ingredients.clear()
        self.create_ingredients(ingredients_data, instance)
        return instance

    def to_representation(self, instance):
        """Для отображения используем детализированный сериализатор."""
        return RecipeSerializer(instance, context=self.context).data


class RecipeSerializer(serializers.ModelSerializer):
    """
    Сериализатор для детального представления рецептов в API.
    Включает связанные теги, автора, ингредиенты, а также поля проверки,
    находится ли рецепт в избранном пользователя или в корзине.
    """
    tags = TagSerializer(read_only=True, many=True,)
    author = UserDetailSerializer(read_only=True)
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
        Проверяет, есть ли рецепт в избранном у пользователя.
        Возвращает True/False.
        """
        request = self.context.get('request')
        return (
            request
            and not request.user.is_anonymous
            and request.user.favorite_recipes.filter(recipe=obj).exists()
        )

    def get_is_in_shopping_cart(self, obj):
        """
        Проверяем, есть ли рецепт в корзине.
        """
        request = self.context.get('request')
        return (
            request
            and not request.user.is_anonymous
            and request.user.shoppingcart_recipes.filter(recipe=obj).exists()
        )


class ListRecipeSerializer(serializers.ModelSerializer):
    """
    Сериалайзер для страницы мои подписки. Импортируюется в Users.
    мини карточка рецепта в списке авторов
    """
    image = Base64ImageField()

    class Meta:
        model = Recipe
        fields = ['id', 'name', 'image', 'cooking_time']
