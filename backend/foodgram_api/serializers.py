"""
Файл содержит сериализаторы для обработки всего, что связано с рецептом:
    созданием и редактированием, а также мини сериализатор который также
    использыется в подписках.
    сериализаторы ингридиентов и тегов.
все сериализаторы с пользователем содержатся в foodgram_users:
работа с аватаром, редактирование пароля, подписки на других пользователей
"""
from django.contrib.auth import get_user_model
# from djoser.serializers import UserCreateSerializer, UserSerializer
from drf_extra_fields.fields import Base64ImageField
from foodgram_app.constants import MIN_AMOUNT
from foodgram_app.models import Ingredient, IngredientRecipe, Recipe, Tag
from foodgram_users.models import Follow
from rest_framework import serializers, status
from rest_framework.exceptions import ValidationError
from rest_framework.fields import SerializerMethodField

"""
from django.contrib.auth import get_user_model
from djoser.serializers import UserCreateSerializer, UserSerializer
from drf_extra_fields.fields import Base64ImageField
from rest_framework import serializers, status
from rest_framework.exceptions import ValidationError
from rest_framework.fields import SerializerMethodField

from foodgram_app.constants import MIN_AMOUNT
from foodgram_app.models import Ingredient, IngredientRecipe, Recipe, Tag
from foodgram_users.models import Follow
"""

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
        if not request or request.user.is_anonymous:
            return False
        return request.user.follower.filter(author=obj).exists()


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
        recipes_author = obj.recipe.all()
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
        return obj.recipe.count()


class SubscribeCreateSerializer(serializers.Serializer):
    """
    Сериализатор для создания подписки (POST).
    Валидация попытки подписаться на себя или повторную подписку.
    """
    author_id = serializers.IntegerField()

    def validate(self, attrs):
        request = self.context.get('request')
        user = request.user
        author_id = attrs.get('author_id')
        if user.pk == author_id:
            raise ValidationError(
                'Нельзя подписываться на себя.',
                code=status.HTTP_400_BAD_REQUEST
            )
        author = User.objects.filter(pk=author_id).first()
        if not author:
            raise ValidationError(
                'Пользователь не найден.',
                code=status.HTTP_404_NOT_FOUND
            )
        if Follow.objects.filter(user=user, author=author).exists():
            raise ValidationError(
                'Вы уже подписаны на этого пользователя!',
                code=status.HTTP_400_BAD_REQUEST
            )
        attrs['author'] = author
        return attrs

    def create(self, validated_data):
        user = self.context['request'].user
        author = validated_data['author']
        return Follow.objects.create(user=user, author=author)


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
    author = UserDetailSerializer(read_only=True)
    image = Base64ImageField(required=False, allow_null=False)

    class Meta:
        model = Recipe
        fields = ['id', 'ingredients', 'tags', 'image', 'name', 'author',
                  'text', 'cooking_time']

    def tags_and_ingredients_set(self, recipe, tags, ingredients):
        """
        Привязывает к рецепту выбранные теги и ингредиенты.
        Создаёт записи в промежуточной модели IngredientRecipe.
        """
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
        if not self.instance:
            if not data.get('image'):
                raise serializers.ValidationError(
                    {'image': 'Нужно добавить файл с изображением.'})
        else:
            if 'image' in data:
                if not data['image']:
                    raise serializers.ValidationError(
                        ({'image': 'Изображение обязательное поле.'
                         'Загрузите новый файл.'})
                    )
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
                    ({'ingredients': f'Ингредиента с id={ingredient_id}'
                      'не существует.'})
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
        Проверяет, находится ли текущий рецепт в избранном у пользователя.
        Возвращает True/False.
        """
        user = self.context['request'].user
        if user.is_anonymous:
            return False
        return user.favorites.filter(recipe=obj).exists()

    def get_is_in_shopping_cart(self, obj):
        """
        Проверяет, есть ли рецепт в корзине у пользователя.
        Возвращает True/False.
        """
        user = self.context['request'].user
        if user.is_anonymous:
            return False
        return user.shoppingcarts.filter(recipe=obj).exists()


class ListRecipeSerializer(serializers.ModelSerializer):
    """
    Сериалайзер для страницы мои подписки. Импортируюется в Users.
    мини карточка рецепта в списке авторов
    """
    image = Base64ImageField()

    class Meta:
        model = Recipe
        fields = ['id', 'name', 'image', 'cooking_time']
