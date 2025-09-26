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
from PIL import Image, ImageDraw, ImageFont


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
    Генерирует и отдает изображение штрихкода для материала
    с названием материала над штрихкодом.
    """
    material = get_object_or_404(Material, pk=pk)
    
    # 1. Настройки для генерации
    CODE128 = barcode.get_barcode_class('code128')
    # Генерируем штрихкод без текста под ним, так как мы добавим его сами
    writer_options = {
        'module_height': 12.0, # Высота штрихкода
        'font_size': 8,       # Размер шрифта для кода под штрихкодом
        'text_distance': 4.0,  # Расстояние от штрихкода до текста
        'quiet_zone': 2.0      # Отступы по бокам
    }
    writer = ImageWriter(format='PNG')
    
    # 2. Генерируем штрихкод в памяти
    code = CODE128(material.barcode, writer=writer)
    barcode_buffer = io.BytesIO()
    code.write(barcode_buffer, options=writer_options)
    barcode_buffer.seek(0)
    
    # --- Используем Pillow для добавления текста ---
    
    # 3. Открываем сгенерированный штрихкод
    barcode_img = Image.open(barcode_buffer)
    
    # 4. Создаем новое изображение, чтобы разместить на нем текст и штрихкод
    material_name = material.name
    try:
        # Попробуем загрузить стандартный шрифт (путь может отличаться в вашей системе)
        font = ImageFont.truetype("arial.ttf", 14)
    except IOError:
        # Если шрифт не найден, используем шрифт по умолчанию
        font = ImageFont.load_default()
        
    draw = ImageDraw.Draw(barcode_img) # Временный объект для расчета размера текста
    text_bbox = draw.textbbox((0, 0), material_name, font=font)
    text_width = text_bbox[2] - text_bbox[0]
    text_height = text_bbox[3] - text_bbox[1]

    # Определяем размеры нового изображения
    padding = 10 # Отступы
    new_width = max(barcode_img.width, text_width) + padding * 2
    new_height = barcode_img.height + text_height + padding * 2

    # Создаем холст
    final_image = Image.new('RGB', (new_width, new_height), 'white')
    draw = ImageDraw.Draw(final_image)
    
    # 5. Рисуем название материала
    text_x = (new_width - text_width) / 2
    text_y = padding
    draw.text((text_x, text_y), material_name, fill='black', font=font)
    
    # 6. Вставляем штрихкод под текстом
    barcode_x = (new_width - barcode_img.width) / 2
    barcode_y = text_y + text_height + 5 # 5 - небольшой отступ между текстом и штрихкодом
    final_image.paste(barcode_img, (int(barcode_x), int(barcode_y)))

    # 7. Сохраняем финальное изображение в буфер и возвращаем как ответ
    final_buffer = io.BytesIO()
    final_image.save(final_buffer, format='PNG')
    
    return HttpResponse(final_buffer.getvalue(), content_type='image/png')


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