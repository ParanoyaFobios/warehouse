from django.shortcuts import redirect, get_object_or_404
from django.views.generic import ListView, FormView
from django.contrib.auth.mixins import LoginRequiredMixin, PermissionRequiredMixin
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.contrib.contenttypes.models import ContentType
from django.http import JsonResponse
from django.db.models import Q
from django.utils import timezone
from .models import InventoryCount, InventoryCountItem
from .forms import InventoryItemForm, InventoryItemUpdateForm
from warehouse1.models import Material
from warehouse2.models import Product, Package
from django.views.generic import DetailView, View
from django.db import transaction
from warehouse1.models import MaterialOperation
from warehouse2.models import ProductOperation

class InventoryCountListView(LoginRequiredMixin, ListView):
    model = InventoryCount
    template_name = 'inventarization/count_list.html'
    context_object_name = 'inventory_counts'
    ordering = ['-created_at']

class StartInventoryCountView(LoginRequiredMixin, View):
    def post(self, request, *args, **kwargs):
        active_count = InventoryCount.objects.filter(user=request.user, status='in_progress').first()
        if active_count:
            messages.warning(request, "У вас уже есть незавершенный переучет. Вы были перенаправлены на него.")
            return redirect('count_work', pk=active_count.pk)
        
        new_count = InventoryCount.objects.create(user=request.user)
        messages.success(request, f"Начат новый переучет №{new_count.id}")
        return redirect('count_work', pk=new_count.pk)

class InventoryCountWorkView(LoginRequiredMixin, FormView):
    template_name = 'inventarization/count_work.html'
    form_class = InventoryItemForm

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        inventory_count = get_object_or_404(InventoryCount, pk=self.kwargs['pk'])
        context['inventory_count'] = inventory_count
        context['items'] = inventory_count.items.all().order_by('-id')
        for item in context['items']:
            item.update_form = InventoryItemUpdateForm(initial={'quantity': item.actual_quantity})
        return context

    def form_valid(self, form):
        inventory_count = get_object_or_404(InventoryCount, pk=self.kwargs['pk'])
        if inventory_count.status != 'in_progress':
            messages.error(self.request, "Этот переучет завершен и не может быть изменен.")
            return redirect('count_work', pk=inventory_count.pk)
            
        identifier = form.cleaned_data['item_identifier']
        actual_quantity = form.cleaned_data['quantity']

        try:
            model_name, obj_id = identifier.split('-')
            
            target_model_class = None
            if model_name == 'product':
                target_model_class = Product
            elif model_name == 'material':
                target_model_class = Material
            elif model_name == 'package':
                package = get_object_or_404(Package, pk=obj_id)
                target_model_class = Product
                obj_id = package.product.id
            
            if not target_model_class:
                raise ValueError("Неизвестный тип объекта")

            content_object = get_object_or_404(target_model_class, pk=obj_id)
            
            system_quantity = 0
            if isinstance(content_object, Product):
                system_quantity = content_object.available_quantity
            elif isinstance(content_object, Material):
                system_quantity = content_object.quantity
            
            item, created = InventoryCountItem.objects.update_or_create(
                inventory_count=inventory_count,
                content_type=ContentType.objects.get_for_model(target_model_class),
                object_id=obj_id,
                defaults={
                    'system_quantity': system_quantity,
                    'actual_quantity': actual_quantity
                }
            )

            if created:
                messages.success(self.request, f"Позиция '{content_object.name}' добавлена.")
            else:
                messages.info(self.request, f"Количество для '{content_object.name}' обновлено.")
        except Exception as e:
            messages.error(self.request, f"Ошибка при добавлении позиции: {e}")
        
        return redirect('count_work', pk=inventory_count.pk)

class InventoryReconciliationView(LoginRequiredMixin, PermissionRequiredMixin, DetailView):
    """
    Представление для сверки завершенного переучета.
    """
    model = InventoryCount
    template_name = 'inventarization/count_reconcile.html'
    context_object_name = 'inventory_count'
    permission_required = 'inventarization.can_reconcile_inventory'

    def get_queryset(self):
        # Показываем только те, что ожидают сверки
        return InventoryCount.objects.filter(status=InventoryCount.Status.COMPLETED)

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        #передаем связанные items, вся логика будет в шаблоне
        context['items'] = self.get_object().items.all().select_related('content_type')
        return context


class ReconcileInventoryView(LoginRequiredMixin, PermissionRequiredMixin,View):
    """
    Обрабатывает POST-запрос на корректировку ОДНОЙ ПОЗИЦИИ.
    """
    permission_required = 'inventarization.can_reconcile_inventory'

    def post(self, request, pk, *args, **kwargs):
        # pk здесь - это pk для InventoryCount
        inventory_count = get_object_or_404(
            InventoryCount, pk=pk, status=InventoryCount.Status.COMPLETED
        )
        item_id = request.POST.get('item_id')
        item = get_object_or_404(inventory_count.items, pk=item_id)

        # Вызываем основную логику корректировки
        try:
            self._adjust_quantity(request.user, inventory_count, item)
            messages.success(
                request, 
                f"Системное количество для '{item.content_object.name}' успешно скорректировано."
            )
        except Exception as e:
            messages.error(request, f"Ошибка при обработке: {e}")
        
        return redirect('count_reconcile', pk=pk)

    def _adjust_quantity(self, user, inventory_count, item):
        """
        Главная функция: корректирует остаток и создает запись в журнале.
        """
        # Если расхождений нет или уже обработано, ничего не делаем
        if item.variance == 0 or item.reconciliation_status == 'reconciled':
            return

        with transaction.atomic():
            content_object = item.content_object
            variance = item.variance
            comment = f"Корректировка по переучету №{inventory_count.id}"

            # --- Логика для Готовой Продукции (Склад 2) ---
            if isinstance(content_object, Product):
                # Обновляем количество продукта
                content_object.total_quantity = item.actual_quantity
                content_object.save()
                
                # Создаем запись в журнале операций
                ProductOperation.objects.create(
                    product=content_object,
                    operation_type=ProductOperation.OperationType.ADJUSTMENT,
                    quantity=variance,
                    content_type=ContentType.objects.get_for_model(InventoryCount),
                    object_id=inventory_count.id,
                    user=user,
                    comment=comment
                )

            # --- Логика для Материалов (Склад 1) ---
            elif isinstance(content_object, Material):
                # Обновляем количество материала
                content_object.quantity = item.actual_quantity
                content_object.save()
                
                # Создаем запись в журнале операций с реальным variance (со знаком)
                MaterialOperation.objects.create(
                    material=content_object,
                    operation_type='adjustment',
                    quantity=variance,  # Для Decimal оставляем abs, но меняем комментарий
                    user=user,
                    comment=f"{comment}. Корректировка: {variance}"
                    # Если у MaterialOperation есть связь с переучетом, добавьте ее здесь
                    # inventory_count=inventory_count
                )
            
            # Отмечаем позицию как обработанную
            item.reconciliation_status = 'reconciled'
            item.save()


class FinalizeInventoryView(LoginRequiredMixin, PermissionRequiredMixin, View):
    """Окончательно закрывает переучет, меняя статус на RECONCILED."""
    permission_required = 'inventarization.can_reconcile_inventory'

    def post(self, request, pk, *args, **kwargs):
        inventory_count = get_object_or_404(
            InventoryCount, pk=pk, status=InventoryCount.Status.COMPLETED
        )
        
        # Проверяем, что все позиции с расхождениями обработаны
        pending_items = []
        for item in inventory_count.items.all():
            # Вычисляем расхождение для каждого элемента
            if item.actual_quantity != item.system_quantity and item.reconciliation_status == 'pending':
                pending_items.append(item)
        
        if pending_items:
            messages.error(request, "Не все позиции с расхождениями были обработаны.")
            return redirect('count_reconcile', pk=pk)

        inventory_count.status = InventoryCount.Status.RECONCILED
        inventory_count.save()
        
        messages.success(request, f"Переучет №{inventory_count.id} успешно закрыт.")
        return redirect('count_list')

@login_required
def update_inventory_item(request, pk):
    item = get_object_or_404(InventoryCountItem, pk=pk)
    if item.inventory_count.status != 'in_progress':
        messages.error(request, "Нельзя изменить завершенный переучет.")
        return redirect('count_work', pk=item.inventory_count.pk)

    if request.method == 'POST':
        form = InventoryItemUpdateForm(request.POST)
        if form.is_valid():
            item.actual_quantity = form.cleaned_data['quantity']
            item.save()
            messages.success(request, f"Количество для '{item.content_object.name}' обновлено.")
    return redirect('count_work', pk=item.inventory_count.pk)

@login_required
def delete_inventory_item(request, pk):
    item = get_object_or_404(InventoryCountItem, pk=pk)
    inventory_pk = item.inventory_count.pk
    if item.inventory_count.status != 'in_progress':
        messages.error(request, "Нельзя изменить завершенный переучет.")
        return redirect('count_work', pk=inventory_pk)

    if request.method == 'POST':
        item_name = str(item.content_object)
        item.delete()
        messages.warning(request, f"Позиция '{item_name}' удалена из переучета.")
        return redirect('count_work', pk=inventory_pk)
    
    return redirect('count_work', pk=inventory_pk)

@login_required
def complete_inventory_count(request, pk):
    if request.method == 'POST':
        # 1. Сначала находим переучет только по его номеру (pk)
        inventory_count = get_object_or_404(InventoryCount, pk=pk)

        # 2. Затем проверяем права доступа: это владелец ИЛИ администратор/менеджер?
        #    (is_staff обычно используется для доступа к админке)
        if inventory_count.user != request.user and not request.user.has_perm('inventarization.can_reconcile_inventory'):
            messages.error(request, "У вас нет прав...")
            return redirect('count_list')

        # 3. Основная логика остается без изменений
        if inventory_count.status == 'in_progress':
            inventory_count.status = InventoryCount.Status.COMPLETED
            inventory_count.completed_at = timezone.now()
            inventory_count.save()
            messages.success(request, f"Переучет №{inventory_count.id} завершен и готов к сверке.")
            return redirect('count_list')
        else:
            messages.error(request, "Этот переучет уже был завершен.")
            # Перенаправляем на страницу самого переучета, а не в список
            return redirect('count_work', pk=pk)
    
    # Если это GET-запрос, просто возвращаем пользователя на страницу переучета
    return redirect('count_work', pk=pk)

@login_required
def inventory_stock_search(request):
    query = request.GET.get('q', '').strip()
    inventory_count_id = request.GET.get('inventory_count_id')
    results = []

    counted_items = {}
    if inventory_count_id:
        items = InventoryCountItem.objects.filter(inventory_count_id=inventory_count_id)
        for item in items:
            item_key = f"{item.content_type.model}-{item.object_id}"
            counted_items[item_key] = item.actual_quantity

    if len(query) < 2:
        return JsonResponse({'results': results})

    # Сначала ищем продукты
    product_query = (
        Q(name__icontains=query) | Q(sku__icontains=query) |
        Q(barcode__exact=query) | Q(packages__barcode__exact=query)
    )
    products_found = Product.objects.filter(product_query).distinct()[:5]
    for p in products_found:
        item_key = f"product-{p.id}"
        results.append({
            'id': item_key,
            'name': f"{p.name}",
            'info': f"Посчитано: <strong>{counted_items.get(item_key, 0)} шт.</strong>",
            'counted_quantity': counted_items.get(item_key, 0)
        })

    # Затем ищем материалы
    material_query = (
        Q(name__icontains=query) | Q(article__icontains=query) | Q(barcode__exact=query)
    )
    materials_found = Material.objects.filter(material_query)[:5]
    for m in materials_found:
        item_key = f"material-{m.id}"
        results.append({
            'id': item_key,
            'name': f"{m.name}",
            'info': f"Посчитано: <strong>{counted_items.get(item_key, 0)} {m.unit.short_name}</strong>",
            'counted_quantity': counted_items.get(item_key, 0)
        })

    return JsonResponse({'results': results})