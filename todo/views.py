from django.views.generic import ListView, DetailView, CreateView, UpdateView, DeleteView, FormView
from django.urls import reverse_lazy
from django.shortcuts import get_object_or_404, redirect
from django.contrib import messages
from django.contrib.auth.mixins import LoginRequiredMixin
from django.db import transaction
from django.db.models import F, Q
from django import forms
from .models import ProductionOrder, ProductionOrderItem, WorkOrder
from .forms import (
    ProductionOrderForm, ProductionOrderItemFormSet, 
    WorkOrderAdHocForm, ReportProductionForm)

# ==============================================================================
# Вью для "Портфеля заказов" (Header/Detail)
# ==============================================================================

class ProductionOrderListView(LoginRequiredMixin, ListView):
    model = ProductionOrder
    template_name = 'todo/portfolio_list.html'
    context_object_name = 'orders'

class ProductionOrderDetailView(LoginRequiredMixin, DetailView):
    model = ProductionOrder
    template_name = 'todo/portfolio_detail.html'
    context_object_name = 'order'
    # 'order.items.all' будет доступен в шаблоне

class ProductionOrderCreateView(LoginRequiredMixin, CreateView):
    """Создание Заказа (шапка) + Строк (инлайн-формсет)"""
    model = ProductionOrder
    form_class = ProductionOrderForm
    template_name = 'todo/portfolio_order_form.html' # <-- Новый шаблон
    success_url = reverse_lazy('portfolio_list')

    def get_context_data(self, **kwargs):
        data = super().get_context_data(**kwargs)
        if self.request.POST:
            data['items_formset'] = ProductionOrderItemFormSet(self.request.POST)
        else:
            data['items_formset'] = ProductionOrderItemFormSet()
        return data

    def form_valid(self, form):
        context = self.get_context_data()
        items_formset = context['items_formset']
        
        with transaction.atomic(): # <-- Гарантируем, что все или ничего
            self.object = form.save()
            if items_formset.is_valid():
                items_formset.instance = self.object
                items_formset.save()
            else:
                # Если формсет невалиден, откатываем все
                return self.form_invalid(form)

        messages.success(self.request, 'Заказ успешно создан')
        return super().form_valid(form)

class ProductionOrderUpdateView(LoginRequiredMixin, UpdateView):
    """Обновление Заказа (шапка) + Строк (инлайн-формсет)"""
    model = ProductionOrder
    form_class = ProductionOrderForm
    template_name = 'todo/portfolio_order_form.html' # <-- Новый шаблон
    success_url = reverse_lazy('portfolio_list')

    def get_context_data(self, **kwargs):
        data = super().get_context_data(**kwargs)
        if self.request.POST:
            data['items_formset'] = ProductionOrderItemFormSet(
                self.request.POST, instance=self.object
            )
        else:
            data['items_formset'] = ProductionOrderItemFormSet(instance=self.object)
        return data

    def form_valid(self, form):
        context = self.get_context_data()
        items_formset = context['items_formset']
        
        with transaction.atomic():
            self.object = form.save()
            if items_formset.is_valid():
                items_formset.instance = self.object
                items_formset.save()
            else:
                return self.form_invalid(form)

        messages.success(self.request, 'Заказ успешно обновлен')
        return super().form_valid(form)

class ProductionOrderDeleteView(LoginRequiredMixin, DeleteView):
    model = ProductionOrder
    template_name = 'todo/confirm_delete.html'
    success_url = reverse_lazy('portfolio_list')

# ==============================================================================
# НОВАЯ ВЬЮ: "Планировать всё"
# ==============================================================================

class PlanWorkOrdersView(LoginRequiredMixin, FormView):
    """
    Берет "Заказ Портфеля" и создает из него "Задания на смену" (WorkOrders).
    """
    template_name = 'todo/plan_workorders_form.html'
    form_class = forms.Form # Нам нужна пустая форма просто для CSRF токена и POST запроса

    def setup(self, request, *args, **kwargs):
        super().setup(request, *args, **kwargs)
        # Получаем заказ по ID из URL
        self.portfolio_order = get_object_or_404(ProductionOrder, pk=self.kwargs['pk'])

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['order'] = self.portfolio_order
        # Показываем только те строки, где План < Запроса (то есть еще не все отправлено в цех)
        context['lines_to_plan'] = self.portfolio_order.items.filter(
            quantity_requested__gt=F('quantity_planned')
        )
        return context

    def form_valid(self, form):
        order = self.portfolio_order
        # Выбираем строки, которые нужно запланировать
        lines_to_plan = order.items.filter(quantity_requested__gt=F('quantity_planned'))
        
        created_count = 0
        
        # transaction.atomic гарантирует: либо создадутся ВСЕ задания, либо (при ошибке) НИ ОДНОГО.
        # Это защищает от дублей и рассинхрона данных.
        with transaction.atomic():
            for line in lines_to_plan:
                quantity_to_plan = line.remaining_to_plan
                
                if quantity_to_plan > 0:
                    # 1. Создаем Задание на смену (WorkOrder)
                    WorkOrder.objects.create(
                        order_item=line, # Привязываем к строке
                        product=line.product, # Дублируем продукт для удобства
                        quantity_planned=quantity_to_plan,
                        comment=f"По заказу №{order.id} (Заказчик: {order.customer})"
                    )
                    
                    # 2. Обновляем строку (Items): говорим, что мы передали это кол-во в план
                    line.quantity_planned = F('quantity_planned') + quantity_to_plan
                    line.status = ProductionOrderItem.Status.PLANNED
                    line.save()
                    created_count += 1
            
            # 3. Обновляем статус самого Заказа (Header)
            if created_count > 0:
                order.status = ProductionOrder.Status.PLANNED
                order.save()

        if created_count > 0:
            messages.success(self.request, f'Успешно создано {created_count} заданий на смену. Они появились на доске.')
        else:
            messages.info(self.request, 'Все позиции заказа уже были запланированы ранее.')
            
        # Возвращаем пользователя на детальную страницу заказа
        return redirect('portfolio_detail', pk=order.pk)

# ==============================================================================
# Вью для "Доски объявлений" (WorkOrder) - БЕЗ ИЗМЕНЕНИЙ
# ==============================================================================

class WorkOrderListView(LoginRequiredMixin, ListView):
    model = WorkOrder
    template_name = 'todo/workorder_list.html'
    context_object_name = 'workorders'

    def get_queryset(self):
        # 1. Получаем параметр даты из GET-запроса
        due_date_str = self.request.GET.get('due_date')
        
        # 2. Базовый QuerySet
        queryset = WorkOrder.objects.all()

        if due_date_str:
            # Пользователь выбрал дату: ищем задания, связанные с заказами на эту дату
            try:
                # Фильтруем WorkOrder по полю order_item -> order -> due_date.
                # Также включаем WorkOrder, которые не привязаны к заказу (Ad-Hoc), 
                # но были завершены в этот день (для полноты картины).
                queryset = queryset.filter(
                    Q(order_item__production_order__due_date=due_date_str) | 
                    Q(completed_at__date=due_date_str, order_item__isnull=True)
                ).order_by('-completed_at', 'created_at') # Сортируем по дате завершения, чтобы выполненные были сверху
                
                # Сохраняем дату в контексте, чтобы вернуть ее в шаблон
                self.filtered_date = due_date_str
                
            except ValueError:
                # Если дата введена некорректно, игнорируем фильтр
                messages.error(self.request, "Введена некорректная дата.")
                self.filtered_date = None
                
        # Если фильтр по дате НЕ применен или был некорректен, показываем только активные задания
        if not due_date_str or not hasattr(self, 'filtered_date'):
            queryset = queryset.filter(status__in=[WorkOrder.Status.NEW, WorkOrder.Status.IN_PROGRESS]).order_by('created_at')

        return queryset

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        # Передаем статус фильтрации в шаблон
        context['is_filtered_by_date'] = hasattr(self, 'filtered_date') and self.filtered_date
        return context

class WorkOrderAdHocCreateView(LoginRequiredMixin, CreateView):
    """
    Создание задания на смену, не привязанного к портфелю (Ad-Hoc).
    """
    model = WorkOrder
    form_class = WorkOrderAdHocForm
    template_name = 'todo/form.html' 
    success_url = reverse_lazy('workorder_list')
    extra_context = {'form_title': 'Новое Ad-Hoc Задание на смену'}

    def form_valid(self, form):
        # При создании Ad-Hoc задания, order_item остается NULL, 
        # так как нет привязки к PortfolioOrder.
        self.object = form.save(commit=False)
        # Если нужно сохранить пользователя, который создал:
        self.object.created_by = self.request.user
        self.object.save()
        messages.success(self.request, f"Задание '{self.object.product.name}' успешно создано.")
        return super().form_valid(form)

class ReportProductionView(LoginRequiredMixin, FormView):
    """
    Форма для отчета о фактическом производстве по WorkOrder.
    """
    template_name = 'todo/report_production_form.html'
    form_class = ReportProductionForm
    
    def setup(self, request, *args, **kwargs):
        super().setup(request, *args, **kwargs)
        # Получаем WorkOrder, по которому отчитываемся
        self.work_order = get_object_or_404(WorkOrder, pk=self.kwargs['pk'])

    def get_form_kwargs(self):
        """Передаем WorkOrder в форму, чтобы установить max_value и initial"""
        kwargs = super().get_form_kwargs()
        kwargs['work_order'] = self.work_order
        return kwargs

    def get_context_data(self, **kwargs):
        """Передаем WorkOrder в шаблон для отображения деталей"""
        context = super().get_context_data(**kwargs)
        context['workorder'] = self.work_order
        return context

    def form_valid(self, form):
        quantity_done = form.cleaned_data['quantity_done']
        work_order = self.work_order

        if quantity_done <= 0:
            messages.error(self.request, "Количество должно быть больше нуля.")
            return self.form_invalid(form)

        if quantity_done > work_order.remaining_to_produce:
            messages.error(self.request, f"Нельзя выпустить больше, чем осталось в плане ({work_order.remaining_to_produce} шт.).")
            return self.form_invalid(form)

        # Вызываем метод, который мы определили в models.py
        success, message = work_order.report_production(quantity_done, self.request.user)

        if success:
            messages.success(self.request, message)
        else:
            messages.error(self.request, message)

        # Редирект обратно на Доску объявлений
        return redirect('workorder_list')
    
# ... (WorkOrderUpdateView, WorkOrderDeleteView без изменений) ...
class WorkOrderUpdateView(LoginRequiredMixin, UpdateView):
    model = WorkOrder
    form_class = WorkOrderAdHocForm
    template_name = 'todo/form.html'
    success_url = reverse_lazy('workorder_list')
    extra_context = {'form_title': 'Редактировать задание'}

class WorkOrderDeleteView(LoginRequiredMixin, DeleteView):
    model = WorkOrder
    template_name = 'todo/confirm_delete.html'
    success_url = reverse_lazy('workorder_list')