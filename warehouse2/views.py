from django.shortcuts import redirect, get_object_or_404, render
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.urls import reverse_lazy
from .models import Product, WorkOrder, Shipment, ShipmentItem, ShipmentDocument
from .forms import ProductForm, WorkOrderForm, ShipmentForm, ShipmentItemForm, ShipmentDocumentForm
from django.views.generic import ListView, CreateView, UpdateView, DeleteView, DetailView
from django.http import JsonResponse
from django.db import models
from django.views.generic.edit import FormView
from django.forms import inlineformset_factory
from django.db.models import F
from django.db.models import Sum, Q


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
    ordering = ['-created_at']

class ShipmentDetailView(DetailView):
    model = Shipment
    template_name = 'warehouse2/shipment_detail.html'
    context_object_name = 'shipment'
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['items'] = self.object.shipmentitem_set.all()
        return context

class ShipmentCreateView(CreateView):
    model = Shipment
    form_class = ShipmentForm
    template_name = 'warehouse2/shipment_form.html'
    success_url = reverse_lazy('shipment_list')
    
    def form_valid(self, form):
        messages.success(self.request, 'Отгрузка создана')
        return super().form_valid(form)

class ShipmentUpdateView(UpdateView):
    model = Shipment
    form_class = ShipmentForm
    template_name = 'warehouse2/shipment_form.html'
    success_url = reverse_lazy('shipment_list')
    
    def form_valid(self, form):
        messages.success(self.request, 'Отгрузка обновлена')
        return super().form_valid(form)

class ShipmentDeleteView(DeleteView):
    model = Shipment
    template_name = 'warehouse2/shipment_confirm_delete.html'
    success_url = reverse_lazy('shipment_list')
    
    def delete(self, request, *args, **kwargs):
        messages.success(request, 'Отгрузка удалена')
        return super().delete(request, *args, **kwargs)

@login_required
def ship_shipment(request, pk):
    shipment = get_object_or_404(Shipment, pk=pk)
    try:
        if shipment.can_be_shipped():
            shipment.ship()
            messages.success(request, 'Отгрузка успешно выполнена')
        else:
            messages.error(request, 'Невозможно отгрузить: нет товаров или уже отгружена')
    except Exception as e:
        messages.error(request, f'Ошибка при отгрузке: {str(e)}')
    return redirect('shipment_list')

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
        context['items'] = shipment.shipmentitem_set.all()
        context['can_edit'] = shipment.can_be_edited()
        return context
    
    def form_valid(self, form):
        shipment = get_object_or_404(Shipment, pk=self.kwargs['pk'])
        if not shipment.can_be_edited():
            messages.error(self.request, 'Невозможно изменить отгруженную отгрузку')
            return redirect('shipment_list')
        
        try:
            item = form.save(commit=False)
            item.shipment = shipment
            item.save()
            messages.success(self.request, 'Товар добавлен в отгрузку')
        except Exception as e:
            messages.error(self.request, f'Ошибка: {str(e)}')
        
        return super().form_valid(form)

@login_required
def delete_shipment_item(request, pk):
    item = get_object_or_404(ShipmentItem, pk=pk)
    shipment = item.shipment
    
    if not shipment.can_be_edited():
        messages.error(request, 'Невозможно изменить отгруженную отгрузку')
        return redirect('shipment_list')
    
    item.delete()
    messages.success(request, 'Товар удален из отгрузки')
    return redirect('shipment_items', pk=shipment.pk)

# ==============================================================================
# Product Search (только доступные товары)
# ==============================================================================

@login_required
def available_product_search(request):
    query = request.GET.get('q', '')
    
    # Ищем товары, у которых (total_quantity - reserved_quantity) > 0
    products = Product.objects.annotate(
        available=F('total_quantity') - F('reserved_quantity')
    ).filter(
        available__gt=0,
        name__icontains=query
    )[:10]
    
    results = []
    for product in products:
        results.append({
            'id': product.id,
            'name': f"{product.name} ({product.sku})", # Добавим артикул для наглядности
            'available_quantity': float(product.available_quantity),
        })
    
    return JsonResponse({'results': results})


# ==============================================================================
# Shipment Document (Накладные)
# ==============================================================================

class ShipmentDocumentListView(ListView):
    model = ShipmentDocument
    template_name = 'warehouse2/shipment_document_list.html'
    context_object_name = 'documents'
    ordering = ['-created_at']

class ShipmentDocumentCreateView(CreateView):
    model = ShipmentDocument
    form_class = ShipmentDocumentForm
    template_name = 'warehouse2/shipment_document_form.html'
    
    def get_success_url(self):
        # После создания накладной, переходим на страницу управления ею
        return reverse_lazy('shipment_document_manage', kwargs={'pk': self.object.pk})

class ShipmentDocumentDetailView(DetailView):
    model = ShipmentDocument
    template_name = 'warehouse2/shipment_document_detail.html'
    context_object_name = 'document'

# Управление накладной: добавление отгрузок по штрихкоду
@login_required
def manage_shipment_document(request, pk):
    document = get_object_or_404(ShipmentDocument, pk=pk)
    
    if request.method == 'POST':
        shipment_barcode = request.POST.get('shipment_barcode')
        shipment_id = request.POST.get('shipment_id')
        
        # Строим запрос, который найдет отгрузку или по штрихкоду, или по ID
        query = Q()
        if shipment_barcode:
            query |= Q(barcode=shipment_barcode)
        elif shipment_id:
            query |= Q(pk=shipment_id)
        
        if query:
            try:
                shipment_to_add = Shipment.objects.get(query)
                
                # Проверяем, что отгрузка готова и еще не в другой накладной
                if shipment_to_add.status == 'pending' and shipment_to_add.document is None:
                    shipment_to_add.document = document
                    shipment_to_add.status = 'assigned'
                    shipment_to_add.save()
                    messages.success(request, f"Отгрузка №{shipment_to_add.id} добавлена в накладную.")
                else:
                    messages.error(request, "Эта отгрузка уже в другой накладной или еще не собрана.")
            
            except Shipment.DoesNotExist:
                messages.error(request, "Отгрузка с таким штрихкодом или ID не найдена.")
            except Shipment.MultipleObjectsReturned:
                messages.error(request, "Найдено несколько отгрузок, уточните запрос.")
        else:
            messages.error(request, "Не указан ID или штрихкод отгрузки.")
            
        return redirect('shipment_document_manage', pk=pk)
            
    # Аннотируем queryset, чтобы посчитать общее кол-во товаров в каждой отгрузке
    available_shipments = Shipment.objects.filter(
        status='pending', 
        document__isnull=True
    ).annotate(
        total_items=Sum('shipmentitem__quantity')
    )
    
    context = {
        'document': document,
        'available_shipments': available_shipments
    }
    return render(request, 'warehouse2/shipment_document_manage.html', context)