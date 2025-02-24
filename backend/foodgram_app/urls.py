from django.urls import path

from foodgram_app.models import RecipeShortLinkView

urlpatterns = [
    path('s/<str:short_link>/',
         RecipeShortLinkView.as_view(), name='recipe_short_link'),
]