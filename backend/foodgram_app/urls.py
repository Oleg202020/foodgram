from django.urls import path

from foodgram_app.models import RecipeShortLinkView

urlpatterns = [
    path('<str:short_link>/',
         RecipeShortLinkView.as_view(), name='recipe_short_link'),
]
