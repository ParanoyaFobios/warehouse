from django.shortcuts import redirect, get_object_or_404
from django.views.generic import ListView, FormView
from django.contrib.auth.mixins import LoginRequiredMixin, PermissionRequiredMixin
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.contrib.contenttypes.models import ContentType
from django.http import JsonResponse
from django.db.models import Q, F, Case, When, Value, IntegerField
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
    paginate_by = 20

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
        # Оптимизируем запрос: тянем тип контента сразу
        inventory_count = get_object_or_404(
            InventoryCount.objects.prefetch_related('items__content_type'), 
            pk=self.kwargs['pk']
        )
        
        # Сортировка: сначала те, что требуют пересчета, потом остальные
        items = inventory_count.items.all().annotate(
            recount_priority=Case(
                When(reconciliation_status=InventoryCountItem.ReconciliationStatus.RECOUNT, then=Value(0)),
                default=Value(1),
                output_field=IntegerField(),
            )
        ).order_by('recount_priority', '-id')

        # Чтобы не создавать формы в цикле в шаблоне (это тяжело), 
        # подготовим их один раз или будем использовать один инпут
        for item in items:
            item.update_form = InventoryItemUpdateForm(initial={'quantity': item.actual_quantity})

        context['inventory_count'] = inventory_count
        context['items'] = items
        return context

    def form_valid(self, form):
        inventory_count = get_object_or_404(InventoryCount, pk=self.kwargs['pk'])
        
        # Разрешаем правки и в процессе, и в режиме "исправления"
        allowed_statuses = [InventoryCount.Status.IN_PROGRESS, InventoryCount.Status.FIXING]
        if inventory_count.status not in allowed_statuses:
            messages.error(self.request, "Этот переучет нельзя редактировать в текущем статусе.")
            return redirect('count_work', pk=inventory_count.pk)
            
        identifier = form.cleaned_data['item_identifier']
        actual_quantity = form.cleaned_data['quantity']

        # Избавляемся от "ёлочки" через словарь (Strategy-like pattern)
        model_map = {
            'product': Product,
            'material': Material,
            'package': Package,
        }

        try:
            prefix, obj_id = identifier.split('-')
            model_class = model_map.get(prefix)
            
            if not model_class:
                raise ValueError(f"Неизвестный тип: {prefix}")

            target_obj = get_object_or_404(model_class, pk=obj_id)
            
            # Если это упаковка, работаем с привязанным товаром
            if prefix == 'package':
                target_obj = target_obj.product
                model_class = Product
                obj_id = target_obj.id

            # Логика получения системного остатка
            sys_qty = getattr(target_obj, 'available_quantity', getattr(target_obj, 'quantity', 0))

            item, created = InventoryCountItem.objects.update_or_create(
                inventory_count=inventory_count,
                content_type=ContentType.objects.get_for_model(model_class),
                object_id=obj_id,
                defaults={
                    'system_quantity': sys_qty,
                    'actual_quantity': actual_quantity,
                    # ВАЖНО: Если кладовщик пересчитал, сбрасываем статус "RECOUNT" на "PENDING"
                    'reconciliation_status': InventoryCountItem.ReconciliationStatus.PENDING
                }
            )

            msg = f"Позиция '{target_obj.name}' добавлена." if created else f"Обновлено: {target_obj.name}"
            messages.success(self.request, msg)

        except Exception as e:
            messages.error(self.request, f"Ошибка: {e}")
        
        return redirect('count_work', pk=inventory_count.pk)

class InventoryReconciliationView(LoginRequiredMixin, PermissionRequiredMixin, DetailView):
    """
    Представление для сверки завершенного переучета.
    """
    model = InventoryCount
    template_name = 'inventarization/count_reconcile.html'
    context_object_name = 'inventory_count'
    permission_required = 'inventarization.can_reconcile_inventory'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        # Оптимизируем запрос
        items = self.object.items.select_related('content_type').all()
        
        # Считаем статистику для дашборда сверху
        context['total_items'] = items.count()
        context['discrepancy_count'] = sum(1 for item in items if item.variance != 0)
        context['items'] = items
        return context


class InventoryAjaxActions(LoginRequiredMixin, PermissionRequiredMixin, View):
    permission_required = 'inventarization.can_reconcile_inventory'

    def post(self, request, pk):
        action = request.POST.get('action')
        item_id = request.POST.get('item_id')
        inventory_count = get_object_or_404(InventoryCount, pk=pk)

        # Проверяем, что переучет в нужном статусе
        if inventory_count.status != InventoryCount.Status.COMPLETED:
            return JsonResponse({'status': 'error', 'message': 'Статус не позволяет правки'}, status=400)

        if action == 'reconcile_single':
            item = get_object_or_404(inventory_count.items, pk=item_id)
            
            # 1. Если бухгалтер изменил цифру в инпуте, сохраняем её
            new_actual = request.POST.get('actual_quantity')
            if new_actual is not None:
                item.actual_quantity = int(new_actual)
                item.save()

            # 2. Применяем твою логику корректировки остатков
            try:
                self._adjust_stock_logic(request.user, inventory_count, item)
                return JsonResponse({'status': 'success'})
            except Exception as e:
                return JsonResponse({'status': 'error', 'message': str(e)}, status=500)

        elif action == 'bulk_approve_zeros':
            # Массово закрываем то, где расхождений нет
            inventory_count.items.filter(
                system_quantity=F('actual_quantity'),
                reconciliation_status=InventoryCountItem.ReconciliationStatus.PENDING
            ).update(reconciliation_status=InventoryCountItem.ReconciliationStatus.RECONCILED)
            return JsonResponse({'status': 'success'})
        
        elif action == 'mark_recount':
            item = get_object_or_404(inventory_count.items, pk=item_id)
            item.reconciliation_status = InventoryCountItem.ReconciliationStatus.RECOUNT
            # Сохраняем причину, которую ввел бухгалтер в prompt()
            item.manager_comment = request.POST.get('comment', '')
            item.save()
            return JsonResponse({'status': 'success'})

        return JsonResponse({'status': 'error', 'message': 'Неизвестное действие'}, status=400)

    def _adjust_stock_logic(self, user, inventory_count, item):
        """ Твоя оригинальная логика корректировки из вопроса """
        with transaction.atomic():
            model_class = item.content_type.model_class()
            content_object = model_class.objects.select_for_update().get(pk=item.object_id)
            
            variance = item.variance
            comment = f"Корректировка по переучету №{inventory_count.id}"

            if isinstance(content_object, Product):
                content_object.total_quantity = item.actual_quantity
                content_object.save(update_fields=['total_quantity'])
                ProductOperation.objects.create(
                    product=content_object,
                    operation_type=ProductOperation.OperationType.ADJUSTMENT,
                    quantity=variance,
                    content_type=item.content_type,
                    object_id=inventory_count.id,
                    user=user,
                    comment=comment
                )
            elif isinstance(content_object, Material):
                content_object.quantity = item.actual_quantity
                content_object.save(update_fields=['quantity'])
                MaterialOperation.objects.create(
                    material=content_object,
                    operation_type='adjustment',
                    quantity=variance,
                    user=user,
                    comment=f"{comment}. Корректировка: {variance}"
                )
            
            item.reconciliation_status = InventoryCountItem.ReconciliationStatus.RECONCILED
            item.save(update_fields=['reconciliation_status'])


class SendToFixingView(LoginRequiredMixin, PermissionRequiredMixin, View):
    permission_required = 'inventarization.can_reconcile_inventory'

    def post(self, request, pk):
        inventory_count = get_object_or_404(InventoryCount, pk=pk, status=InventoryCount.Status.COMPLETED)
        
        # Проверяем, пометил ли бухгалтер хоть что-то на пересчет
        recount_exists = inventory_count.items.filter(
            reconciliation_status=InventoryCountItem.ReconciliationStatus.RECOUNT
        ).exists()

        if not recount_exists:
            messages.error(request, "Сначала пометьте позиции, которые нужно пересчитать.")
            return redirect('count_reconcile', pk=pk)

        inventory_count.status = InventoryCount.Status.FIXING
        inventory_count.save()
        
        messages.warning(request, f"Переучет №{inventory_count.id} отправлен кладовщику на доработку.")
        return redirect('count_list')


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
@transaction.atomic  # Обязательно для работы select_for_update
def update_inventory_item(request, pk):
    # Используем select_for_update, чтобы заблокировать строку в БД до конца транзакции
    item = get_object_or_404(
        InventoryCountItem.objects.select_for_update(), 
        pk=pk
    )
    inventory = item.inventory_count
    
    # Твоя логика доступа (оставляем как есть)
    can_edit = (inventory.status == InventoryCount.Status.IN_PROGRESS) or \
               (inventory.status == InventoryCount.Status.FIXING and 
                item.reconciliation_status == InventoryCountItem.ReconciliationStatus.RECOUNT)

    if not can_edit:
        messages.error(request, "Эту позицию сейчас нельзя редактировать.")
        return redirect('count_work', pk=inventory.pk)

    if request.method == 'POST':
        form = InventoryItemUpdateForm(request.POST)
        if form.is_valid():
            # Обновляем количество
            item.actual_quantity = form.cleaned_data['quantity']
            
            # Сбрасываем статус, чтобы бухгалтер видел исправление
            # Важно: если мы в режиме IN_PROGRESS, статус может быть и так PENDING
            item.reconciliation_status = InventoryCountItem.ReconciliationStatus.PENDING
            
            item.save()
            messages.success(request, f"Количество для '{item.content_object.name}' обновлено.")
    
    return redirect('count_work', pk=inventory.pk)

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
        inventory_count = get_object_or_404(InventoryCount, pk=pk)

        # Проверка прав (как у тебя была)
        if inventory_count.user != request.user and not request.user.has_perm('inventarization.can_reconcile_inventory'):
            messages.error(request, "У вас нет прав...")
            return redirect('count_list')

        # Разрешаем завершать и обычный переучет, и исправление
        if inventory_count.status in [InventoryCount.Status.IN_PROGRESS, InventoryCount.Status.FIXING]:
            inventory_count.status = InventoryCount.Status.COMPLETED
            inventory_count.completed_at = timezone.now()
            inventory_count.save()
            messages.success(request, f"Переучет №{inventory_count.id} отправлен на сверку.")
            return redirect('count_list')
        else:
            messages.error(request, "Этот переучет нельзя завершить в текущем статусе.")
            return redirect('count_work', pk=pk)
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