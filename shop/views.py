from decimal import Decimal

from django.contrib import messages
from django.contrib.auth import login
from django.contrib.auth.decorators import login_required
from django.contrib.admin.views.decorators import staff_member_required
from django.db import transaction
from django.shortcuts import render, redirect, get_object_or_404

from django.db.models import Sum, Count, Avg
from django.db.models.functions import TruncDate
from django.utils import timezone
from datetime import timedelta

from .forms import (
    CustomUserCreationForm,
    UserEmailForm,
    ProductForm,
    CategoryForm,
    BlogPostForm,
)

from .models import (
    Category,
    Product,
    Order,
    OrderItem,
    BlogPost,
    UserProfile,
    Sticker,
)


# =========================
# ВСПОМОГАТЕЛЬНЫЕ ФУНКЦИИ
# =========================

def get_cart(request):
    return request.session.get('cart', {})


def get_cart_items(request):
    cart = get_cart(request)
    products = Product.objects.filter(
        id__in=cart.keys(),
        is_available=True
    )

    items = []
    total = Decimal('0.00')

    for product in products:
        quantity = int(cart.get(str(product.id), 1))
        line_total = product.price * quantity

        items.append({
            'product': product,
            'quantity': quantity,
            'line_total': line_total,
        })

        total += line_total

    return items, total


# =========================
# ГЛАВНАЯ СТРАНИЦА
# =========================

def home(request):
    categories = Category.objects.all()
    products = Product.objects.filter(
        is_available=True
    ).order_by('-created_at')[:6]

    posts = BlogPost.objects.filter(
        is_published=True
    ).order_by('-created_at')[:3]

    return render(request, 'shop/home.html', {
        'categories': categories,
        'products': products,
        'posts': posts,
    })


# =========================
# КАТАЛОГ И ТОВАРЫ
# =========================


def catalog(request):
    products = Product.objects.filter(is_available=True)
    categories = Category.objects.all()

    category_slug = request.GET.get('category')
    search_query = request.GET.get('q', '').strip()

    if category_slug:
        products = products.filter(
            category__slug=category_slug
        )

    if search_query:
        search_words = search_query.casefold().split()

        products = [
            product for product in products
            if any(
                word in product.name.casefold()
                for word in search_words
            )
        ]

    return render(request, 'shop/catalog.html', {
        'products': products,
        'categories': categories,
        'selected_category': category_slug,
        'search_query': search_query,
    })



def product_detail(request, product_id):
    product = get_object_or_404(
        Product,
        id=product_id,
        is_available=True
    )

    related_products = Product.objects.filter(
        category=product.category,
        is_available=True
    ).exclude(id=product.id)[:4]

    return render(request, 'shop/product_detail.html', {
        'product': product,
        'related_products': related_products,
    })


# =========================
# КОРЗИНА
# =========================

def cart_detail(request):
    items, total = get_cart_items(request)

    return render(request, 'shop/cart.html', {
        'items': items,
        'total': total,
    })


def add_to_cart(request, product_id):
    if request.method != 'POST':
        return redirect('catalog')

    product = get_object_or_404(
        Product,
        id=product_id,
        is_available=True
    )

    cart = get_cart(request)
    product_id = str(product.id)

    cart[product_id] = int(cart.get(product_id, 0)) + 1

    request.session['cart'] = cart
    request.session.modified = True

    messages.success(
        request,
        f'«{product.name}» добавлен в корзину.'
    )

    return redirect(request.POST.get('next') or 'cart')


def update_cart(request, product_id):
    if request.method != 'POST':
        return redirect('cart')

    cart = get_cart(request)
    product_id = str(product_id)

    if product_id in cart:
        try:
            quantity = int(request.POST.get('quantity', 1))
        except (ValueError, TypeError):
            quantity = 1

        if quantity <= 0:
            cart.pop(product_id)
        else:
            cart[product_id] = min(quantity, 99)

    request.session['cart'] = cart
    request.session.modified = True

    return redirect('cart')


def remove_from_cart(request, product_id):
    if request.method != 'POST':
        return redirect('cart')

    cart = get_cart(request)
    cart.pop(str(product_id), None)

    request.session['cart'] = cart
    request.session.modified = True

    messages.success(request, 'Товар удалён из корзины.')

    return redirect('cart')


# =========================
# ОФОРМЛЕНИЕ ЗАКАЗА
# =========================



def checkout(request):
    items, total = get_cart_items(request)

    if not items:
        messages.warning(request, 'Ваша корзина пока пуста.')
        return redirect('catalog')

    # Получаем профиль, если пользователь авторизован
    user_profile = None

    if request.user.is_authenticated:
        user_profile, created = UserProfile.objects.get_or_create(
            user=request.user
        )

    if request.method == 'POST':
        customer_name = request.POST.get(
            'customer_name', ''
        ).strip()

        phone = request.POST.get(
            'customer_phone', ''
        ).strip()

        email = request.POST.get(
            'customer_email', ''
        ).strip()

        comment = request.POST.get(
            'comment', ''
        ).strip()

        if not customer_name or not phone:
            messages.error(
                request,
                'Заполните имя и номер телефона.'
            )
            return redirect('checkout')

        # Сохраняем обновлённые контакты в аккаунте
        if request.user.is_authenticated:
            user_profile.full_name = customer_name
            user_profile.phone = phone
            user_profile.save()

            request.user.email = email
            request.user.save(update_fields=['email'])

        with transaction.atomic():
            order = Order.objects.create(
                user=request.user if request.user.is_authenticated else None,
                customer_name=customer_name,
                phone=phone,
                email=email,
                comment=comment,
                total_price=total,
            )

            for item in items:
                OrderItem.objects.create(
                    order=order,
                    product=item['product'],
                    product_name=item['product'].name,
                    price=item['product'].price,
                    quantity=item['quantity'],
                )

        request.session['cart'] = {}
        request.session['last_order_id'] = order.id
        request.session.modified = True

        return redirect('receipt', order_id=order.id)

    # Автоматически подставляем сохранённые контакты
    initial_name = ''
    initial_phone = ''
    initial_email = ''

    if request.user.is_authenticated:
        initial_name = (
            user_profile.full_name
            or request.user.get_full_name()
            or request.user.username
        )
        initial_phone = user_profile.phone
        initial_email = request.user.email

    return render(request, 'shop/checkout.html', {
        'items': items,
        'total': total,
        'initial_name': initial_name,
        'initial_phone': initial_phone,
        'initial_email': initial_email,
    })



def receipt(request, order_id):
    order = get_object_or_404(Order, id=order_id)

    has_access = (
        request.user.is_staff
        or (
            request.user.is_authenticated
            and order.user_id == request.user.id
        )
        or request.session.get('last_order_id') == order.id
    )

    if not has_access:
        from django.core.exceptions import PermissionDenied
        raise PermissionDenied

    return render(request, 'shop/receipt.html', {
        'order': order,
    })


# =========================
# РЕГИСТРАЦИЯ И ПРОФИЛЬ
# =========================


def register(request):
    if request.user.is_authenticated:
        return redirect('profile')

    form = CustomUserCreationForm(request.POST or None)

    if request.method == 'POST' and form.is_valid():
        user = form.save()
        login(request, user)
        messages.success(request, 'Добро пожаловать в MOKKA!')
        return redirect('profile')

    return render(request, 'registration/register.html', {'form': form})




@login_required
def profile(request):
    user_profile, created = UserProfile.objects.get_or_create(
        user=request.user
    )

    if request.method == 'POST':
        if 'save_email' in request.POST:
            form = UserEmailForm(request.POST, instance=request.user)

            if form.is_valid():
                form.save()
                messages.success(
                    request,
                    'Электронная почта успешно обновлена!'
                )
                return redirect('profile')

        elif 'save_contacts' in request.POST:
            user_profile.full_name = request.POST.get(
                'full_name', ''
            ).strip()
            user_profile.phone = request.POST.get(
                'phone', ''
            ).strip()
            user_profile.save()

            messages.success(
                request,
                'Личные данные успешно обновлены!'
            )
            return redirect('profile')
    else:
        form = UserEmailForm(instance=request.user)

    orders = Order.objects.filter(
        user=request.user
    ).order_by('-created_at')

    return render(request, 'shop/profile.html', {
        'orders': orders,
        'email_form': form,
        'user_profile': user_profile,
    })




# =========================
# БЛОГ
# =========================

def blog(request):
    posts = BlogPost.objects.filter(
        is_published=True
    ).order_by('-created_at')

    return render(request, 'shop/blog.html', {
        'posts': posts,
    })


def blog_detail(request, slug):
    post = get_object_or_404(
        BlogPost,
        slug=slug,
        is_published=True
    )

    return render(request, 'shop/blog_detail.html', {
        'post': post,
    })


# =========================
# ИНФОРМАЦИОННЫЕ СТРАНИЦЫ
# =========================

def about(request):
    return render(request, 'shop/about.html')


def contact(request):
    return render(request, 'shop/contact.html')


# =========================
# АДМИНИСТРАТИВНАЯ ПАНЕЛЬ
# =========================

@staff_member_required
def admin_dashboard(request):
    period = request.GET.get('period', '7')

    if period not in ['7', '30', 'all']:
        period = '7'

    today = timezone.localdate()

    orders = Order.objects.all()

    if period == '7':
        start_date = today - timedelta(days=6)
        orders = orders.filter(created_at__date__gte=start_date)

    elif period == '30':
        start_date = today - timedelta(days=29)
        orders = orders.filter(created_at__date__gte=start_date)

    completed_orders = orders.filter(status='completed')

    total_sales = completed_orders.aggregate(
        total=Sum('total_price')
    )['total'] or Decimal('0.00')

    orders_count = orders.count()

    average_check = completed_orders.aggregate(
        average=Avg('total_price')
    )['average'] or Decimal('0.00')

    sold_items = OrderItem.objects.filter(
        order__in=completed_orders
    ).aggregate(
        total=Sum('quantity')
    )['total'] or 0

    revenue_by_day = (
        completed_orders
        .annotate(day=TruncDate('created_at'))
        .values('day')
        .annotate(revenue=Sum('total_price'))
        .order_by('day')
    )

    popular_products = (
        OrderItem.objects
        .filter(order__in=completed_orders)
        .values('product_name')
        .annotate(total_quantity=Sum('quantity'))
        .order_by('-total_quantity')[:5]
    )

    return render(request, 'shop/admin_dashboard.html', {
        'orders_count': orders_count,
        'products_count': Product.objects.count(),
        'customers_count': orders.exclude(
            user=None
        ).values('user').distinct().count(),
        'total_sales': total_sales,
        'average_check': average_check,
        'sold_items': sold_items,
        'revenue_by_day': list(revenue_by_day),
        'popular_products': popular_products,
        'recent_orders': Order.objects.order_by(
            '-created_at'
        )[:5],
        'selected_period': period,
    })



@staff_member_required
def admin_orders(request):
    orders = Order.objects.all().order_by('-created_at')

    return render(request, 'shop/admin_orders.html', {
        'orders': orders,
    })

@staff_member_required
def admin_order_detail(request, order_id):
    order = get_object_or_404(
        Order.objects.prefetch_related('items'),
        id=order_id
    )

    if request.method == 'POST':
        new_status = request.POST.get('status')

        allowed_statuses = [
            status[0] for status in Order.STATUS_CHOICES
        ]

        if new_status in allowed_statuses:
            order.status = new_status
            order.save(update_fields=['status'])

            messages.success(
                request,
                f'Статус заказа №{order.id} обновлён!'
            )
            return redirect('admin_order_detail', order_id=order.id)

        messages.error(request, 'Выбран некорректный статус.')

    items = order.items.all()

    for item in items:
        item.line_total = item.price * item.quantity

    return render(request, 'shop/admin_order_detail.html', {
        'order': order,
        'items': items,
        'status_choices': Order.STATUS_CHOICES,
    })


@staff_member_required
def admin_products(request):
    products = Product.objects.all().order_by('-created_at')

    return render(request, 'shop/admin_products.html', {
        'products': products,
    })


# УПРАВЛЕНИЕ КАТЕГОРИЯМИ

@staff_member_required
def admin_categories(request):
    categories = Category.objects.annotate(
        products_count=Count('products')
    ).order_by('name')

    return render(request, 'shop/admin_categories.html', {
        'categories': categories,
    })


@staff_member_required
def admin_category_create(request):
    if request.method == 'POST':
        form = CategoryForm(request.POST)

        if form.is_valid():
            form.save()
            messages.success(request, 'Категория успешно добавлена!')
            return redirect('admin_categories')
    else:
        form = CategoryForm()

    return render(request, 'shop/admin_category_form.html', {
        'form': form,
        'page_title': 'Добавление категории',
    })


@staff_member_required
def admin_category_edit(request, category_id):
    category = get_object_or_404(Category, id=category_id)

    if request.method == 'POST':
        form = CategoryForm(request.POST, instance=category)

        if form.is_valid():
            form.save()
            messages.success(request, 'Изменения категории сохранены!')
            return redirect('admin_categories')
    else:
        form = CategoryForm(instance=category)

    return render(request, 'shop/admin_category_form.html', {
        'form': form,
        'page_title': 'Редактирование категории',
        'category': category,
    })


@staff_member_required
def admin_category_delete(request, category_id):
    category = get_object_or_404(Category, id=category_id)

    if request.method == 'POST':
        if category.products.exists():
            messages.error(
                request,
                'Нельзя удалить категорию, пока в ней есть товары!'
            )
            return redirect('admin_categories')

        category.delete()
        messages.success(request, 'Категория удалена!')
        return redirect('admin_categories')

    return render(request, 'shop/admin_category_delete.html', {
        'category': category,
    })

@staff_member_required
def admin_product_create(request):
    if request.method == 'POST':
        form = ProductForm(request.POST)

        if form.is_valid():
            form.save()
            messages.success(request, 'Товар успешно добавлен!')
            return redirect('admin_products')
    else:
        form = ProductForm()

    return render(request, 'shop/admin_product_form.html', {
        'form': form,
        'page_title': 'Добавление товара',
    })


@staff_member_required
def admin_product_edit(request, product_id):
    product = get_object_or_404(Product, id=product_id)

    if request.method == 'POST':
        form = ProductForm(request.POST, instance=product)

        if form.is_valid():
            form.save()
            messages.success(request, 'Изменения товара сохранены!')
            return redirect('admin_products')
    else:
        form = ProductForm(instance=product)

    return render(request, 'shop/admin_product_form.html', {
        'form': form,
        'page_title': 'Редактирование товара',
        'product': product,
    })


@staff_member_required
def admin_product_delete(request, product_id):
    product = get_object_or_404(Product, id=product_id)

    if request.method == 'POST':
        product.delete()
        messages.success(request, 'Товар удалён!')
        return redirect('admin_products')

    return render(request, 'shop/admin_product_delete.html', {
        'product': product,
    })


@staff_member_required
def admin_blog(request):
    posts = BlogPost.objects.all().order_by('-created_at')

    return render(request, 'shop/admin_blog.html', {
        'posts': posts,
    })


@staff_member_required
def admin_blog_create(request):
    if request.method == 'POST':
        form = BlogPostForm(
            request.POST,
            request.FILES
        )

        if form.is_valid():
            form.save()
            messages.success(request, 'Статья успешно добавлена!')
            return redirect('admin_blog')
    else:
        form = BlogPostForm()

    return render(request, 'shop/admin_blog_form.html', {
        'form': form,
        'page_title': 'Добавление статьи',
    })


@staff_member_required
def admin_blog_edit(request, post_id):
    post = get_object_or_404(BlogPost, id=post_id)

    if request.method == 'POST':
        form = BlogPostForm(
            request.POST,
            request.FILES,
            instance=post
        )

        if form.is_valid():
            form.save()
            messages.success(request, 'Статья успешно обновлена!')
            return redirect('admin_blog')
    else:
        form = BlogPostForm(instance=post)

    return render(request, 'shop/admin_blog_form.html', {
        'form': form,
        'page_title': 'Редактирование статьи',
        'post': post,
    })


@staff_member_required
def admin_blog_delete(request, post_id):
    post = get_object_or_404(BlogPost, id=post_id)

    if request.method == 'POST':
        post.delete()
        messages.success(request, 'Статья удалена!')
        return redirect('admin_blog')

    return render(request, 'shop/admin_blog_delete.html', {
        'post': post,
    })



# =========================
# ИНТЕРАКТИВНАЯ ДОСКА
# =========================

@staff_member_required
def admin_stickers(request):
    stickers = Sticker.objects.all().order_by('-created_at')

    return render(request, 'shop/admin_stickers.html', {
        'stickers': stickers,
    })


@staff_member_required
def admin_sticker_create(request):
    if request.method == 'POST':
        text = request.POST.get('text', '').strip()
        color = request.POST.get('color', '#F5CBA7')

        allowed_colors = [
            '#F5CBA7',
            '#F9E79F',
            '#A9DFBF',
            '#AED6F1',
            '#D7BDE2',
            '#F5B7B1',
        ]

        if text:
            if color not in allowed_colors:
                color = '#F5CBA7'

            Sticker.objects.create(
                text=text[:200],
                color=color,
            )

            messages.success(request, 'Стикер добавлен на доску!')
        else:
            messages.error(request, 'Введите текст заметки.')

    return redirect('admin_stickers')


@staff_member_required
def admin_sticker_move(request, sticker_id):
    if request.method == 'POST':
        sticker = get_object_or_404(Sticker, id=sticker_id)

        try:
            x = int(request.POST.get('position_x', 0))
            y = int(request.POST.get('position_y', 0))
        except (ValueError, TypeError):
            return redirect('admin_stickers')

        sticker.position_x = max(0, min(x, 10000))
        sticker.position_y = max(0, min(y, 10000))

        sticker.save(update_fields=['position_x', 'position_y'])

    return redirect('admin_stickers')


@staff_member_required
def admin_sticker_delete(request, sticker_id):
    if request.method == 'POST':
        sticker = get_object_or_404(Sticker, id=sticker_id)
        sticker.delete()
        messages.success(request, 'Стикер удалён.')

    return redirect('admin_stickers')