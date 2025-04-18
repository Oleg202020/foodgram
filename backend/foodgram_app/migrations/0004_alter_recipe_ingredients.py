# Generated by Django 3.2.16 on 2025-02-23 00:02

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('foodgram_app', '0003_auto_20250222_1416'),
    ]

    operations = [
        migrations.AlterField(
            model_name='recipe',
            name='ingredients',
            field=models.ManyToManyField(related_name='recipes', through='foodgram_app.IngredientRecipe', to='foodgram_app.Ingredient', verbose_name='Ингридиенты рецепта'),
        ),
    ]
