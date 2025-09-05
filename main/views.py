from django.shortcuts import render, redirect
from django.contrib.auth import authenticate, login, logout
from .forms import LoginForm
from django.shortcuts import get_object_or_404
from django.http import HttpResponse, Http404
from django.contrib.contenttypes.models import ContentType
import barcode
from barcode.writer import ImageWriter
import io
from django.views.generic import View
from django.contrib.auth.mixins import LoginRequiredMixin
from warehouse2.models import Shipment, WorkOrder
from django.contrib import messages
from django.db.models import Q
from warehouse1.models import Material
from warehouse2.models import Product
from django.urls import reverse
from urllib.parse import urlencode


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
        
        context = {
            'user': request.user,
            'pending_shipments': pending_shipments,
            'pending_workorders': pending_workorders,
            'pending_shipments_count': Shipment.objects.filter(status__in=['pending', 'packaged']).count(),
            'pending_workorders_count': WorkOrder.objects.filter(status__in=['new', 'in_progress']).count(),
        }
        return render(request, 'index.html', context)
    
# ==============================================================================
# Генерация штрихкода для любого объекта
# ==============================================================================

def generate_barcode_view(request, content_type_id, object_id):
    """
    Универсальное view для генерации штрихкода для любого объекта.
    """
    try:
        # 1. Находим "удостоверение" модели по ее ID
        content_type = get_object_or_404(ContentType, pk=content_type_id)
        
        # 2. Находим сам объект (Product, Material и т.д.) по его ID
        obj = content_type.get_object_for_this_type(pk=object_id)

    except ContentType.DoesNotExist:
        raise Http404("Указанный тип контента не существует")

    # 3. Проверяем, есть ли у объекта поле 'barcode'
    if not hasattr(obj, 'barcode'):
        raise Http404("У этого объекта нет поля 'barcode'")

    # 4. Генерируем изображение штрихкода (как и раньше)
    CODE128 = barcode.get_barcode_class('code128')
    writer = ImageWriter(format='PNG')
    code = CODE128(obj.barcode, writer=writer)
    
    buffer = io.BytesIO()
    code.write(buffer)
    
    return HttpResponse(buffer.getvalue(), content_type='image/png')

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
