from django.contrib.auth import get_user_model
from django.shortcuts import get_object_or_404

from djoser.serializers import SetPasswordSerializer
from djoser.views import UserViewSet as DjoserUserViewSet

from rest_framework import status, viewsets
from rest_framework.decorators import action
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response

from foodgram_api.pagination import CustomPagination

from .models import Follow

from .models import Follow
from .serializers import (CorrectAndSeeUserSerializer, FollowSerializer,
                          RegistrationUserSerializer)

"""
Список пользователей                api/users/                 GET
Регистрация пользователя            api/users/                 POST

Профиль пользователя                api/users/{id}/            GET
Текущий пользователь                api/users/me/              GET
Добавление аватара                  api/users/me/avatar/       PUT
Удаление аватара                    api/users/me/avatar/       DELET

Изменение пароля                    api/users/set_password/    POST

Получить токен авторизации          api/auth/token/login/      POST
Удаление токена                     api/auth/token/logout/     POST

Мои подписки                        api/users/subscriptions/   GET
Подписаться на пользователя         api/users/{id}/subscribe/  POST
Отписаться от пользователя          api/users/{id}/subscribe/  DELET
"""

User = get_user_model()


class UserViewSet(viewsets.ModelViewSet):
    """
    Вьюсет позволяет выполнять операции с пользователями, по
    эндпоинтам:
    Список пользователей               api/users/        GET
    Профиль пользователя               api/users/{id}/   GET
    Регистрация пользователя           api/users/        POST
    Обновление данных пользователя     api/users/{id}/   PUT
    Частичное обновление данных        api/users/{id}/   PATCH
    Удаление пользователя              api/users/{id}/   DELETE

    """
    queryset = User.objects.all()
    serializer_class = CorrectAndSeeUserSerializer
    pagination_class = CustomPagination

    def get_serializer_class(self):
        """Определяет сериализатор для использования ViewSet
         зависимости от action."""
        if self.action in ('list', 'retrieve'):
            return CorrectAndSeeUserSerializer
        return RegistrationUserSerializer

    @action(detail=False, methods=['get'],
            permission_classes=(IsAuthenticated,))
    def me(self, request):
        """Возвращает данные пользователя.
        Используется для получения информации о пользователе, который
        выполняет запрос. Доступно только авторизованным пользователям.
        """
        serializer = CorrectAndSeeUserSerializer(request.user,
                                                 context={'request': request})
        return Response(serializer.data, status=status.HTTP_200_OK)

    @action(
        detail=True,
        methods=['put', 'delete'],
        permission_classes=[IsAuthenticated]
    )
    def avatar(self, request, **kwargs):
        """Обновляет или удаляет аватар текущего пользователя."""
        user = get_object_or_404(User, pk=request.user.id)
        if request.method == 'PUT':
            serializers = CorrectAndSeeUserSerializer(
                user, data=request.data,
                partial=True, context={'request': request}
            )
            serializers.is_valid(raise_exception=True)
            serializers.save()
            return Response(
                {'avatar': serializers.data.get('avatar')},
                status=status.HTTP_200_OK
            )
        user.avatar = None
        user.save()
        return Response(status=status.HTTP_204_NO_CONTENT)

    @action(
        detail=False,
        methods=['post'],
        permission_classes=[IsAuthenticated]
    )
    def set_password(self, request):
        """Позволяет менять пароль пользователю."""
        serializer = SetPasswordSerializer(data=request.data,
                                           context={'request': request})
        serializer.is_valid(raise_exception=True)
        request.user.set_password(serializer.data['new_password'])
        request.user.save()
        return Response('Пароль изменен', status=status.HTTP_204_NO_CONTENT)

    @action(
        detail=False,
        permission_classes=[IsAuthenticated]
    )
    def subscriptions(self, request):
        """
         Возвращает список авторов, на которых подписан пользователь.
        """
        users = User.objects.filter(author__user=request.user)
        paginated_queryset = self.paginate_queryset(users)
        if paginated_queryset is not None:
            serializer = FollowSerializer(
                paginated_queryset, many=True, context={'request': request}
            )
            return self.get_paginated_response(serializer.data)
        serializer = FollowSerializer(
            paginated_queryset, many=True, context={'request': request})
        return Response(serializer.data)

    @action(
        detail=True,
        methods=['post', 'delete'],
        permission_classes=[IsAuthenticated]
    )
    def subscribe(self, request, pk=None):
        """Подписаться или отписаться от автора."""
        user = request.user
        author = get_object_or_404(User, pk=pk)
        limit_param = request.query_params.get('recipes_limit')
        if request.method == 'POST':
            if user == author:
                return Response(
                    {'errors': 'Нельзя подписываться на себя.'},
                    status=status.HTTP_400_BAD_REQUEST
                )
            subscr, created = Follow.objects.get_or_create(
                user=user, author=author)
            if not created:
                return Response(
                    {'errors': 'Вы подписаны на этого автора.'},
                    status=status.HTTP_400_BAD_REQUEST
                )
            serializer = FollowSerializer(
                author,
                context={'request': request, 'limit_param': limit_param}
            )
            return Response(serializer.data, status=status.HTTP_201_CREATED)
        if request.method == 'DELETE':
            subscr = Follow.objects.filter(user=user, author=author).first()
            if not subscr:
                return Response(
                    {'errors': 'Подписка не найдена.'},
                    status=status.HTTP_400_BAD_REQUEST
                )
            subscr.delete()
            return Response(status=status.HTTP_204_NO_CONTENT)
