# warehouse1/views_operations.py
from django.shortcuts import render, redirect
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from .forms import IncomingForm, OutgoingForm, InventoryForm
from .models import Material

@login_required
def incoming_operation(request):
    if request.method == 'POST':
        form = IncomingForm(request.POST)
        if form.is_valid():
            try:
                material = Material.objects.get(barcode=form.cleaned_data['barcode'])
                material.add_quantity(
                    quantity=form.cleaned_data['quantity'],
                    user=request.user,
                    comment=form.cleaned_data['comment']
                )
                messages.success(request, f"Материал {material.name} успешно принят в количестве {form.cleaned_data['quantity']} {material.unit.short_name}")
                return redirect('incoming_operation')
            except Material.DoesNotExist:
                messages.error(request, "Материал с таким штрихкодом не найден")
            except Exception as e:
                messages.error(request, f"Ошибка: {str(e)}")
    else:
        form = IncomingForm()
    
    return render(request, 'warehouse1/operation_form.html', {
        'form': form,
        'title': 'Прием материала',
        'action': 'incoming_operation'
    })

@login_required
def outgoing_operation(request):
    if request.method == 'POST':
        form = OutgoingForm(request.POST)
        if form.is_valid():
            try:
                material = Material.objects.get(barcode=form.cleaned_data['barcode'])
                material.subtract_quantity(
                    quantity=form.cleaned_data['quantity'],
                    user=request.user,
                    comment=form.cleaned_data['comment']
                )
                messages.success(request, f"Материал {material.name} успешно выдан в количестве {form.cleaned_data['quantity']} {material.unit.short_name}")
                return redirect('outgoing_operation')
            except Material.DoesNotExist:
                messages.error(request, "Материал с таким штрихкодом не найден")
            except ValueError as e:
                messages.error(request, str(e))
            except Exception as e:
                messages.error(request, f"Ошибка: {str(e)}")
    else:
        form = OutgoingForm()
    
    return render(request, 'warehouse1/operation_form.html', {
        'form': form,
        'title': 'Выдача материала',
        'action': 'outgoing_operation'
    })

@login_required
def inventory_operation(request):
    if request.method == 'POST':
        form = InventoryForm(request.POST)
        if form.is_valid():
            try:
                material = Material.objects.get(barcode=form.cleaned_data['barcode'])
                difference = material.inventory_adjustment(
                    new_quantity=form.cleaned_data['new_quantity'],
                    user=request.user,
                    comment=form.cleaned_data['comment']
                )
                if difference > 0:
                    msg = f"Добавлено {difference} {material.unit.short_name}"
                elif difference < 0:
                    msg = f"Списано {abs(difference)} {material.unit.short_name}"
                else:
                    msg = "Количество не изменилось"
                messages.success(request, f"Инвентаризация {material.name} завершена. {msg}")
                return redirect('inventory_operation')
            except Material.DoesNotExist:
                messages.error(request, "Материал с таким штрихкодом не найден")
            except Exception as e:
                messages.error(request, f"Ошибка: {str(e)}")
    else:
        form = InventoryForm()
    
    return render(request, 'warehouse1/operation_form.html', {
        'form': form,
        'title': 'Инвентаризация',
        'action': 'inventory_operation'
    })