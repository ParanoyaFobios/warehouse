from django.shortcuts import redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.urls import reverse_lazy
from .models import Product, WorkOrder, Shipment
from .forms import ProductForm, WorkOrderForm
from django.views.generic import ListView, CreateView, UpdateView, DeleteView, DetailView
from django.http import JsonResponse
from django.db import models

# ==============================================================================
# Продукция
# ==============================================================================

class ProductListView(ListView):
    model = Product
    template_name = 'warehouse2/product_list.html'
    context_object_name = 'products'
    paginate_by = 20

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

    def form_valid(self, form):
        messages.success(self.request, 'Продукт успешно обновлен')
        return super().form_valid(form)

class ProductDetailView(DetailView):
    model = Product
    template_name = 'warehouse2/product_detail.html'
    context_object_name = 'product'

# ==============================================================================
# Производственные заказы
# ==============================================================================

class WorkOrderListView(ListView):
    model = WorkOrder
    template_name = 'warehouse2/workorder_list.html'
    context_object_name = 'workorders'
    paginate_by = 20
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
    paginate_by = 20

@login_required
def ship_shipment(request, pk):
    shipment = get_object_or_404(Shipment, pk=pk)
    try:
        shipment.ship()
        messages.success(request, 'Отгрузка успешно выполнена')
    except Exception as e:
        messages.error(request, f'Ошибка при отгрузке: {str(e)}')
    return redirect('shipment_list')