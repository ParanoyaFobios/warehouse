# warehouse1/views.py
from django.views.generic import ListView, CreateView, UpdateView
from django.contrib.auth.mixins import LoginRequiredMixin
from django.urls import reverse_lazy
from .models import Material, MaterialCategory
from .forms import MaterialForm
from django.db import models


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

class MaterialUpdateView(LoginRequiredMixin, UpdateView):
    model = Material
    form_class = MaterialForm
    template_name = 'warehouse1/material_form.html'
    success_url = reverse_lazy('material_list')

    def form_valid(self, form):
        # Дополнительные действия перед сохранением
        return super().form_valid(form)