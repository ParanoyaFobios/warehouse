from django.shortcuts import redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.urls import reverse_lazy
from .models import Product, Shipment, ShipmentItem, Package, ProductCategory, ProductOperation
from reports.models import ShipmentAuditLog
from .forms import ProductForm, ShipmentForm, ShipmentItemForm, PackageForm, ProductIncomingForm
from django.views.generic import ListView, CreateView, UpdateView, DeleteView, DetailView, View
from django.http import JsonResponse, HttpResponse
from django.db import models
from django.views.generic.edit import FormView, FormMixin
from django.db.models import F, Q
from django.core.exceptions import ValidationError
from django.contrib.auth.mixins import LoginRequiredMixin
from django.db import transaction
from django.conf import settings
from django.template.loader import render_to_string
from weasyprint import HTML
import tempfile

# ==============================================================================
# Продукция
# ==============================================================================

class ProductListView(ListView):
    model = Product
    template_name = 'warehouse2/product_list.html'
    context_object_name = 'products'
    paginate_by = 20 #поменять

    def get_queryset(self):
            queryset = super().get_queryset().order_by('name') # Хорошая практика: всегда сортировать при пагинации
            show_archived = self.request.GET.get('archived') == '1'
            category = self.request.GET.get('category')
            search = self.request.GET.get('search')
            if category:
                queryset = queryset.filter(category_id=category)
                
            search = self.request.GET.get('search')
            if search:
                product_query = (
                    models.Q(name__icontains=search) | 
                    models.Q(sku__icontains=search) |
                    models.Q(barcode__exact=search) |
                    models.Q(packages__barcode__exact=search)
                )
                queryset = queryset.filter(product_query).distinct()
            else:
        # Если поиска НЕТ — разделяем активные и архивные по флагу
                queryset = queryset.filter(is_archived=show_archived)
            
            return queryset

    def get_context_data(self, **kwargs):
            context = super().get_context_data(**kwargs)
            context['categories'] = ProductCategory.objects.all()
            # Сохраняем значения фильтров для использования в ссылках пагинации
            context['current_category'] = self.request.GET.get('category', '')
            context['current_search'] = self.request.GET.get('search', '')
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
    
class ProductArchiveView(LoginRequiredMixin, View):
    def post(self, request, pk):
        product = get_object_or_404(Product, pk=pk)
        product.is_archived = not product.is_archived  # Переключает туда-обратно
        product.save()
        
        if product.is_archived:
            messages.success(request, f'Товар "{product.name}" архивирован.')
        else:
            messages.success(request, f'Товар "{product.name}" восстановлен из архива.')
            
        return redirect('product_list')

class ProductIncomingView(LoginRequiredMixin, FormView):
    template_name = 'warehouse2/product_incoming_form.html'
    form_class = ProductIncomingForm
    success_url = reverse_lazy('product_list')

    def form_valid(self, form):
        product_id = form.cleaned_data['product']
        quantity = form.cleaned_data['quantity']
        comment = form.cleaned_data['comment']
        product = get_object_or_404(Product, pk=product_id)

        try:
            with transaction.atomic():
                # Нам нужно получить ContentType для модели Product, 
                # так как source требует хоть какую-то привязку
                from django.contrib.contenttypes.models import ContentType
                product_ct = ContentType.objects.get_for_model(product)

                ProductOperation.objects.create(
                    product=product,  # К какому товару относится (ForeignKey)
                    operation_type=ProductOperation.OperationType.INCOMING,
                    quantity=quantity,
                    # Заполняем GenericForeignKey (source), чтобы не было ошибки NOT NULL
                    content_type=product_ct,
                    object_id=product.id, 
                    user=self.request.user,
                    comment=comment
                )

                # Обновляем остаток
                product.total_quantity += quantity
                product.save(update_fields=['total_quantity'])
                
            messages.success(self.request, f"Товар '{product.name}' успешно оприходован.")
        except Exception as e:
            print(f"DEBUG ERROR: {e}")
            messages.error(self.request, f"Ошибка: {e}")

        return redirect(self.get_success_url())
    
def product_search_json(request):
    query = request.GET.get('q', '').strip()
    results = []
    if len(query) >= 2:
        products = Product.objects.filter(
            Q(name__icontains=query) |
            Q(sku__icontains=query) |
            Q(barcode__exact=query)
        ).distinct()[:10]

        for product in products:
            results.append({
                'id': product.id,
                'name': str(product),
                'sku': product.sku,
                'barcode': product.barcode,
                'category': str(product.category),
                'available_quantity': product.available_quantity
            })
    return JsonResponse({'results': results})

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
# Отгрузки
# ==============================================================================

class ShipmentListView(ListView):
    model = Shipment
    template_name = 'warehouse2/shipment_list.html'
    context_object_name = 'shipments'
    paginate_by = 20
    ordering = ['-created_at']
    
    def get_queryset(self):
        # Аннотируем queryset для оптимизации
        queryset = Shipment.objects.prefetch_related('items').all().order_by('-created_at')
                # Получаем параметры фильтрации
        created_at = self.request.GET.get('created_at')
        order_id = self.request.GET.get('order_id')

        if created_at:
            # Ищем записи за конкретный день, игнорируя время
            queryset = queryset.filter(created_at__date=created_at)
        
        if order_id and order_id.isdigit():
            queryset = queryset.filter(id=order_id)

        return queryset

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        # Передаем текущие фильтры обратно в контекст, чтобы форма их "помнила"
        context['filter_created_at'] = self.request.GET.get('created_at', '')
        context['filter_order_id'] = self.request.GET.get('order_id', '')
        return context

class ShipmentDetailView(DetailView):
    model = Shipment
    template_name = 'warehouse2/shipment_detail.html'
    context_object_name = 'shipment'
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        shipment = self.object
        context['items'] = self.object.items.all().select_related(
            'product',  # Загружаем связанный продукт
            'package',  # Загружаем связанную упаковку
            'package__product'  # Загружаем продукт внутри упаковки
            )
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

    def dispatch(self, request, *args, **kwargs):
        """
        Проверяем права на удаление до того, как что-либо будет сделано.
        """
        shipment = self.get_object()
        if not shipment.can_be_deleted():
            messages.error(request, "Нельзя удалить отгруженную или возвращенную накладную.")
            return redirect('shipment_detail', pk=shipment.pk)
        return super().dispatch(request, *args, **kwargs)
    
    def form_valid(self, form):
        # Используем transaction.atomic для безопасности:
        # либо все удалится, либо ничего
        with transaction.atomic():
            # self.object - это отгрузка, которую мы собираемся удалить
            shipment_to_delete = self.get_object()
            # Перед удалением самой отгрузки, проходим по всем ее позициям
            # и удаляем их по одной. При этом у каждой сработает ее собственный
            # метод .delete(), который снимает товар с резерва.
            for item in shipment_to_delete.items.all():
                item.delete()
            # Теперь, когда все резервы сняты, можно безопасно
            # вызывать стандартный метод удаления для самой отгрузки.
            response = super().form_valid(form)

        messages.success(self.request, f'Отгрузка была удалена, товары возвращены из резерва.')
        return response

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

class ShipmentItemsView(LoginRequiredMixin, FormView):
    template_name = 'warehouse2/shipment_items.html'
    form_class = ShipmentItemForm

    def dispatch(self, request, *args, **kwargs):
        """Гарантируем, что никто не зайдет по ссылке, если отгрузка закрыта."""
        shipment = get_object_or_404(Shipment, pk=self.kwargs['pk'])
        
        if not shipment.can_be_edited():
            messages.error(request, "Редактирование состава невозможно: накладная уже отгружена или возвращена.")
            return redirect('shipment_detail', pk=shipment.pk)
            
        return super().dispatch(request, *args, **kwargs)
    
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
            # Получаем цену из формы (может быть None)
            custom_price = form.cleaned_data.get('price_override')
            
            try:
                item_type, item_id = identifier.split('-')
                item_id = int(item_id)
                
                # 1. СНАЧАЛА находим сам объект товара/упаковки, а также определяем цену
                product_obj = None
                package_obj = None
                target_price = None

                if item_type == 'product':
                    product_obj = get_object_or_404(Product, pk=item_id)
                    # Если ввели вручную - берем её, если нет - берем из товара
                    target_price = custom_price if custom_price is not None else product_obj.price
                
                elif item_type == 'package':
                    package_obj = get_object_or_404(Package, pk=item_id)
                    target_price = custom_price if custom_price is not None else package_obj.price
                
                else:
                    raise ValidationError('Неверный тип идентификатора.')

                # 2. ИЩЕМ существующую позицию, совпадающую ПО ТОВАРУ И ПО ЦЕНЕ
                existing_item = None
                
                if item_type == 'product':
                    existing_item = ShipmentItem.objects.filter(
                        shipment=shipment, 
                        product=product_obj, 
                        package__isnull=True,
                        price=target_price  # <--- ГЛАВНОЕ ИЗМЕНЕНИЕ: ищем по конкретной цене
                    ).first()
                elif item_type == 'package':
                    existing_item = ShipmentItem.objects.filter(
                        shipment=shipment, 
                        package=package_obj, 
                        product__isnull=True,
                        price=target_price  # <--- ГЛАВНОЕ ИЗМЕНЕНИЕ
                    ).first()

                if existing_item:
                    # === СЦЕНАРИЙ 1: Товар с такой же ценой уже есть ===
                    # Просто увеличиваем количество
                    old_quantity = existing_item.quantity
                    existing_item.quantity += quantity
                    existing_item.save()
                    
                    messages.success(
                        self.request, 
                        f'Добавлено к существующей позиции ({target_price} грн). Было: {old_quantity}, Стало: {existing_item.quantity}'
                    )
                else:
                    # === СЦЕНАРИЙ 2: Товара нет ИЛИ цена отличается ===
                    # Создаем новую строчку
                    new_item = ShipmentItem(
                        shipment=shipment, 
                        quantity=quantity,
                        price=target_price # Явно записываем вычисленную цену
                    )
                    
                    if item_type == 'product':
                        new_item.product = product_obj
                    elif item_type == 'package':
                        new_item.package = package_obj
                    
                    new_item.save()
                    messages.success(self.request, f'Добавлена новая позиция: {quantity} шт. по цене {target_price} грн.')

            except (ValueError, ValidationError) as e:
                messages.error(self.request, f'Ошибка: {str(e)}')
                return self.form_invalid(form)
            
            return super().form_valid(form)
    
class ShipmentUpdateView(LoginRequiredMixin, UpdateView):
    """
    Редактирование шапки отгрузки (Отправитель, Адрес, Получатель).
    Доступно только если отгрузка еще не уехала.
    """
    model = Shipment
    form_class = ShipmentForm
    template_name = 'warehouse2/shipment_form.html'
    
    def dispatch(self, request, *args, **kwargs):
        """Проверка прав на редактирование перед открытием страницы."""
        obj = self.get_object()
        
        # Используем метод модели can_be_edited (pending или packaged)
        if not obj.can_be_edited():
            messages.error(request, "Нельзя редактировать уже отгруженную или возвращенную накладную.")
            return redirect('shipment_detail', pk=obj.pk)
            
        return super().dispatch(request, *args, **kwargs)

    def form_valid(self, form):
        messages.success(self.request, 'Данные накладной успешно обновлены.')
        return super().form_valid(form)

    def get_success_url(self):
        # Возвращаемся обратно в детали отгрузки
        return reverse_lazy('shipment_detail', kwargs={'pk': self.object.pk})

class ReturnShipmentView(LoginRequiredMixin, DetailView):
    model = Shipment
    template_name = 'warehouse2/shipment_confirm_return.html'
    context_object_name = 'shipment'

    def post(self, request, *args, **kwargs):
        shipment = self.get_object()

        if shipment.status != 'shipped':
            messages.error(request, "Возврат можно оформить только для отгруженных накладных.")
            return redirect('shipment_detail', pk=shipment.pk)

        try:
            with transaction.atomic():
                for item in shipment.items.all():
                    product_to_return = item.stock_product
                    quantity_to_return = item.base_product_units

                    # Возвращаем количество на склад
                    product_to_return.total_quantity += quantity_to_return
                    
                    # 1. ИСПРАВЛЕНИЕ: Используем update_fields
                    product_to_return.save(update_fields=['total_quantity'])

                    # 2. Создаем операцию
                    ProductOperation.objects.create(
                        product=product_to_return,
                        operation_type=ProductOperation.OperationType.RETURN,
                        quantity=quantity_to_return,
                        source=shipment,
                        user=request.user,
                        comment=f"Возврат по отгрузке №{shipment.id}"
                    )
                
                shipment.status = 'returned'
                shipment.save()
                messages.success(request, f"Товары по отгрузке №{shipment.id} успешно возвращены на склад.")
        except Exception as e:
            messages.error(request, f"Произошла ошибка при оформлении возврата: {e}")
            return redirect('shipment_detail', pk=shipment.pk)

        return redirect('shipment_list')

@login_required
def delete_shipment_item(request, pk):
    item = get_object_or_404(ShipmentItem, pk=pk)
    shipment_pk = item.shipment.pk
    item_name = str(item) # Запоминаем имя до удаления
    if not item.shipment.can_be_edited():
        messages.error(request, "Нельзя удалять товары из закрытой накладной!")
        return redirect('shipment_detail', pk=item.shipment.pk)
    item.delete()
    messages.success(request, f'Позиция "{item_name}" удалена из отгрузки.')
    return redirect('shipment_items', pk=shipment_pk)

#Генерация PDF для отгрузки (накладной)
def shipment_pdf_view(request, shipment_id):
    shipment = get_object_or_404(Shipment, id=shipment_id)
    
    # ФИКСАЦИЯ СТАТУСА ПРИ ПЕРВОЙ ПЕЧАТИ
    if shipment.status == 'pending':
        shipment.status = 'packaged'
        shipment.processed_by = request.user
        shipment.save(update_fields=['status', 'processed_by'])

    items = shipment.items.all()
    
    # Собираем контекст для шаблона
    context = {
        'shipment': shipment,
        'items': items,
        'request': request, # важно для путей к медиа-файлам
    }

    # Рендерим HTML в строку
    html_string = render_to_string('warehouse2/shipment_pdf.html', context)

    # Создаем PDF в памяти
    html = HTML(string=html_string, base_url=request.build_absolute_uri('/'))
    pdf = html.write_pdf()

    # Отдаем PDF браузеру
    response = HttpResponse(pdf, content_type='application/pdf')
    # 'inline' откроет в браузере, 'attachment' сразу начнет скачку
    response['Content-Disposition'] = f'inline; filename="shipment_{shipment.id}.pdf"'
    
    return response

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
            'info': f"Арт: {p.sku} | Доступно: {int(p.available_quantity)} шт. | Цена: {p.price} грн",
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