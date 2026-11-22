from django.urls import path
from . import views
from django.contrib.auth import views as auth_views

urlpatterns = [
    # Основные страницы
    path('', views.home, name='home'),
    path('about/', views.about, name='about'),
    path('contact/', views.contact, name='contact'),

    # Каталог
    path('catalog/', views.catalog, name='catalog'),
    path('product/<int:product_id>/', views.product_detail, name='product_detail'),

    # Корзина
    path('cart/', views.cart_detail, name='cart'),
    path('cart/add/<int:product_id>/', views.add_to_cart, name='add_to_cart'),
    path('cart/update/<int:product_id>/', views.update_cart, name='update_cart'),
    path('cart/remove/<int:product_id>/', views.remove_from_cart, name='remove_from_cart'),

    # Заказы
    path('checkout/', views.checkout, name='checkout'),
    path('receipt/<int:order_id>/', views.receipt, name='receipt'),

    # Пользователи
    path('register/', views.register, name='register'),
    path('login/', auth_views.LoginView.as_view(template_name='registration/login.html'), name='login'),
    path('logout/', auth_views.LogoutView.as_view(next_page='home'), name='logout'),
    path('profile/', views.profile, name='profile'),

    # Блог
    path('blog/', views.blog, name='blog'),
    path('blog/<slug:slug>/', views.blog_detail, name='blog_detail'),

    # Административная панель

    path('management/', views.admin_dashboard, name='admin_dashboard'),
    path('management/orders/', views.admin_orders, name='admin_orders'),
    path('management/orders/<int:order_id>/', views.admin_order_detail, name='admin_order_detail'),
    path('management/products/', views.admin_products, name='admin_products'),

    # Управление товарами
    path('management/products/add/', views.admin_product_create, name='admin_product_create'),
    path('management/products/<int:product_id>/edit/', views.admin_product_edit, name='admin_product_edit'),
    path('management/products/<int:product_id>/delete/', views.admin_product_delete, name='admin_product_delete'),

    # Управление категориями
    path('management/categories/', views.admin_categories, name='admin_categories'),
    path('management/categories/add/', views.admin_category_create, name='admin_category_create'),
    path('management/categories/<int:category_id>/edit/', views.admin_category_edit, name='admin_category_edit'),
    path('management/categories/<int:category_id>/delete/', views.admin_category_delete, name='admin_category_delete'),

    # Управление блогом
    path('management/blog/', views.admin_blog, name='admin_blog'),
    path('management/blog/add/', views.admin_blog_create, name='admin_blog_create'),
    path('management/blog/<int:post_id>/edit/', views.admin_blog_edit, name='admin_blog_edit'),
    path('management/blog/<int:post_id>/delete/', views.admin_blog_delete, name='admin_blog_delete'),

    # Интерактивная доска
    path('management/stickers/', views.admin_stickers, name='admin_stickers'),
    path('management/stickers/add/', views.admin_sticker_create, name='admin_sticker_create'),
    path('management/stickers/<int:sticker_id>/move/', views.admin_sticker_move, name='admin_sticker_move'),
    path('management/stickers/<int:sticker_id>/delete/', views.admin_sticker_delete, name='admin_sticker_delete'),
]
