from django.shortcuts import render, redirect, get_object_or_404
from django.views import View
from django.views.generic import ListView, FormView
from django.urls import reverse_lazy, reverse
from django.contrib.auth.mixins import LoginRequiredMixin
from django.contrib import messages
from django.contrib.contenttypes.models import ContentType

from .models import InventoryCount, InventoryCountItem
from .forms import InventoryItemForm, InventoryItemUpdateForm

# Импортируем модели с наших складов
from warehouse1.models import Material
from warehouse2.models import Product, Package

class InventoryCountListView(LoginRequiredMixin, ListView):
    """Отображает список всех переучетов."""
    model = InventoryCount
    template_name = 'inventarization/count_list.html'
    context_object_name = 'inventory_counts'
    ordering = ['-created_at']

class StartInventoryCountView(LoginRequiredMixin, View):
    """Создает новый переучет для текущего пользователя."""
    def post(self, request, *args, **kwargs):
        # Проверяем, нет ли уже активного переучета у этого пользователя
        active_count = InventoryCount.objects.filter(user=request.user, status='in_progress').first()
        if active_count:
            messages.warning(request, "У вас уже есть незавершенный переучет. Вы были перенаправлены на него.")
            return redirect('count_work', pk=active_count.pk)
        
        # Создаем новый переучет
        new_count = InventoryCount.objects.create(user=request.user)
        messages.success(request, f"Начат новый переучет №{new_count.id}")
        return redirect('count_work', pk=new_count.pk)

class InventoryCountWorkView(LoginRequiredMixin, FormView):
    """Главная рабочая страница для проведения переучета."""
    template_name = 'inventarization/count_work.html'
    form_class = InventoryItemForm

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        inventory_count = get_object_or_404(InventoryCount, pk=self.kwargs['pk'])
        context['inventory_count'] = inventory_count
        context['items'] = inventory_count.items.all().order_by('-id')
        # Создаем для каждой позиции свою форму обновления
        for item in context['items']:
            item.update_form = InventoryItemUpdateForm(initial={'quantity': item.actual_quantity})
        return context

    def form_valid(self, form):
        inventory_count = get_object_or_404(InventoryCount, pk=self.kwargs['pk'])
        identifier = form.cleaned_data['item_identifier']
        actual_quantity = form.cleaned_data['quantity']

        try:
            # Разбираем идентификатор, чтобы понять, с какой моделью работаем
            model_name, obj_id = identifier.split('-')
            
            # Находим сам объект (Material, Product или Package)
            if model_name == 'product':
                model = Product
            elif model_name == 'material':
                model = Material
            else: # Добавим логику для упаковок
                # Для упаковки мы всегда работаем с ее родительским товаром
                package = get_object_or_404(Package, pk=obj_id)
                model = Product
                obj_id = package.product.id

            content_object = get_object_or_404(model, pk=obj_id)
            
            # "Фотографируем" системное количество
            system_quantity = 0
            if isinstance(content_object, Product):
                system_quantity = content_object.available_quantity
            elif isinstance(content_object, Material):
                system_quantity = content_object.quantity
            
            # Используем update_or_create для атомарного создания/обновления
            item, created = InventoryCountItem.objects.update_or_create(
                inventory_count=inventory_count,
                content_type=ContentType.objects.get_for_model(model),
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

        except (ValueError, AttributeError) as e:
            messages.error(self.request, f"Ошибка при добавлении позиции: {e}")
        
        return redirect('count_work', pk=inventory_count.pk)

def update_inventory_item(request, pk):
    """Обновляет количество для уже существующей позиции."""
    item = get_object_or_404(InventoryCountItem, pk=pk)
    if request.method == 'POST':
        form = InventoryItemUpdateForm(request.POST)
        if form.is_valid():
            item.actual_quantity = form.cleaned_data['quantity']
            item.save()
            messages.success(request, f"Количество для '{item.content_object.name}' обновлено.")
    return redirect('count_work', pk=item.inventory_count.pk)


def delete_inventory_item(request, pk):
    """Удаляет позицию из переучета."""
    item = get_object_or_404(InventoryCountItem, pk=pk)
    if request.method == 'POST':
        item_name = item.content_object.name
        inventory_pk = item.inventory_count.pk
        item.delete()
        messages.warning(request, f"Позиция '{item_name}' удалена из переучета.")
        return redirect('inventarization:count_work', pk=inventory_pk)
    # GET-запрос просто перенаправляем
    return redirect('inventarization:count_work', pk=item.inventory_count.pk)