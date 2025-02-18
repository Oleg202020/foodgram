from django.urls import include, path
from foodgram_users.views import UserViewSet
from rest_framework.routers import DefaultRouter

from .views import (IngredientViewSet, RecipeShortLinkView, RecipeViewSet,
                    TagViewSet)

router = DefaultRouter()

router.register(r'tags', TagViewSet, basename='tags')
router.register(r'ingredients', IngredientViewSet, basename='ingredients')
router.register(r'recipes', RecipeViewSet, basename='recipes')
router.register(r'users', UserViewSet, basename='users')


urlpatterns = [
    path('', include(router.urls)),
    path('', include('djoser.urls')),
    path('auth/', include('djoser.urls.authtoken')),
    path('<str:short_link>/',
         RecipeShortLinkView.as_view(), name='recipe_short_link'),
]
