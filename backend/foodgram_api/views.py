import random
import string

from django.db.models import Sum
from django.http import HttpResponse
from django.shortcuts import get_object_or_404
from django_filters.rest_framework import DjangoFilterBackend
from rest_framework import generics, status, viewsets
from rest_framework.decorators import action
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework.response import Response

from core_foodgram.filters import IngredientFilter, TagFavCartFilter
from core_foodgram.pagination import CustomPagination
from core_foodgram.permissions import IsOwnerOrAdmin
from foodgram_api.serializers import (CreateRecipeSerializer,
                                      IngredientSerializer,
                                      ListRecipeSerializer, RecipeSerializer,
                                      TagSerializer)
from foodgram_app.models import (Favorite, Ingredient, IngredientRecipe,
                                 Recipe, ShoppingCart, Tag)

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


def generate_short_code(length=3):
    """
    Генерирует случайную строку из символов [a-zA-Z0-9].
    """
    letters_digits = string.ascii_letters + string.digits
    return ''.join(random.choice(letters_digits) for _ in range(length))


class RecipeShortLinkView(generics.RetrieveAPIView):
    """
    Позволяет получить рецепт по короткой ссылке `/s/<short_link>/`.
    Не генерирует ссылку, только возвращает рецепт.
    """
    queryset = Recipe.objects.all()
    serializer_class = RecipeSerializer
    permission_classes = [AllowAny]
    lookup_field = 'short_link'


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
    filter_backends = (DjangoFilterBackend,)
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
        """Возвращает сериализатор в зависимости от действия (action)."""
        if self.action in ('list', 'retrieve'):
            return RecipeSerializer
        return CreateRecipeSerializer

    def get_permissions(self):
        """Авторизованный пользователь может добавить в корзину любой рецепт"""
        if self.action in ('shopping_cart',):
            return [IsAuthenticated()]
        return super().get_permissions()

    @action(detail=True, permission_classes=(AllowAny,), url_path='get-link')
    def get_short_link(self, request, pk=None):
        """Генерирует или получает из базы короткую ссылку для рецепта.
        Доступ /api/recipes/{id}/get-link/      GET
        """
        recipe = get_object_or_404(Recipe, pk=pk)
        if not recipe.short_link:
            while True:
                short_code = generate_short_code(3)
                if not Recipe.objects.filter(short_link=short_code).exists():
                    recipe.short_link = short_code
                    recipe.save()
                    break
        return Response({'short-link': recipe.short_link},
                        status=status.HTTP_200_OK)

    @action(
        detail=True,
        methods=['post', 'delete']
    )
    def shopping_cart(self, request, pk):
        """Добавляет или удаляет рецепт в списке покупок пользователя."""
        user = request.user
        recipe = get_object_or_404(Recipe, pk=pk)
        if request.method == 'POST':
            if ShoppingCart.objects.filter(user=user, recipe=recipe).exists():
                return Response(
                    {'errors': 'Рецепт уже в списке покупок.'},
                    status=status.HTTP_400_BAD_REQUEST)
            ShoppingCart.objects.create(user=user, recipe=recipe)
            serializer = ListRecipeSerializer(
                recipe, context={'request': request})
            return Response(serializer.data, status=status.HTTP_201_CREATED)
        if request.method == 'DELETE':
            in_cart = ShoppingCart.objects.filter(user=user, recipe=recipe)
            if not in_cart:
                return Response(
                    {'detail': 'Рецепт не в списке покупок.'},
                    status=status.HTTP_400_BAD_REQUEST
                )
            in_cart.delete()
            return Response(
                {'detail': 'Рецепт успешно удален из списка покупок.'},
                status=status.HTTP_204_NO_CONTENT
            )

    @action(
        detail=False,
        methods=['get'],
        permission_classes=[IsAuthenticated]
    )
    def download_shopping_cart(self, request, **kwargs):
        """Позволяет скачать список покупок пользователю."""
        ingredients = (
            IngredientRecipe.objects
            .filter(recipe__shoppingcart_recipes__user=request.user
                    ).values('ingredient'
                             ).annotate(total_amount=Sum('amount')
                                        ).values_list(
                                            'ingredient__name',
                                            'total_amount',
                                            'ingredient__measurement_unit'))
        lines = []
        for name, total, unit in ingredients:
            lines.append(f'{name} - {total} {unit}')
        shopping_list = '\n'.join(lines) or 'Список для покупок пуст.'
        response = HttpResponse(shopping_list, content_type='text/plain')
        response['Content-Disposition'] = 'attachment; \
            filename="shopping_list.txt"'
        return response

    @action(
        detail=True,
        methods=['post', 'delete'],
        permission_classes=[IsAuthenticated],
    )
    def favorite(self, request, pk):
        """Добавляет или удаляет рецепт из избранного текущего пользователя."""
        recipe = get_object_or_404(Recipe, pk=pk)

        if request.method == 'POST':
            if Favorite.objects.filter(user=request.user,
                                       recipe=recipe).exists():
                return Response(
                    {'errors': 'Рецепт находится в избранном.'},
                    status=status.HTTP_400_BAD_REQUEST
                )
            Favorite.objects.create(user=request.user, recipe=recipe)
            serializer = ListRecipeSerializer(
                recipe, context={'request': request})
            return Response(serializer.data, status=status.HTTP_201_CREATED)

        if request.method == 'DELETE':
            favorite = Favorite.objects.filter(
                user=request.user,
                recipe=recipe
            ).first()
            if not favorite:
                return Response(
                    {'errors': 'Рецепта нет в избранном.'},
                    status=status.HTTP_400_BAD_REQUEST
                )
            favorite.delete()
            return Response(
                {'detail': 'Рецепт удален из избранного.'},
                status=status.HTTP_204_NO_CONTENT
            )
