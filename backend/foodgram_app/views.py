from django.shortcuts import redirect
from rest_framework import generics
from .models import Recipe


class RecipeShortLinkView(generics.GenericAPIView):
    """ Позволяет открыть рецепт по короткой ссылке:
    https://foodgramlar.viewdns.net/s/<short_link>
    Позволяет перейти на рецепт по короткой ссылке `/s/<short_link>/`.
    """
    def get(self, request, short_link):
        try:
            recipe = Recipe.objects.get(short_link=short_link)
        except Recipe.DoesNotExist:
            return redirect('/404')
        frontend_url = f"/recipes/{recipe.id}/"
        return redirect(frontend_url)
