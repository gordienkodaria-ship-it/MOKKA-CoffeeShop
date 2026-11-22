from django import forms
from django.contrib.auth.forms import UserCreationForm
from django.contrib.auth.models import User
from .models import Product, Category, BlogPost


class CustomUserCreationForm(UserCreationForm):
    email = forms.EmailField(
        required=True,
        label='Электронная почта',
        widget=forms.EmailInput(attrs={
            'placeholder': 'Введите электронную почту',
            'autocomplete': 'email',
        })
    )

    class Meta:
        model = User
        fields = ('username', 'email', 'password1', 'password2')


class UserEmailForm(forms.ModelForm):
    email = forms.EmailField(
        required=True,
        label='Электронная почта',
        widget=forms.EmailInput(attrs={
            'placeholder': 'Введите электронную почту',
            'autocomplete': 'email',
        })
    )

    class Meta:
        model = User
        fields = ('email',)


class ProductForm(forms.ModelForm):
    class Meta:
        model = Product
        fields = [
            'name',
            'category',
            'description',
            'price',
            'image_url',
            'is_available',
        ]
        labels = {
            'name': 'Название товара',
            'category': 'Категория',
            'description': 'Описание',
            'price': 'Цена',
            'image_url': 'Ссылка на изображение',
            'is_available': 'Есть в наличии',
        }
        widgets = {
            'name': forms.TextInput(attrs={
                'placeholder': 'Например, Ванильный айс кофе'
            }),
            'description': forms.Textarea(attrs={
                'placeholder': 'Описание товара',
                'rows': 4,
            }),
            'price': forms.NumberInput(attrs={
                'placeholder': '0.00',
                'min': '0',
                'step': '0.01',
            }),
            'image_url': forms.TextInput(attrs={
            'placeholder': '/static/images/products/image.jpg'
        }),
        }


class CategoryForm(forms.ModelForm):
    class Meta:
        model = Category
        fields = ['name', 'description']
        labels = {
            'name': 'Название категории',
            'description': 'Описание категории',
        }
        widgets = {
            'name': forms.TextInput(attrs={
                'placeholder': 'Например, Кофе'
            }),
            'description': forms.Textarea(attrs={
                'placeholder': 'Краткое описание категории',
                'rows': 4,
            }),
        }


class BlogPostForm(forms.ModelForm):
    class Meta:
        model = BlogPost
        fields = [
            'title',
            'excerpt',
            'content',
            'image',
            'is_published',
        ]

        labels = {
            'title': 'Заголовок статьи',
            'excerpt': 'Краткое описание',
            'content': 'Текст статьи',
            'image': 'Изображение статьи',
            'is_published': 'Опубликовать статью',
        }

        widgets = {
            'title': forms.TextInput(attrs={
                'placeholder': 'Введите заголовок статьи'
            }),
            'excerpt': forms.Textarea(attrs={
                'placeholder': 'Краткое описание статьи',
                'rows': 3,
            }),
            'content': forms.Textarea(attrs={
                'placeholder': 'Полный текст статьи',
                'rows': 10,
            }),
        }