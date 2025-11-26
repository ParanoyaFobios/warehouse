from django.views.generic import ListView, DetailView, CreateView, UpdateView, DeleteView, FormView
from django.urls import reverse_lazy
from django.shortcuts import get_object_or_404, redirect
from django.contrib import messages
from django.contrib.auth.mixins import LoginRequiredMixin
from django.db import transaction
from django.db.models import F
from django import forms

# Импортируем НОВЫЕ модели и формы
from .models import ProductionOrder, ProductionOrderItem, WorkOrder
from .forms import (
    ProductionOrderForm, ProductionOrderItemFormSet, 
    WorkOrderAdHocForm, ReportProductionForm
)

# ==============================================================================
# Вью для "Портфеля заказов" (Header/Detail) - ОБНОВЛЕНО
# ==============================================================================

class ProductionOrderListView(LoginRequiredMixin, ListView):
    model = ProductionOrder # <-- Новая "шапка"
    template_name = 'todo/portfolio_list.html'
    context_object_name = 'orders'

class ProductionOrderDetailView(LoginRequiredMixin, DetailView):
    model = ProductionOrder # <-- Новая "шапка"
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
    Создает WorkOrders (Задания) для ВСЕХ невыполненных строк 
    в ProductionOrder.
    """
    template_name = 'todo/plan_workorders_form.html' # <-- Новый шаблон
    form_class = forms.Form # Простая форма, можно и без нее

    def setup(self, request, *args, **kwargs):
        super().setup(request, *args, **kwargs)
        self.portfolio_order = get_object_or_404(ProductionOrder, pk=self.kwargs['pk'])

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['order'] = self.portfolio_order
        context['lines_to_plan'] = self.portfolio_order.lines.filter(
            quantity_requested__gt=F('quantity_planned') # Находим строки, где план < запроса
        )
        return context

    def form_valid(self, form):
        order = self.portfolio_order
        lines_to_plan = order.lines.filter(quantity_requested__gt=F('quantity_planned'))
        
        created_count = 0
        with transaction.atomic():
            for line in lines_to_plan:
                quantity_to_plan = line.remaining_to_plan
                
                if quantity_to_plan > 0:
                    # Создаем Задание на смену (WorkOrder)
                    WorkOrder.objects.create(
                        order_line=line,
                        product=line.product,
                        quantity_planned=quantity_to_plan,
                        comment=f"По заказу №{order.id} (Заказчик: {order.customer})"
                    )
                    
                    # Обновляем строку, что мы ее запланировали
                    line.quantity_planned = line.quantity_requested
                    line.status = ProductionOrderItem.Status.PLANNED
                    line.save()
                    created_count += 1
            
            # Обновляем статус "шапки"
            if created_count > 0:
                order.status = ProductionOrder.Status.PLANNED
                order.save()

        if created_count > 0:
            messages.success(self.request, f'Создано {created_count} заданий на смену.')
        else:
            messages.info(self.request, 'Нет строк, требующих планирования.')
            
        return redirect('portfolio_detail', pk=order.pk)

# ==============================================================================
# Вью для "Доски объявлений" (WorkOrder) - БЕЗ ИЗМЕНЕНИЙ
# ==============================================================================

class WorkOrderListView(LoginRequiredMixin, ListView):
    # ... (без изменений) ...
    model = WorkOrder
    template_name = 'todo/workorder_list.html'
    context_object_name = 'workorders'
    def get_queryset(self):
        return WorkOrder.objects.filter(status__in=['new', 'in_progress']).order_by('created_at')

class WorkOrderAdHocCreateView(LoginRequiredMixin, CreateView):
    # ... (без изменений) ...
    model = WorkOrder
    form_class = WorkOrderAdHocForm
    template_name = 'todo/form.html' # <-- Эта форма использует старый шаблон
    success_url = reverse_lazy('workorder_list')
    extra_context = {'form_title': 'Новое Ad-Hoc Задание'}

class ReportProductionView(LoginRequiredMixin, FormView):
    # ... (без изменений) ...
    template_name = 'todo/report_production_form.html'
    form_class = ReportProductionForm
    # ... (остальная логика) ...
    
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