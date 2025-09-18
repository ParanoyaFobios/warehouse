from django.views.generic import TemplateView, FormView
from django.http import JsonResponse
from django.db.models import Sum, F, Q, Value, CharField
from django.db.models.functions import TruncDay, TruncMonth
from django.utils import timezone
from datetime import timedelta, date
from django.contrib.auth.decorators import login_required
from django.contrib.auth.mixins import LoginRequiredMixin
from django.core.paginator import Paginator, EmptyPage, PageNotAnInteger
from reports.servises import get_unified_movement_data, generate_movement_report_excel

from .forms import MovementReportFilterForm, DateRangeFilterForm
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


class MovementReportView(LoginRequiredMixin, TemplateView):
    template_name = 'reports/movement_report.html'

    def get(self, request, *args, **kwargs):
        form = MovementReportFilterForm(request.GET or None)
        operations = []
        
        if form.is_valid():
            operations = get_unified_movement_data(form.cleaned_data)

        # Проверяем, если запрос на выгрузку в Excel
        if 'export_excel' in request.GET:
            return generate_movement_report_excel(operations)
        
        # Если не экспорт, то продолжаем с пагинацией и рендерингом
        try:
            per_page = int(request.GET.get('per_page', 25))
            if per_page > 500: per_page = 500 # Ограничение
        except (ValueError, TypeError):
            per_page = 25
            
        paginator = Paginator(operations, per_page)
        page_number = request.GET.get('page')
        page_obj = paginator.get_page(page_number)
        
        context = {
            'filter_form': form,
            'page_obj': page_obj,
            'per_page': per_page,
            'per_page_options': [25, 50, 100, 200, 500]
        }
        return self.render_to_response(context)
    
class SalesByProductReportView(LoginRequiredMixin, FormView):
    """
    Отображает страницу с фильтрами и холстами для графиков.
    """
    template_name = 'reports/sales_by_product_report.html'
    form_class = DateRangeFilterForm

@login_required
def sales_by_product_api(request):
    """
    API для отчета "Топ-10 товаров по выручке".
    """
    form = DateRangeFilterForm(request.GET)
    if not form.is_valid():
        return JsonResponse({'error': 'Invalid date format'}, status=400)

    # Устанавливаем период по умолчанию (последние 30 дней), если даты не указаны
    start_date = form.cleaned_data.get('start_date') or date.today() - timedelta(days=30)
    end_date = form.cleaned_data.get('end_date') or date.today()

    # Агрегируем данные: группируем по товару и считаем сумму продаж
    sales_data = ShipmentItem.objects.filter(
        shipment__status='shipped',
        shipment__shipped_at__date__range=[start_date, end_date]
    ).values(
        'product__name' # Группируем по имени продукта
    ).annotate(
        total_revenue=Sum(F('price') * F('quantity'))
    ).order_by('-total_revenue')[:10] # Сортируем по убыванию выручки и берем топ-10

    labels = [item['product__name'] for item in sales_data]
    data = [float(item['total_revenue']) for item in sales_data]
    
    return JsonResponse({'labels': labels, 'data': data})

@login_required
def sales_by_category_api(request):
    """
    API для отчета "Выручка по категориям".
    """
    form = DateRangeFilterForm(request.GET)
    if not form.is_valid():
        return JsonResponse({'error': 'Invalid date format'}, status=400)

    start_date = form.cleaned_data.get('start_date') or date.today() - timedelta(days=30)
    end_date = form.cleaned_data.get('end_date') or date.today()

    # Агрегируем данные: группируем по категории и считаем сумму
    category_data = ShipmentItem.objects.filter(
        shipment__status='shipped',
        shipment__shipped_at__date__range=[start_date, end_date]
    ).values(
        'product__category__name' # Группируем по имени категории
    ).annotate(
        total_revenue=Sum(F('price') * F('quantity'))
    ).order_by('-total_revenue')

    labels = [item['product__category__name'] for item in category_data]
    data = [float(item['total_revenue']) for item in category_data]

    return JsonResponse({'labels': labels, 'data': data})