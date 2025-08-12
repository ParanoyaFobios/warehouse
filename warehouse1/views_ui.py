from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from .forms import MaterialForm
from .models import Material

@login_required
def material_list(request):
    materials = Material.objects.all()
    return render(request, 'warehouse1/material_list.html', {'materials': materials})

@login_required
def material_create(request):
    if request.method == 'POST':
        form = MaterialForm(request.POST, request.FILES)
        if form.is_valid():
            material = form.save()
            return redirect('material_list')
    else:
        form = MaterialForm()
    return render(request, 'warehouse1/material_form.html', {'form': form})

@login_required
def material_update(request, pk):
    material = get_object_or_404(Material, pk=pk)
    if request.method == 'POST':
        form = MaterialForm(request.POST, request.FILES, instance=material)
        if form.is_valid():
            form.save()
            return redirect('material_list')
    else:
        form = MaterialForm(instance=material)
    return render(request, 'warehouse1/material_form.html', {'form': form})