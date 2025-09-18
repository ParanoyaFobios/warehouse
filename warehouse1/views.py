from django.views.generic import ListView, CreateView, UpdateView, DetailView
from django.contrib.auth.mixins import LoginRequiredMixin
from django.urls import reverse, reverse_lazy
from .models import Material, MaterialCategory
from .forms import MaterialForm
from django.db import models
from django.shortcuts import get_object_or_404
from django.http import HttpResponse
from django.db.models import F
import barcode
from barcode.writer import ImageWriter # для генерации PNG
import io # для работы с данными в памяти
from django.utils.safestring import mark_safe


class MaterialListView(LoginRequiredMixin, ListView):
    model = Material
    template_name = 'warehouse1/material_list.html'
    context_object_name = 'materials'
    paginate_by = 20

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
                models.Q(article__icontains=search) |
                models.Q(barcode__icontains=search))
        
        return queryset

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['categories'] = MaterialCategory.objects.all()
        return context

class MaterialCreateView(LoginRequiredMixin, CreateView):
    model = Material
    form_class = MaterialForm
    template_name = 'warehouse1/material_form.html'
    success_url = reverse_lazy('material_list')

    def form_valid(self, form):
        # Дополнительные действия перед сохранением
        return super().form_valid(form)
    
def material_barcode_view(request, pk):
    """
    Генерирует и отдает изображение штрихкода для материала.
    """
    material = get_object_or_404(Material, pk=pk)
    
    # 1. Выбираем формат штрихкода (Code128 - хороший универсальный выбор)
    CODE128 = barcode.get_barcode_class('code128')
    
    # 2. Создаем штрихкод с данными из нашего поля, используя writer для PNG
    # Writer можно настроить (шрифты, размеры и т.д.)
    writer = ImageWriter(format='PNG')
    code = CODE128(material.barcode, writer=writer)
    
    # 3. Генерируем изображение в памяти, а не в файл
    buffer = io.BytesIO()
    code.write(buffer)
    
    # 4. Возвращаем изображение как HTTP-ответ
    return HttpResponse(buffer.getvalue(), content_type='image/png')


class MaterialDetailView(LoginRequiredMixin, DetailView):
    model = Material
    template_name = 'warehouse1/material_detail.html'
    context_object_name = 'material'
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        # Добавляем историю операций
        context['operations'] = self.object.materialoperation_set.order_by('-date')[:15]
        # Генерируем HTML для отображения штрихкода
        barcode_url = reverse('material_barcode', kwargs={'pk': self.object.pk})
        context['barcode_img'] = mark_safe(
            f'<img src="{barcode_url}" alt="{self.object.barcode}" class="img-fluid">'
        )
        
        return context
    

class MaterialUpdateView(LoginRequiredMixin, UpdateView):
    model = Material
    form_class = MaterialForm
    template_name = 'warehouse1/material_form.html'
    success_url = reverse_lazy('material_list')

    def form_valid(self, form):
        # Дополнительные действия перед сохранением
        return super().form_valid(form)