from django.urls import path

from foodgram_app.views import RecipeShortLinkView

urlpatterns = [
    path('<str:short_link>/',
         RecipeShortLinkView.as_view(), name='recipe_short_link'),
]
