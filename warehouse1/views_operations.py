# warehouse1/views_operations.py
from django.views.generic import FormView, TemplateView
from django.contrib.auth.mixins import LoginRequiredMixin
from django.urls import reverse, reverse_lazy
from django.shortcuts import redirect
from django.contrib import messages
from django.db.models import Q
from .models import Material
from .forms import MaterialSearchForm, MaterialOperationForm
from django.shortcuts import get_object_or_404


class OperationBaseView(LoginRequiredMixin):
    operation_type = None
    template_name = 'warehouse1/operation_search.html'
    success_url = reverse_lazy('start-page')

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        # Используем self.operation_type который должен быть установлен в дочерних классах
        context['operation_type'] = self.operation_type
        # Правильно определяем название операции
        if self.operation_type == 'incoming':
            context['operation_name'] = 'Прием'
        elif self.operation_type == 'outgoing':
            context['operation_name'] = 'Выдача'
        else:
            context['operation_name'] = 'Операция'
        return context

class OperationSearchView(OperationBaseView, FormView):
    form_class = MaterialSearchForm

    def form_valid(self, form):
        # Сохраняем тип операции в сессии
        self.request.session['operation_type'] = self.operation_type
        
        # Поиск материалов по разным критериям
        barcode = form.cleaned_data['barcode']
        name = form.cleaned_data['name']
        article = form.cleaned_data['article']

        query = Q()
        if barcode:
            query &= Q(barcode__icontains=barcode)
        if name:
            query &= Q(name__icontains=name)
        if article:
            query &= Q(article__icontains=article)

        materials = Material.objects.filter(query)
        
        if not materials.exists():
            messages.warning(self.request, "Материалы не найдены")
            return redirect(self.request.path)

        # Сохраняем найденные материалы в сессии
        self.request.session['operation_materials'] = list(materials.values_list('id', flat=True))
        return redirect('operation_confirm')

class OperationConfirmView(OperationBaseView, TemplateView):
    template_name = 'warehouse1/operation_confirm.html'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        
        # Получаем тип операции из сессии
        operation_type = self.request.session.get('operation_type')
        context['operation_type'] = operation_type
        
        # Обновляем название операции
        if operation_type == 'incoming':
            context['operation_name'] = 'Прием'
        elif operation_type == 'outgoing':
            context['operation_name'] = 'Выдача'
        elif operation_type == 'inventory':
            context['operation_name'] = 'Инвентаризация'
        
        # Получаем материалы из сессии
        material_ids = self.request.session.get('operation_materials', [])
        materials = Material.objects.filter(id__in=material_ids)
        
        # Создаем формы для каждого материала
        forms = []
        for material in materials:
            forms.append({
                'material': material,
                'form': MaterialOperationForm(prefix=str(material.id))
            })
        
        context['material_forms'] = forms
        return context

    def post(self, request, *args, **kwargs):
        # Получаем тип операции из сессии
        operation_type = request.session.get('operation_type')
        if not operation_type:
            messages.error(request, "Тип операции не определен")
            return redirect('start-page')

        material_ids = request.session.get('operation_materials', [])
        if not material_ids:
            messages.error(request, "Материалы не выбраны")
            return redirect('start-page')

        success_count = 0
        for material_id in material_ids:
            # Создаем форму с префиксом
            form = MaterialOperationForm(request.POST, prefix=str(material_id))
            if form.is_valid():
                material = get_object_or_404(Material, id=material_id)
                quantity = form.cleaned_data['quantity']
                comment = form.cleaned_data['comment']
                
                try:
                    if operation_type == 'incoming':
                        material.add_quantity(quantity, request.user, comment)
                        success_count += 1
                    elif operation_type == 'outgoing':
                        material.subtract_quantity(quantity, request.user, comment)
                        success_count += 1
                    elif operation_type == 'inventory':
                        material.inventory_adjustment(quantity, request.user, comment)
                        success_count += 1
                except ValueError as e:
                    messages.error(request, f"Ошибка с материалом {material.name}: {str(e)}")
                except Exception as e:
                    messages.error(request, f"Ошибка с материалом {material.name}: {str(e)}")
        
        if success_count > 0:
            messages.success(request, f"Успешно {operation_type} {material.name}: {quantity}{material.unit.short_name}")
        return redirect(self.success_url)

class IncomingSearchView(OperationSearchView):
    operation_type = 'incoming'

class OutgoingSearchView(OperationSearchView):
    operation_type = 'outgoing'

class IncomingConfirmView(OperationConfirmView):
    operation_type = 'incoming'

class OutgoingConfirmView(OperationConfirmView):
    operation_type = 'outgoing'