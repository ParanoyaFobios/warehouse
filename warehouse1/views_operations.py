from django.views.generic import TemplateView
from django.contrib.auth.mixins import LoginRequiredMixin
from django.urls import reverse_lazy
from django.contrib import messages
from django.db.models import Q
from .models import Material
from .forms import MaterialSearchForm, MaterialOperationForm
from django.shortcuts import get_object_or_404
from django.shortcuts import redirect, get_object_or_404


class MaterialOperationView(LoginRequiredMixin, TemplateView):
    template_name = 'warehouse1/operation_single_page.html' # Мы создадим новый шаблон
    success_url = reverse_lazy('start-page')
    operation_type = None # Будет 'incoming' или 'outgoing'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        
        # Определяем название операции для шаблона
        context['operation_type'] = self.operation_type
        context['operation_name'] = 'Прием' if self.operation_type == 'incoming' else 'Выдача'
        
        # Форма для поиска всегда в контексте
        context['search_form'] = MaterialSearchForm(self.request.GET or None)
        
        # Если в GET-запросе есть параметры поиска, выполняем его
        search_query = self.request.GET.get('name') or self.request.GET.get('article') or self.request.GET.get('barcode')
        if search_query:
            query = Q()
            if self.request.GET.get('barcode'):
                query &= Q(barcode__icontains=self.request.GET.get('barcode'))
            if self.request.GET.get('name'):
                query &= Q(name__icontains=self.request.GET.get('name'))
            if self.request.GET.get('article'):
                query &= Q(article__icontains=self.request.GET.get('article'))
            
            materials = Material.objects.filter(query)
            
            # Добавляем к каждому материалу свою форму операции
            material_forms = []
            for material in materials:
                material_forms.append({
                    'material': material,
                    'form': MaterialOperationForm()
                })
            context['material_forms'] = material_forms

        return context

    def post(self, request, *args, **kwargs):
        # Получаем ID материала из скрытого поля в форме
        material_id = request.POST.get('material_id')
        if not material_id:
            messages.error(request, "Не удалось определить материал.")
            return redirect(request.path)

        material = get_object_or_404(Material, id=material_id)
        form = MaterialOperationForm(request.POST)

        if form.is_valid():
            quantity = form.cleaned_data['quantity']
            comment = form.cleaned_data['comment']
            
            try:
                op_name_past = '' # для сообщения об успехе
                if self.operation_type == 'incoming':
                    material.add_quantity(quantity, request.user, comment)
                    op_name_past = 'принято'
                elif self.operation_type == 'outgoing':
                    material.subtract_quantity(quantity, request.user, comment)
                    op_name_past = 'выдано'
                
                messages.success(request, f"Успешно {op_name_past} {material.name}: {quantity} {material.unit.short_name}")
            
            except ValueError as e:
                messages.error(request, f"Ошибка с материалом {material.name}: {str(e)}")
        
        else:
            # Если форма невалидна, выводим ошибки
            for error in form.errors.values():
                messages.error(request, error)

        # Перенаправляем обратно на ту же страницу с теми же параметрами поиска
        return redirect(f"{request.path}?{request.GET.urlencode()}")
