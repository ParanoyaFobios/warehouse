from django.shortcuts import redirect, get_object_or_404, render
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.urls import reverse_lazy
from .models import Product, WorkOrder, Shipment, ShipmentItem, Package, ProductCategory
from .forms import ProductForm, WorkOrderForm, ShipmentForm, ShipmentItemForm, PackageForm
from django.views.generic import ListView, CreateView, UpdateView, DeleteView, DetailView
from django.http import JsonResponse
from django.db import models
from django.views.generic.edit import FormView
from django.db.models import Sum, F
from django.views.generic.edit import FormMixin
from django.core.exceptions import ValidationError
from django.db.models import Q
from decimal import Decimal


# ==============================================================================
# Продукция
# ==============================================================================

class ProductListView(ListView):
    model = Product
    template_name = 'warehouse2/product_list.html'
    context_object_name = 'products'
    paginate_by = 5 #поменять

    def get_queryset(self):
        queryset = super().get_queryset()
        # Фильтр по категории
        category = self.request.GET.get('category')
        if category:
            queryset = queryset.filter(category_id=category)
        # Поиск по названию или артикулу
        search = self.request.GET.get('search')
        if search:
            queryset = queryset.filter(
                models.Q(name__icontains=search) | 
                models.Q(sku__icontains=search) |
                models.Q(barcode__icontains=search))
        
        return queryset

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['categories'] = ProductCategory.objects.all()
        return context

class ProductCreateView(CreateView):
    model = Product
    form_class = ProductForm
    template_name = 'warehouse2/product_form.html'
    success_url = reverse_lazy('product_list')

    def form_valid(self, form):
        messages.success(self.request, 'Продукт успешно создан')
        return super().form_valid(form)

class ProductUpdateView(UpdateView):
    model = Product
    form_class = ProductForm
    template_name = 'warehouse2/product_form.html'
    success_url = reverse_lazy('product_list')

    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        kwargs['user'] = self.request.user  # Передаем пользователя в форму
        return kwargs

    def form_valid(self, form):
        messages.success(self.request, 'Продукт успешно обновлен')
        return super().form_valid(form)

class ProductDetailView(FormMixin, DetailView):
    model = Product
    template_name = 'warehouse2/product_detail.html'
    context_object_name = 'product'
    form_class = PackageForm # Указываем форму для создания упаковки

    def get_success_url(self):
        # После успешного создания упаковки, перенаправляем на эту же страницу
        return reverse_lazy('product_detail', kwargs={'pk': self.object.pk})

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        # Передаем в шаблон список существующих упаковок для этого товара
        context['packages'] = self.object.packages.all().order_by('quantity')
        # Передаем форму для создания новой упаковки
        context['form'] = self.get_form()
        return context

    def post(self, request, *args, **kwargs):
        # Этот метод вызывается, когда пользователь отправляет форму
        self.object = self.get_object()
        form = self.get_form()
        if form.is_valid():
            return self.form_valid(form)
        else:
            return self.form_invalid(form)

    def form_valid(self, form):
        # Если форма валидна, создаем упаковку
        package = form.save(commit=False)
        package.product = self.object  # Привязываем упаковку к текущему товару
        package.save()
        messages.success(self.request, f'Упаковка на {package.quantity} шт. успешно создана!')
        return super().form_valid(form)

# ==============================================================================
# Упаковки - Package
# ==============================================================================

class PackageUpdateView(UpdateView):
    model = Package
    form_class = PackageForm
    template_name = 'warehouse2/package_form.html'

    def get_success_url(self):
        # После редактирования возвращаемся на страницу базового товара
        return reverse_lazy('product_detail', kwargs={'pk': self.object.product.pk})

    def form_valid(self, form):
        messages.success(self.request, 'Упаковка успешно обновлена')
        return super().form_valid(form)


class PackageDeleteView(DeleteView):
    model = Package
    template_name = 'warehouse2/package_confirm_delete.html' # И этот тоже создадим

    def get_success_url(self):
        # После удаления также возвращаемся на страницу товара
        return reverse_lazy('product_detail', kwargs={'pk': self.object.product.pk})
    
    def form_valid(self, form):
        messages.success(self.request, f'Упаковка "{self.object}" была удалена.')
        return super().form_valid(form)

# ==============================================================================
# Производственные заказы
# ==============================================================================

class WorkOrderListView(ListView):
    model = WorkOrder
    template_name = 'warehouse2/workorder_list.html'
    context_object_name = 'workorders'
    paginate_by = 5 #поменять
    ordering = ['-created_at']

class WorkOrderDetailView(DetailView):
    model = WorkOrder
    template_name = 'warehouse2/workorder_detail.html'
    context_object_name = 'workorder'

class WorkOrderCreateView(CreateView):
    model = WorkOrder
    form_class = WorkOrderForm
    template_name = 'warehouse2/workorder_form.html'
    success_url = reverse_lazy('workorder_list')

    def form_valid(self, form):
        messages.success(self.request, 'Производственный заказ создан')
        return super().form_valid(form)

class WorkOrderUpdateView(UpdateView):
    model = WorkOrder
    form_class = WorkOrderForm
    template_name = 'warehouse2/workorder_form.html'
    success_url = reverse_lazy('workorder_list')

    def form_valid(self, form):
        messages.success(self.request, 'Производственный заказ обновлен')
        return super().form_valid(form)

class WorkOrderDeleteView(DeleteView):
    model = WorkOrder
    template_name = 'warehouse2/workorder_confirm_delete.html'
    success_url = reverse_lazy('workorder_list')
    
    def delete(self, request, *args, **kwargs):
        messages.success(request, 'Производственный заказ удален')
        return super().delete(request, *args, **kwargs)

@login_required
def complete_workorder(request, pk):
    workorder = get_object_or_404(WorkOrder, pk=pk)
    if workorder.status != 'completed':
        if workorder.complete_order():
            messages.success(request, 'Заказ завершен и продукция добавлена на склад')
        else:
            messages.error(request, 'Ошибка при завершении заказа')
    else:
        messages.warning(request, 'Заказ уже был завершен ранее')
    return redirect('workorder_list')

# Функция для поиска продуктов (будет использоваться в AJAX)
@login_required
def product_search(request):
    query = request.GET.get('q', '')
    products = Product.objects.filter(
        models.Q(name__icontains=query) |
        models.Q(sku__icontains=query) |
        models.Q(barcode__icontains=query)
    )[:10]
    
    results = []
    for product in products:
        results.append({
            'id': product.id,
            'name': product.name,
            'sku': product.sku,
            'barcode': product.barcode,
            'category': str(product.category),
            'available_quantity': float(product.available_quantity)
        })
    
    return JsonResponse({'results': results})

# ==============================================================================
# Отгрузки
# ==============================================================================

class ShipmentListView(ListView):
    model = Shipment
    template_name = 'warehouse2/shipment_list.html'
    context_object_name = 'shipments'
    paginate_by = 5 #поменять
    ordering = ['-created_at']
    
    def get_queryset(self):
        # Аннотируем queryset для оптимизации
        return Shipment.objects.prefetch_related('items').all()

class ShipmentDetailView(DetailView):
    model = Shipment
    template_name = 'warehouse2/shipment_detail.html'
    context_object_name = 'shipment'
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        shipment = self.object
        context['items'] = shipment.items.all()
        context['can_edit'] = shipment.can_be_edited()
        context['can_ship'] = shipment.can_be_shipped()
        context['can_pack'] = shipment.can_be_packed()
        return context

class ShipmentCreateView(CreateView):
    model = Shipment
    form_class = ShipmentForm
    template_name = 'warehouse2/shipment_form.html'
    
    def form_valid(self, form):
        # Присваиваем текущего пользователя как создателя отгрузки
        form.instance.created_by = self.request.user
        messages.success(self.request, 'Отгрузка успешно создана. Теперь можно добавить товары.')
        return super().form_valid(form)

    def get_success_url(self):
        # После создания сразу переходим на страницу добавления товаров
        return reverse_lazy('shipment_items', kwargs={'pk': self.object.pk})


class ShipmentDeleteView(DeleteView):
    model = Shipment
    template_name = 'warehouse2/shipment_confirm_delete.html'
    success_url = reverse_lazy('shipment_list')
    
    def form_valid(self, form):
        messages.success(self.request, f'Отгрузка №{self.object.id} была удалена.')
        return super().form_valid(form)

@login_required
def ship_shipment(request, pk):
    shipment = get_object_or_404(Shipment, pk=pk)
    try:
        if shipment.can_be_shipped():
            shipment.ship(request.user)  # Передаем пользователя
            messages.success(request, 'Отгрузка успешно выполнена')
        else:
            messages.error(request, 'Невозможно отгрузить: нет товаров или уже отгружена')
    except ValidationError as e:
        messages.error(request, f'Ошибка при отгрузке: {str(e)}')
    except Exception as e:
        messages.error(request, f'Неожиданная ошибка: {str(e)}')
    
    return redirect('shipment_detail', pk=pk)  # Возвращаем на детальную страницу

# ==============================================================================
# Shipment Items Management
# ==============================================================================

class ShipmentItemsView(FormView):
    template_name = 'warehouse2/shipment_items.html'
    form_class = ShipmentItemForm
    
    def get_success_url(self):
        return reverse_lazy('shipment_items', kwargs={'pk': self.kwargs['pk']})
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        shipment = get_object_or_404(Shipment, pk=self.kwargs['pk'])
        context['shipment'] = shipment
        context['items'] = shipment.items.all().select_related('product', 'package', 'package__product')
        context['can_edit'] = shipment.can_be_edited()
        return context
    
    def form_valid(self, form):
        shipment = get_object_or_404(Shipment, pk=self.kwargs['pk'])
        
        if not shipment.can_be_edited():
            messages.error(self.request, 'Нельзя добавлять товары в отгруженную накладную')
            return self.form_invalid(form)
        
        identifier = form.cleaned_data['item_identifier']
        quantity = form.cleaned_data['quantity']
        
        try:
            item_type, item_id = identifier.split('-')
            item_id = int(item_id)
            
            new_item = ShipmentItem(shipment=shipment, quantity=quantity)
            
            if item_type == 'product':
                product = get_object_or_404(Product, pk=item_id)
                new_item.product = product
                new_item.price = product.price
            elif item_type == 'package':
                package = get_object_or_404(Package, pk=item_id)
                new_item.package = package
                new_item.price = package.price
            else:
                raise ValidationError('Неверный тип товара.')
            
            new_item.save()
            messages.success(self.request, f'Позиция добавлена в отгрузку')
            
        except (ValueError, ValidationError) as e:
            messages.error(self.request, f'Ошибка: {str(e)}')
            return self.form_invalid(form)
        
        return super().form_valid(form)

@login_required
def delete_shipment_item(request, pk):
    item = get_object_or_404(ShipmentItem, pk=pk)
    shipment_pk = item.shipment.pk
    item_name = str(item) # Запоминаем имя до удаления
    item.delete()
    messages.success(request, f'Позиция "{item_name}" удалена из отгрузки.')
    return redirect('shipment_items', pk=shipment_pk)

# ==============================================================================
# Product Search (только доступные товары)
# ==============================================================================

@login_required
def stock_search(request):
    query = request.GET.get('q', '').strip()
    results = []

    if len(query) < 2:
        return JsonResponse({'results': results})

    # --- Создаем Q-объекты для гибкого поиска ---
    # Для штучных товаров: ищем по названию, артикулу ИЛИ штрихкоду
    product_query = (
        Q(name__icontains=query) |
        Q(sku__icontains=query) |
        Q(barcode__icontains=query)
    )

    # Для упаковок: ищем по названию упаковки, штрихкоду упаковки,
    # ИЛИ по названию/артикулу связанного товара.
    package_query = (
        Q(name__icontains=query) |
        Q(barcode__icontains=query) |
        Q(product__name__icontains=query) |
        Q(product__sku__icontains=query)
    )

    # 1. Ищем штучные товары
    products = Product.objects.annotate(
        available=F('total_quantity') - F('reserved_quantity')
    ).filter(product_query, available__gt=0)[:5]

    for p in products:
        results.append({
            'id': f"product-{p.id}",
            'name': f"{p.name} (Штучный товар)",
            'info': f"Арт: {p.sku} | Доступно: {int(p.available_quantity)} шт.",
        })

    # 2. Ищем упаковки
    packages = Package.objects.select_related('product').filter(
        package_query,
        product__total_quantity__gt=F('product__reserved_quantity')
    )[:5]
    
    for pkg in packages:
        available_packages = int(pkg.product.available_quantity // pkg.quantity)
        if available_packages > 0:
            results.append({
                'id': f"package-{pkg.id}",
                'name': str(pkg),
                'info': f"Арт: {pkg.product.sku} | Можно собрать: {available_packages} уп.",
            })

    return JsonResponse({'results': results})

@login_required
def mark_shipment_as_packaged(request, pk):
    shipment = get_object_or_404(Shipment, pk=pk)
    if request.method == 'POST':
        if shipment.status == 'pending':
            shipment.status = 'packaged'
            shipment.processed_by = request.user # Фиксируем, кто собрал
            shipment.save()
            messages.success(request, f'Отгрузка №{shipment.id} отмечена как "Собрано".')
        else:
            messages.warning(request, 'Статус этой отгрузки уже был изменен.')
    return redirect('shipment_detail', pk=pk)