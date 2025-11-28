from django.views.generic import ListView, DetailView, CreateView, UpdateView, DeleteView, FormView
from django.urls import reverse_lazy
from django.shortcuts import get_object_or_404, redirect
from django.contrib import messages
from django.contrib.auth.mixins import LoginRequiredMixin
from django.db import transaction
from django.db.models import F, Q
from django import forms
from .models import ProductionOrder, ProductionOrderItem, WorkOrder
from .forms import ProductionOrderForm, WorkOrderAdHocForm, ReportProductionForm
import json
from warehouse2.models import Product
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
    model = ProductionOrder
    form_class = ProductionOrderForm
    template_name = 'todo/portfolio_order_form.html'
    success_url = reverse_lazy('portfolio_list')

    def form_valid(self, form):
        # 1. Получаем JSON строку из скрытого инпута
        items_json = self.request.POST.get('items_data')
        
        if not items_json:
            messages.error(self.request, "Список товаров пуст.")
            return self.form_invalid(form)

        try:
            items_data = json.loads(items_json)
        except json.JSONDecodeError:
            messages.error(self.request, "Ошибка данных (неверный JSON).")
            return self.form_invalid(form)

        if not items_data:
            messages.error(self.request, "Добавьте хотя бы один товар в заказ.")
            return self.form_invalid(form)

        # Открываем транзакцию: либо сохраним всё, либо ничего
        with transaction.atomic():
            # 2. Сохраняем сам заказ (Header)
            self.object = form.save()

            # 3. Проходим циклом по JSON и создаем строки (Items)
            for item in items_data:
                product_id = item.get('id')
                qty = item.get('qty')

                if product_id and qty:
                    try:
                        product_obj = Product.objects.get(pk=product_id)
                        ProductionOrderItem.objects.create(
                            production_order=self.object, # Привязка к родителю
                            product=product_obj,
                            quantity_requested=int(qty)
                        )
                    except Product.DoesNotExist:
                        # Если вдруг товара уже нет в базе
                        pass 

        messages.success(self.request, f"Заказ №{self.object.id} успешно создан ({len(items_data)} поз.)")
        return redirect(self.success_url)

class ProductionOrderUpdateView(LoginRequiredMixin, UpdateView):
    """
    Обновление Заказа (шапка) с синхронизацией строк по данным из JSON.
    """
    model = ProductionOrder
    form_class = ProductionOrderForm
    template_name = 'todo/portfolio_order_form.html'
    success_url = reverse_lazy('portfolio_list')

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        # Загружаем существующие строки заказа для JS
        existing_items = self.object.items.all().select_related('product')
        
        # Преобразуем данные в JSON-строку для использования в JavaScript
        items_data_for_js = []
        for item in existing_items:
            # Важно: включаем PK строки, чтобы JS знал, что ее нужно обновить, а не создать
            items_data_for_js.append({
                'pk': item.pk, 
                'id': item.product.pk, # ID продукта
                'name': item.product.name,
                'sku': item.product.sku,
                'qty': float(item.quantity_requested) # Передаем как число
            })
            
        # Отправляем JSON-строку в контекст
        context['existing_items_json'] = json.dumps(items_data_for_js)
        return context

    def form_valid(self, form):
        items_json = self.request.POST.get('items_data')
        
        if not items_json:
            messages.error(self.request, "Список товаров пуст.")
            return self.form_invalid(form)

        try:
            new_items_data = json.loads(items_json)
        except json.JSONDecodeError:
            messages.error(self.request, "Ошибка данных (неверный JSON).")
            return self.form_invalid(form)

        with transaction.atomic():
            # 1. Сохраняем шапку заказа
            self.object = form.save()
            current_item_pks = set()
            
            # 2. Обрабатываем новые/существующие строки из POST
            for item in new_items_data:
                item_pk = item.get('pk')
                product_id = item.get('id')
                qty = int(item.get('qty', 0))

                if product_id and qty > 0:
                    
                    if item_pk:
                        # СТРОКА СУЩЕСТВУЕТ: ОБНОВЛЯЕМ
                        item_obj = ProductionOrderItem.objects.get(pk=item_pk, production_order=self.object)
                        item_obj.quantity_requested = qty
                        item_obj.save()
                        current_item_pks.add(item_pk)
                    else:
                        # СТРОКА НОВАЯ: СОЗДАЕМ
                        product_obj = Product.objects.get(pk=product_id)
                        new_item = ProductionOrderItem.objects.create(
                            production_order=self.object,
                            product=product_obj,
                            quantity_requested=qty
                        )
                        current_item_pks.add(new_item.pk)

            # 3. Удаляем строки, которые отсутствуют в новом списке
            # Находим все PK, которые были в базе, но НЕ пришли в POST
            items_to_delete = self.object.items.exclude(pk__in=current_item_pks)
            
            # Внимание: здесь нужно добавить проверку! Нельзя удалять строки, 
            # по которым уже начато производство (quantity_planned > 0)
            
            safe_to_delete_count = items_to_delete.filter(quantity_planned=0).count()
            items_to_delete.filter(quantity_planned=0).delete()
            
            if items_to_delete.filter(quantity_planned__gt=0).exists():
                 messages.warning(self.request, "Не удалось удалить некоторые позиции, так как по ним уже начато производство!")
            
        messages.success(self.request, 'Заказ успешно обновлен.')
        return redirect(self.get_success_url())

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
        # 1. Получаем параметры из GET-запроса
        due_date_str = self.request.GET.get('due_date')
        # ИСПРАВЛЕНО: используем правильное имя production_order_id
        production_order_id_str = self.request.GET.get('production_order_id') 
        
        # Флаг для отслеживания, была ли применена фильтрация пользователем
        is_filtered = False
        
        # 2. Базовый QuerySet
        queryset = WorkOrder.objects.all()

        # --- Фильтрация по дате (если задана) ---
        if due_date_str:
            is_filtered = True
            try:
                # Фильтруем WorkOrder по дате заказа ИЛИ по дате завершения (для Ad-Hoc)
                queryset = queryset.filter(
                    Q(order_item__production_order__due_date=due_date_str) | 
                    Q(completed_at__date=due_date_str, order_item__isnull=True)
                )
                self.filtered_date = due_date_str
            except ValueError:
                messages.error(self.request, "Введена некорректная дата.")
                self.filtered_date = None
                # Если дата некорректна, фактически фильтрация не состоялась.
                
        # --- Фильтрация по номеру заказа (если задана) ---
        if production_order_id_str and production_order_id_str.isdigit():
            is_filtered = True
            try:
                production_order_id = int(production_order_id_str)
                # Фильтруем WorkOrder, которые привязаны к строке заказа, 
                # которая, в свою очередь, привязана к указанному ProductionOrder.id
                # Эта фильтрация ДОБАВЛЯЕТСЯ к предыдущей (если она была)
                queryset = queryset.filter(order_item__production_order__id=production_order_id)
                self.filtered_production_order_id = production_order_id_str
            except ValueError:
                # Хотя мы проверили isdigit(), оставляем на всякий случай
                messages.error(self.request, "Некорректный идентификатор заказа.")
                self.filtered_production_order_id = None
        
        # --- Логика по умолчанию ---
        
        # Если НЕ БЫЛО применено никаких фильтров (ни дата, ни номер заказа),
        # показываем только активные задания (NEW, IN_PROGRESS).
        if not is_filtered:
            queryset = queryset.filter(
                status__in=[WorkOrder.Status.NEW, WorkOrder.Status.IN_PROGRESS]
            ).order_by('created_at')
        else:
            # Если фильтры были, применяем общую сортировку (сначала выполненные)
            queryset = queryset.order_by('-completed_at', 'created_at')

        return queryset
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        # Передаем статус фильтрации в шаблон
        # Улучшенная проверка: true, если хотя бы один из параметров был задан и корректен
        context['is_filtered'] = bool(self.request.GET.get('due_date') or self.request.GET.get('production_order_id'))
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