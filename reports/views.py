from django.views.generic import TemplateView
from django.http import JsonResponse
from django.db.models import Sum, F, Q, Value, CharField
from django.db.models.functions import TruncDay, TruncMonth
from django.utils import timezone
from datetime import timedelta
from django.contrib.auth.decorators import login_required
from django.contrib.auth.mixins import LoginRequiredMixin
from django.core.paginator import Paginator

from .forms import MovementReportFilterForm
from warehouse1.models import MaterialOperation
from warehouse2.models import ProductOperation
from warehouse2.models import Shipment, ShipmentItem

class ReportsHomeView(LoginRequiredMixin, TemplateView):
    template_name = 'reports/reports_home.html'
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['page_title'] = 'Reports Home'
        context['user'] = self.request.user
        return context

class SalesOverTimeView(LoginRequiredMixin, TemplateView):
    """
    Просто отображает HTML-шаблон, в котором будет график.
    Всю работу по загрузке данных выполнит JavaScript.
    """
    template_name = 'reports/sales_over_time.html'

@login_required
def sales_chart_data_api(request):
    """
    API, которое возвращает данные для графика продаж.
    Принимает GET-параметр 'period' ('week', 'month', 'year').
    """
    # 1. Получаем период из запроса, по умолчанию - 'month'
    period = request.GET.get('period', 'month')
    today = timezone.now()
    
    # 2. Определяем дату начала и способ группировки (trunc_kind)
    if period == 'year':
        start_date = today - timedelta(days=365)
        trunc_kind = TruncMonth('shipped_at')
        label_format = '%B %Y' # Формат для метки (напр. "Сентябрь 2025")
    elif period == 'week':
        start_date = today - timedelta(days=7)
        trunc_kind = TruncDay('shipped_at')
        label_format = '%d.%m' # Формат для метки (напр. "14.09")
    else: # По умолчанию 'month'
        start_date = today - timedelta(days=30)
        trunc_kind = TruncDay('shipped_at')
        label_format = '%d.%m'

    # 3. Выполняем запрос к БД с учетом периода и группировки
    sales_data = Shipment.objects.filter(
        status='shipped',
        shipped_at__gte=start_date
    ).select_related(
        # добавьте связанные модели если нужно
    ).prefetch_related(
        'items'  # предзагрузка связанных items
    ).annotate(
        date=trunc_kind
    ).values(
        'date'
    ).annotate(
        total_revenue=Sum(F('items__price') * F('items__quantity'))
    ).order_by('date')

    # 4. Форматируем данные для графика
    labels = [d['date'].strftime(label_format) for d in sales_data]
    data = [float(d['total_revenue']) for d in sales_data]

    return JsonResponse({
        'labels': labels,
        'data': data,
    })

def get_unified_movement_data(filters):
    """
    Собирает данные из обоих журналов операций,
    стандартизирует и возвращает единый отсортированный список.
    """
    start_date = filters.get('start_date')
    end_date = filters.get('end_date')
    operation_type = filters.get('operation_type')
    item_search = filters.get('item_search')

    # 1. Получаем операции с продукцией (Склад 2)
    product_ops_qs = ProductOperation.objects.select_related('product', 'user').all()
    if start_date:
        product_ops_qs = product_ops_qs.filter(timestamp__gte=start_date)
    if end_date:
        product_ops_qs = product_ops_qs.filter(timestamp__lte=end_date)
    if operation_type:
        product_ops_qs = product_ops_qs.filter(operation_type=operation_type)
    if item_search:
        product_ops_qs = product_ops_qs.filter(
            Q(product__name__icontains=item_search) | Q(product__sku__icontains=item_search)
        )
    
    # 2. Получаем операции с материалами (Склад 1)
    material_ops_qs = MaterialOperation.objects.select_related('material', 'user', 'material__unit').all()
    if start_date:
        material_ops_qs = material_ops_qs.filter(date__gte=start_date)
    if end_date:
        material_ops_qs = material_ops_qs.filter(date__lte=end_date)
    # Адаптируем типы операций для материалов
    if operation_type in ['incoming', 'outgoing', 'adjustment']:
        material_ops_qs = material_ops_qs.filter(operation_type=operation_type)
    elif operation_type: # Если выбран тип, которого нет у материалов
        material_ops_qs = material_ops_qs.none()
    if item_search:
        material_ops_qs = material_ops_qs.filter(
            Q(material__name__icontains=item_search) | Q(material__article__icontains=item_search)
        )

    # 3. Стандартизируем и объединяем
    unified_list = []
    for op in product_ops_qs:
        unified_list.append({
            'timestamp': op.timestamp,
            'item_name': op.product.name,
            'item_sku': op.product.sku,
            'warehouse': 'Готовая продукция',
            'operation': op.get_operation_type_display(),
            'quantity': op.quantity,
            'user': op.user.username if op.user else 'N/A',
            'source': str(op.source) if op.source else 'Ручная операция'
        })
    
    for op in material_ops_qs:
        unified_list.append({
            'timestamp': op.date,
            'item_name': op.material.name,
            'item_sku': op.material.article,
            'warehouse': 'Сырье и материалы',
            'operation': op.get_operation_type_display(),
            'quantity': op.quantity,
            'user': op.user.username if op.user else 'N/A',
            'source': op.outgoing_category.name if op.outgoing_category else 'Приемка'
        })

    # 4. Сортируем общий список по дате
    unified_list.sort(key=lambda x: x['timestamp'], reverse=True)
    
    return unified_list

class MovementReportView(LoginRequiredMixin, TemplateView):
    template_name = 'reports/movement_report.html'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        form = MovementReportFilterForm(self.request.GET or None)
        
        operations = []
        if form.is_valid():
            operations = get_unified_movement_data(form.cleaned_data)

        # Ручная пагинация, так как у нас обычный список, а не QuerySet
        paginator = Paginator(operations, 25) # по 25 записей на странице
        page_number = self.request.GET.get('page')
        page_obj = paginator.get_page(page_number)
        
        context['filter_form'] = form
        context['page_obj'] = page_obj
        return context