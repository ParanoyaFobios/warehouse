from django.shortcuts import render, redirect
from django.contrib.auth import authenticate, login, logout
from .forms import LoginForm
from django.shortcuts import get_object_or_404
from django.http import HttpResponse, Http404
from django.contrib.contenttypes.models import ContentType
import barcode
from barcode.writer import ImageWriter
import io
from django.views.generic import View, ListView
from django.contrib.auth.mixins import LoginRequiredMixin, PermissionRequiredMixin
from warehouse2.models import Shipment, WorkOrder
from django.contrib import messages
from django.db.models import F
from warehouse1.models import Material
from warehouse2.models import Product
from django.urls import reverse
from urllib.parse import urlencode
from django.contrib.auth.models import User
from django.urls import reverse_lazy
from .forms import UserCreationWithGroupForm
from django.views.generic.edit import FormView
from django.http import HttpResponse, Http404
from django.shortcuts import get_object_or_404
from PIL import Image, ImageDraw, ImageFont


# ==============================================================================
# Представления для аутентификации
# ==============================================================================
class LoginView(View):
    template_name = 'login.html'
    form_class = LoginForm
    
    def get(self, request):
        if request.user.is_authenticated:
            return redirect('start-page')
        form = self.form_class()
        return render(request, self.template_name, {'form': form})
    
    def post(self, request):
        form = self.form_class(request, data=request.POST)
        if form.is_valid():
            username = form.cleaned_data['username']
            password = form.cleaned_data['password']
            user = authenticate(request, username=username, password=password)
            
            if user is not None:
                login(request, user)
                if not form.cleaned_data['remember_me']:
                    request.session.set_expiry(0)  # Сессия закончится при закрытии браузера
                return redirect('start-page')
        
        context = {
            'form': form,
            'error': 'Не удалось войти. Проверьте имя пользователя и пароль.'
        }
        messages.success(request, f'Вы успешно вошли в систему.')
        return render(request, self.template_name, context)


class LogoutView(View):
    def get(self, request):
        logout(request)
        return redirect('login')

class UserListView(PermissionRequiredMixin, ListView):
    model = User
    template_name = 'user_list.html'
    context_object_name = 'users'
    permission_required = 'auth.view_user' # Только те, кто может просматривать пользователей

    def get_queryset(self):
        # Показываем пользователей с их группами
        return User.objects.all().prefetch_related('groups').order_by('username')

class CreateUserWithGroupView(PermissionRequiredMixin, FormView):
    form_class = UserCreationWithGroupForm
    template_name = 'create_user_form.html'
    success_url = reverse_lazy('user_list') # ИЛИ 'inbox', 'product_list' и т.д.
    
    permission_required = 'auth.add_user'

    def form_valid(self, form):
        username = form.cleaned_data['username']
        password = form.cleaned_data['password']
        group = form.cleaned_data['group']
        first_name = form.cleaned_data.get('first_name', '')
        phone = form.cleaned_data.get('phone') # Если у вас есть поле phone в модели User

        user = User.objects.create_user(username=username, password=password, first_name=first_name)
        user.groups.add(group)

        messages.success(self.request, f"Пользователь '{username}' успешно создан.")
        # Мы выполняем свои действия, а затем просим родительский класс сделать редирект
        return super().form_valid(form)

class IndexView(LoginRequiredMixin, View):
    def get(self, request):
        # Не выполненные отгрузки (не собранные и не отгруженные)
        pending_shipments = Shipment.objects.filter(
            status__in=['pending', 'packaged']
        ).prefetch_related('items').order_by('-created_at')[:10]
        
        # Не выполненные производственные заказы
        pending_workorders = WorkOrder.objects.filter(
            status__in=['new', 'in_progress']
        ).select_related('product').order_by('-created_at')[:10]
        
        # F('min_quantity') позволяет сравнить значение поля quantity со значением поля min_quantity
        low_stock_materials_count = Material.objects.filter(
            quantity__lte=F('min_quantity'),
            min_quantity__gt=0 # Учитываем только те, где мин. остаток задан
            ).count()
        
        context = {
            'user': request.user,
            'pending_shipments': pending_shipments,
            'pending_workorders': pending_workorders,
            'pending_shipments_count': Shipment.objects.filter(status__in=['pending', 'packaged']).count(),
            'pending_workorders_count': WorkOrder.objects.filter(status__in=['new', 'in_progress']).count(),
            'low_stock_materials_count': low_stock_materials_count,
        }
        return render(request, 'index.html', context)
    
# ==============================================================================
# Генерация штрихкода для любого объекта
# ==============================================================================

def generate_barcode_view(request, content_type_id, object_id):
    """
    Универсальное view для генерации штрихкода для любого объекта
    с его названием над штрихкодом.
    """
    try:
        # 1. Находим "удостоверение" модели по ее ID
        content_type = get_object_or_404(ContentType, pk=content_type_id)
        
        # 2. Находим сам объект (Product, Package и т.д.) по его ID
        obj = content_type.get_object_for_this_type(pk=object_id)

    except ContentType.DoesNotExist:
        raise Http404("Указанный тип контента не существует")

    # 3. Проверяем, есть ли у объекта поле 'barcode'
    if not hasattr(obj, 'barcode') or not obj.barcode:
        raise Http404("У этого объекта нет поля 'barcode' или оно пустое")

    # 4. Генерируем изображение штрихкода (базовая часть)
    CODE128 = barcode.get_barcode_class('code128')
    writer = ImageWriter(format='PNG')
    
    # Настройки для штрихкода
    writer_options = {
        'module_height': 12.0,
        'font_size': 8,
        'text_distance': 4.0,
        'quiet_zone': 2.0
    }

    code = CODE128(obj.barcode, writer=writer)
    barcode_buffer = io.BytesIO()
    code.write(barcode_buffer, options=writer_options)
    barcode_buffer.seek(0)

    # --- Используем Pillow для добавления текста ---

    # 5. Открываем сгенерированный штрихкод как изображение
    barcode_img = Image.open(barcode_buffer)
    
    # 6. Получаем текст для подписи из строкового представления объекта
    display_text = str(obj)

    try:
        font = ImageFont.truetype("arial.ttf", 14)
    except IOError:
        font = ImageFont.load_default()

    # 7. Создаем новый холст, чтобы разместить на нем текст и штрихкод
    temp_draw = ImageDraw.Draw(barcode_img)
    text_bbox = temp_draw.textbbox((0, 0), display_text, font=font)
    text_width = text_bbox[2] - text_bbox[0]
    text_height = text_bbox[3] - text_bbox[1]
    
    padding = 10
    new_width = max(barcode_img.width, text_width) + padding * 2
    new_height = barcode_img.height + text_height + padding * 2

    final_image = Image.new('RGB', (new_width, new_height), 'white')
    draw = ImageDraw.Draw(final_image)

    # 8. Рисуем текст (название объекта)
    text_x = (new_width - text_width) / 2
    text_y = padding
    draw.text((text_x, text_y), display_text, fill='black', font=font)

    # 9. Вставляем изображение штрихкода под текстом
    barcode_x = (new_width - barcode_img.width) / 2
    barcode_y = text_y + text_height + 5
    final_image.paste(barcode_img, (int(barcode_x), int(barcode_y)))

    # 10. Сохраняем итоговое изображение в буфер
    final_buffer = io.BytesIO()
    final_image.save(final_buffer, format='PNG')
    
    return HttpResponse(final_buffer.getvalue(), content_type='image/png')

# ==============================================================================
# Глобальный поиск по названию, артикулу, штрихкоду
# ==============================================================================

def global_search_view(request):
    query = request.GET.get('q', '').strip()

    if not query:
        # Если запрос пустой, просто возвращаемся назад
        return redirect(request.META.get('HTTP_REFERER', '/'))

    # 1. ОПРЕДЕЛЯЕМ ЗАПРОСЫ
    # Запрос для склада 1 (Материалы)
    material_query = (
        Q(name__icontains=query) |
        Q(article__icontains=query) |
        Q(barcode__exact=query)
    )
    # Запрос для склада 2 (Продукция), который включает поиск по упаковкам
    product_query = (
        Q(name__icontains=query) |
        Q(sku__icontains=query) |
        Q(barcode__exact=query) |
        Q(packages__barcode__exact=query)
    )

    # 2. ВЫПОЛНЯЕМ ПОИСК ОДИН РАЗ
    materials_found = Material.objects.filter(material_query)
    products_found = Product.objects.filter(product_query).distinct()

    # 3. ПРОВЕРЯЕМ РЕЗУЛЬТАТЫ И ПРИНИМАЕМ РЕШЕНИЕ
    materials_exist = materials_found.exists()
    products_exist = products_found.exists()

    # Случай 1: Найдены ТОЛЬКО материалы
    if materials_exist and not products_exist:
        base_url = reverse('material_list')
        query_params = urlencode({'search': query})
        url = f'{base_url}?{query_params}'
        messages.info(request, f'Показаны результаты поиска по материалам для "{query}"')
        return redirect(url)

    # Случай 2: Найдена ТОЛЬКО готовая продукция
    elif products_exist and not materials_exist:
        base_url = reverse('product_list')
        query_params = urlencode({'search': query})
        url = f'{base_url}?{query_params}'
        messages.info(request, f'Показаны результаты поиска по готовой продукции для "{query}"')
        return redirect(url)

    # Случай 3: Найдены ОБА типа (неоднозначный поиск)
    elif materials_exist and products_exist:
        context = {
            'query': query,
            'materials': materials_found, # Используем уже найденные результаты
            'products': products_found,   # Используем уже найденные результаты
        }
        messages.warning(request, f'Найдены результаты на обоих складах для "{query}"')
        return render(request, 'search_results.html', context)

    # Случай 4: Ничего не найдено (этот блок сработает, если оба exists() вернут False)
    else:
        messages.error(request, f'По запросу "{query}" ничего не найдено.')
        return redirect(request.META.get('HTTP_REFERER', '/'))

