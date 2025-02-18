from django.contrib.auth import get_user_model
from djoser.serializers import UserSerializer, UserCreateSerializer
from drf_extra_fields.fields import Base64ImageField
from rest_framework import serializers, status
from rest_framework.exceptions import ValidationError
from rest_framework.fields import SerializerMethodField

from .models import Follow


User = get_user_model()


class RegistrationUserSerializer(UserCreateSerializer):
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


class CorreсtAndSeeUserSerializer(UserSerializer):
    """
    Сериализатор для просмотра и редактирования данных пользователя.
    Используемые адреса:
        Получение списка пользователей   /users/         GET
        Регистрация пользователя         /users/         POST
        Профиль текущего пользователя    /users/me/      GET/PUT/PATCH
        Отдельный пользователь           /users/{id}/    GET/PUT/PATCH/DELETE
    """
    avatar = Base64ImageField(
        required=False,
        allow_null=True,
    )
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

    def validate(self, data):
        """Проверяет наличие аватара при обновлении.
        Если метод PUT и файл аватара не был передан,
        генерируется ValidationError.
        """
        request = self.context.get('request')
        if request and request.method == 'PUT':
            if not data.get('avatar'):
                raise serializers.ValidationError('Нет фото для аватара!')
        return data

    def get_is_subscribed(self, obj):
        """Возвращает True если пользователь подписан на автора."""
        current_user = self.context['request'].user
        if current_user.is_anonymous:
            return False
        return current_user.follower.filter(author=obj).exists()


class FollowSerializer(serializers.ModelSerializer):
    """Сериализатор для отображения информации о подписках."""
    is_subscribed = serializers.SerializerMethodField()
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

    def validate_author(self, data):
        """
        Проверяет корректность данных для подписки:
        Нельзя подписаться на самого себя.
        Нельзя подписаться на автора повторно.
        """
        current_user = self.context['request'].user
        author = self.instance
        if Follow.objects.filter(author=author, user=current_user).exists():
            raise ValidationError(
                detail='Вы уже подписаны на этого пользователя!',
                code=status.HTTP_400_BAD_REQUEST
            )
        if current_user == author:
            raise ValidationError(
                detail='Вы не можете подписаться на самого себя!',
                code=status.HTTP_400_BAD_REQUEST
            )
        return data

    def get_is_subscribed(self, obj):
        """Возвращает True если пользователь подписан на автора."""
        current_user = self.context['request'].user
        if current_user.is_anonymous:
            return False
        return Follow.objects.filter(user=current_user, author=obj).exists()

    def get_recipes(self, obj):
        """Возвращает сериализованные данные о рецептах автора.
        Параметр recipes_limit использовуется, для ограничения
        количества рецептов.
        """
        from foodgram_api.serializers import ListRecipeSerializer
        recipes_author = obj.recipe.all()
        recipes_qs = recipes_author

        request = self.context.get('request')
        if request is not None:
            limit_param = request.query_params.get('recipes_limit')
            if limit_param:
                try:
                    limit = int(limit_param)
                    recipes_qs = recipes_author[:limit]
                except ValueError:
                    pass
        return ListRecipeSerializer(recipes_qs, many=True).data

    def get_recipes_count(self, obj):
        """Определяет количество рецептов автора на которого подписан"""
        return obj.recipe.count()
