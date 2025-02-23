from django.conf import settings
from django.contrib.auth import get_user_model
from django.db.models import Sum
from django.http import HttpResponse
from django.shortcuts import get_object_or_404

from django_filters.rest_framework import DjangoFilterBackend
from rest_framework import status, viewsets
from rest_framework.decorators import action
from rest_framework.filters import SearchFilter
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework.response import Response

from foodgram_api.serializers import (
    CreateRecipeSerializer,
    IngredientSerializer,
    ListRecipeSerializer,
    RecipeSerializer,
    TagSerializer,
)
from foodgram_app.models import (
    Favorite,
    Ingredient,
    IngredientRecipe,
    Recipe,
    ShoppingCart,
    Tag,
)
from foodgram_users.models import Follow

from .filters import IngredientFilter, TagFavCartFilter
from .pagination import CustomPagination
from .permissions import IsOwnerOrAdmin
from .serializers import (
    FollowSerializer,
    RegistrationUserSerializer,
    SubscribeCreateSerializer,
    UserAvatarSerializer,
    UserDetailSerializer,
)

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
    serializer_class = UserDetailSerializer
    pagination_class = CustomPagination

    def get_serializer_class(self):
        """Определяет сериализатор для использования ViewSet
         зависимости от action."""
        if self.action in ('list', 'retrieve', 'partial_update', 'update'):
            return UserDetailSerializer
        return RegistrationUserSerializer

    @action(detail=False, methods=['get'],
            permission_classes=(IsAuthenticated,))
    def me(self, request):
        """Возвращает данные пользователя.
        Используется для получения информации о пользователе, который
        выполняет запрос. Доступно только авторизованным пользователям.
        """
        serializer = UserDetailSerializer(request.user,
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
            serializer = UserAvatarSerializer(
                user,
                data=request.data,
                partial=True,
                context={'request': request}
            )
            serializer.is_valid(raise_exception=True)
            serializer.save()
            return Response(
                {'avatar': serializer.data.get('avatar')},
                status=status.HTTP_200_OK
            )
        user.avatar.delete(save=True)
        return Response(status=status.HTTP_204_NO_CONTENT)

    @action(
        detail=False,
        methods=['post'],
        permission_classes=[IsAuthenticated]
    )
    def set_password(self, request):
        """Позволяет менять пароль пользователю."""
        old_password = request.data.get('current_password')
        new_password = request.data.get('new_password')
        if not old_password or not new_password:
            return Response(
                {'error': 'Нужно передать текущий и новый пароль'},
                status=status.HTTP_400_BAD_REQUEST
            )
        if not request.user.check_password(old_password):
            return Response(
                {'error': 'Текущий пароль указан неверно.'},
                status=status.HTTP_400_BAD_REQUEST
            )
        request.user.set_password(new_password)
        request.user.save()
        return Response({'detail': 'Пароль изменен'},
                        status=status.HTTP_204_NO_CONTENT)

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
        serializer = FollowSerializer(
            paginated_queryset, many=True, context={'request': request}
        )
        return self.get_paginated_response(serializer.data)

    @action(
        detail=True,
        methods=['post'],
        permission_classes=[IsAuthenticated]
    )
    def subscribe(self, request, pk=None):
        """Подписаться на автора."""
        author = get_object_or_404(User, pk=pk)
        data = {
            'user': request.user.id,
            'author': author.id
        }
        serializer = SubscribeCreateSerializer(data=data,
                                               context={'request': request})
        serializer.is_valid(raise_exception=True)
        serializer.save()
        author_serializer = FollowSerializer(author,
                                             context={'request': request})
        return Response(author_serializer.data, status=status.HTTP_201_CREATED)

    @subscribe.mapping.delete
    def unsubscribe(self, request, pk=None):
        """Отписаться от автора."""
        author = get_object_or_404(User, pk=pk)
        deleted_count, _ = Follow.objects.filter(user=request.user,
                                                 author=author).delete()
        if deleted_count == 0:
            return Response(
                {'error': 'Подписка не найдена.'},
                status=status.HTTP_400_BAD_REQUEST
            )
        return Response(status=status.HTTP_204_NO_CONTENT)


"""
Cписок тегов                        api/tags/                           GET
Получение тега                      api/tags/{id}/                      GET
Список ингредиентов                 api/ingredients/                    GET
Получение ингредиента               api/ingredients/{id}/               GET

Список рецептов                     api/recipes/                        GET
Создание рецепта                    api/recipes/                        POST
Получение рецепта                   api/recipes/{id}/                   GET
Обновление рецепта                  api/recipes/{id}/                   PATCH
Удаление рецепта                    api/recipes/{id}/                   DELETE
Получить короткую ссылку на рецепт  api/recipes/{id}/get-link/          GET

Скачать список покупок              api/recipes/download_shopping_cart/ GET
Добавить рецепт в список покупок    api/recipes/{id}/shopping_cart/     POST
Удалить рецепт из списка покупок    api/recipes/{id}/shopping_cart/     DELETE

Добавить рецепт в избранное         api/recipes/{id}/favorite/          POST
Удалить рецепт из избранного        api/recipes/{id}/favorite/          DELETE
"""

'''
# Или клас или функия
def recipe_short_redirect_view(request, short_link):
    """Находит рецепт по short_link и редиректит на /recipes/<id>/."""
    recipe = get_object_or_404(Recipe, short_link=short_link)
    return redirect(f"/recipes/{recipe.id}/")
в урле:  path('<str:short_link>/', recipe_short_redirect_view,
              name='recipe_short_link'),
    мне больше класс нравится
'''


class TagViewSet(viewsets.ReadOnlyModelViewSet):
    """
    Вьюсет обрабатывает адреса:
        Cписок тегов           api/tags/                           GET
        Получение тега         api/tags/{id}/                      GET
        позволяет получить список тегов или один тег
    """
    queryset = Tag.objects.all()
    serializer_class = TagSerializer
    pagination_class = None


class IngredientViewSet(viewsets.ReadOnlyModelViewSet):
    """
    Вьюсет обрабатывает адреса:
        Список ингредиентов     api/ingredients/                    GET
        Получение ингредиента   api/ingredients/{id}/               GET
    позволяет получить список ингридиентов или один ингридиент
    """
    queryset = Ingredient.objects.all()
    serializer_class = IngredientSerializer
    pagination_class = None
    filter_backends = (DjangoFilterBackend, SearchFilter)
    filterset_class = IngredientFilter
    search_fields = ['name']


class RecipeViewSet(viewsets.ModelViewSet):
    """Вьюсет для управления рецептами."""
    queryset = Recipe.objects.all()
    serializer_class = CreateRecipeSerializer
    permission_classes = [IsOwnerOrAdmin]
    filter_backends = (DjangoFilterBackend,)
    filterset_class = TagFavCartFilter
    pagination_class = CustomPagination

    def get_serializer_class(self):
        """Возвращает сериализатор в зависимости от action."""
        if self.action in ('list', 'retrieve'):
            return RecipeSerializer
        return CreateRecipeSerializer

    @action(detail=True, permission_classes=(AllowAny,), url_path='get-link')
    def get_short_link(self, request, pk=None):
        """Генерирует или получает из базы короткую ссылку для рецепта.
        /api/recipes/{id}/get-link/          GET
        """
        recipe = get_object_or_404(Recipe, pk=pk)
        short_url = f"{settings.SHORT_DOMAIN}/s/{recipe.short_link}"
        return Response({'short-link': short_url}, status=status.HTTP_200_OK)

    @action(detail=True, methods=['post'],
            permission_classes=[IsAuthenticated])
    def shopping_cart(self, request, pk):
        """
        Добавляет рецепт в список покупок пользователя.
        /api/recipes/{id}/shopping_cart/     POST
        """
        return self.create_relation(
            model=ShoppingCart,
            user=request.user,
            pk=pk,
            error_msg='Рецепт в списке покупок.',
            success_msg='Рецепт добавлен в список покупок.'
        )

    @shopping_cart.mapping.delete
    def remove_from_cart(self, request, pk):
        """
        Удаляет рецепт из списка покупок пользователя.
        /api/recipes/{id}/shopping_cart/     DELETE
        """
        return self.delete_relation(
            model=ShoppingCart,
            user=request.user,
            pk=pk,
            error_msg='Рецепта нет в списке покупок.'
        )

    @action(detail=True, methods=['post'],
            permission_classes=[IsAuthenticated])
    def favorite(self, request, pk):
        """
        Добавляет рецепт в избранное пользователя.
        /api/recipes/{id}/favorite/         POST
        """
        return self.create_relation(
            model=Favorite,
            user=request.user,
            pk=pk,
            error_msg='Рецепт уже в избранном.',
            success_msg='Рецепт добавлен в избранное.'
        )

    @favorite.mapping.delete
    def remove_favorite(self, request, pk):
        """
        Удаляет рецепт из избранного пользователя.
        /api/recipes/{id}/favorite/         DELETE
        """
        return self.delete_relation(
            model=Favorite,
            user=request.user,
            pk=pk,
            error_msg='Рецепта нет в избранном.'
        )

    def create_relation(self, model, user, pk, error_msg, success_msg):
        """
        Метод для добавления записи ShoppingCart или Favorite.
        Используем get_or_create() для проверки дубликата.
        """
        recipe = get_object_or_404(Recipe, pk=pk)
        obj, created = model.objects.get_or_create(user=user, recipe=recipe)
        if not created:
            return Response({'errors': error_msg},
                            status=status.HTTP_400_BAD_REQUEST)
        serializer = ListRecipeSerializer(recipe,
                                          context={'request': self.request})
        return Response(serializer.data, status=status.HTTP_201_CREATED)

    def delete_relation(self, model, user, pk, error_msg):
        """
        Метод для удаления записи ShoppingCart или Favorite.
        Если ничего не удалилось — возвращаем 400. Иначе 204.
        """
        recipe = get_object_or_404(Recipe, pk=pk)
        deleted_count, _ = model.objects.filter(user=user,
                                                recipe=recipe).delete()
        if deleted_count == 0:
            return Response({'errors': error_msg},
                            status=status.HTTP_400_BAD_REQUEST)
        return Response(status=status.HTTP_204_NO_CONTENT)

    @action(detail=False, methods=['get'],
            permission_classes=[IsAuthenticated])
    def download_shopping_cart(self, request, **kwargs):
        """
        Позволяет скачать список покупок в виде текстового файла.
        /api/recipes/download_shopping_cart/         GET
        """
        ingredients = (IngredientRecipe.objects
                       .filter(recipe__shoppingcart_recipes__user=request.user)
                       .values('ingredient')
                       .annotate(total_amount=Sum('amount'))
                       .order_by('ingredient__name')
                       .values_list(
                           'ingredient__name',
                           'total_amount',
                           'ingredient__measurement_unit'))
        lines = (
            [f'{name} - {total} {unit}' for name, total, unit in ingredients]
        )
        shopping_list = '\n'.join(lines) or 'Список для покупок пуст.'
        response = HttpResponse(shopping_list, content_type='text/plain')
        response['Content-Disposition'] = (
            'attachment; filename="shopping_list.txt"')
        return response
