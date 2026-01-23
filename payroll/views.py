from django.urls import reverse_lazy
from django.views.generic import ListView, CreateView, UpdateView, DeleteView, TemplateView
from .models import Operation, TechCardGroup, TechCardOperation, WorkEntry, Payout, PenaltyBonus, User
from .forms import OperationForm, TechCardGroupForm, HourlyWorkForm, PieceWorkForm, TechCardOperationFormSet
from django.db import transaction
from django.contrib import messages
from warehouse2.models import Product
from django.http import JsonResponse
from django.contrib.auth.mixins import LoginRequiredMixin
from django.shortcuts import redirect, get_object_or_404
from django.db.models import Sum, F, Q, DecimalField
from django.contrib.auth.models import User
from django.db.models.functions import Coalesce

#===============================================
# Операции CRUD для Operation и TechCardGroup
#===============================================
class OperationListView(ListView):
    model = Operation
    template_name = 'payroll/operation_list.html'
    context_object_name = 'operations'

class OperationCreateView(CreateView):
    model = Operation
    form_class = OperationForm
    template_name = 'payroll/operation_form.html'
    success_url = reverse_lazy('operation_list')

class OperationUpdateView(UpdateView):
    model = Operation
    form_class = OperationForm
    template_name = 'payroll/operation_form.html'
    success_url = reverse_lazy('operation_list')

class OperationDeleteView(DeleteView):
    model = Operation
    template_name = 'payroll/operation_confirm_delete.html'
    success_url = reverse_lazy('operation_list')

#===============================================
# Техкарты CRUD для TechCardGroup и TechCardOperation
#===============================================

class TechCardListView(ListView):
    model = TechCardGroup
    template_name = 'payroll/tech_card_list.html'
    context_object_name = 'tech_cards'

class TechCardGroupMixin:
    """Миксин для обработки общей логики создания и редактирования"""
    model = TechCardGroup
    form_class = TechCardGroupForm
    template_name = 'payroll/tech_card_form.html'
    success_url = reverse_lazy('tech_card_list')

    def get_context_data(self, **kwargs):
        data = super().get_context_data(**kwargs)
        if self.request.POST:
            data['formset'] = TechCardOperationFormSet(self.request.POST, instance=self.object)
        else:
            data['formset'] = TechCardOperationFormSet(instance=self.object)
        return data

    def form_valid(self, form):
        context = self.get_context_data()
        formset = context['formset']
        with transaction.atomic():
            self.object = form.save()
            if formset.is_valid():
                formset.instance = self.object
                formset.save()
            else:
                return self.form_invalid(form)
        return super().form_valid(form)

class TechCardCreateView(TechCardGroupMixin, CreateView):
    pass

class TechCardUpdateView(TechCardGroupMixin, UpdateView):
    pass

class TechCardDeleteView(DeleteView):
    model = TechCardGroup
    template_name = 'payroll/tech_card_confirm_delete.html'
    success_url = reverse_lazy('tech_card_list')


class BulkAssignTechCardView(ListView):
    model = Product
    template_name = 'payroll/bulk_assign.html'
    context_object_name = 'products'
    paginate_by = 50  # По 50 товаров на страницу

    def get_queryset(self):
        # Показываем сначала товары без техкарт, чтобы менеджер видел пробелы
        return Product.objects.all().order_by('tech_card', 'name')

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['tech_cards'] = TechCardGroup.objects.all()
        return context

    def post(self, request, *args, **kwargs):
        product_ids = request.POST.getlist('selected_products')
        tech_card_id = request.POST.get('tech_card')

        if not product_ids:
            messages.warning(request, "Вы не выбрали ни одного товара.")
            return redirect('bulk_assign_tech_card')

        if not tech_card_id:
            messages.warning(request, "Выберите техкарту для назначения.")
            return redirect('bulk_assign_tech_card')

        # Массовое обновление в базе (один SQL запрос)
        tech_card = TechCardGroup.objects.get(id=tech_card_id)
        Product.objects.filter(id__in=product_ids).update(tech_card=tech_card)

        messages.success(request, f"Техкарта '{tech_card.name}' успешно назначена для {len(product_ids)} товаров.")
        return redirect('bulk_assign_tech_card')
    


#===============================================
# Представления для подачи заявок на выполненные работы
#===============================================
    
class WorkSelectionView(LoginRequiredMixin, TemplateView):
    """Главная страница кабинета работника"""
    template_name = 'payroll/worker_cabinet.html'

class WorkEntryCreateView(LoginRequiredMixin, CreateView):
    model = WorkEntry
    template_name = 'payroll/work_entry_form.html'
    success_url = reverse_lazy('worker_cabinet')

    def get_form_class(self):
        if self.kwargs.get('type') == 'hourly':
            return HourlyWorkForm
        return PieceWorkForm

    def form_valid(self, form):
        form.instance.worker = self.request.user
        return super().form_valid(form)

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['work_type'] = self.kwargs.get('type')
        return context

def get_operations_for_product(request):
    """Вспомогательный API-метод для динамического обновления списка операций"""
    product_id = request.GET.get('product_id')
    product = Product.objects.get(id=product_id)
    # Берем операции только из привязанной техкарты
    ops = TechCardOperation.objects.filter(group=product.tech_card).select_related('operation')
    
    data = [{'id': o.operation.id, 'name': o.operation.name} for o in ops]
    return JsonResponse(data, safe=False)

#===============================================
# Кабинет менеджера, подтверждение заявок на работы
#===============================================

class WorkVerificationListView(ListView):
    model = WorkEntry
    template_name = 'payroll/verify_work.html'
    context_object_name = 'entries'

    def get_queryset(self):
        # Показываем только непроверенные записи
        return WorkEntry.objects.filter(is_verified=False).order_by('-created_at')

    def post(self, request, *args, **kwargs):
        # Массовое подтверждение через чекбоксы
        entry_ids = request.POST.getlist('selected_entries')
        if entry_ids:
            WorkEntry.objects.filter(id__in=entry_ids).update(
                is_verified=True, 
                verified_by=request.user
            )
            messages.success(request, f"Подтверждено записей: {len(entry_ids)}")
        return redirect('verify_work_list')
    
class PenaltyBonusCreateView(CreateView):
    model = PenaltyBonus
    fields = ['worker', 'type', 'amount', 'reason']
    template_name = 'payroll/add_penalty_bonus.html'
    success_url = reverse_lazy('accountant_dashboard') # После добавления вернемся в дашборд

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['title'] = "Начислить премию или штраф"
        return context
    
#===============================================
# Бухгалтерия
#===============================================


class AccountantDashboardView(ListView):
    model = User
    template_name = 'payroll/accountant_dashboard.html'
    context_object_name = 'workers'

    def get_queryset(self):
        # Используем Coalesce, чтобы вместо None (если записей нет) был 0
        return User.objects.annotate(
            earned=Coalesce(
                Sum('work_entries__final_rate', 
                    filter=Q(work_entries__is_verified=True)), 
                0, output_field=DecimalField()
            ),
            paid=Coalesce(
                Sum('payouts__amount'), 
                0, output_field=DecimalField()
            ),
            # Добавляем премии и штрафы (если они есть)
            bonuses=Coalesce(
                Sum('penaltybonus__amount', filter=Q(penaltybonus__type='bonus')), 
                0, output_field=DecimalField()
            ),
            penalties=Coalesce(
                Sum('penaltybonus__amount', filter=Q(penaltybonus__type='penalty')), 
                0, output_field=DecimalField()
            )
        ).order_by('username')

class WorkerPayrollDetailView(CreateView):
    """Детальный расчет по одному сотруднику + форма выплаты"""
    model = Payout
    fields = ['amount', 'comment']
    template_name = 'payroll/worker_payroll_detail.html'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        worker = get_object_or_404(User, id=self.kwargs['worker_id'])
        
        # Считаем заработок (кол-во * ставку) для подтвержденных записей
        entries = WorkEntry.objects.filter(worker=worker, is_verified=True)
        total_earned = sum(e.quantity * e.final_rate for e in entries)
        
        # Считаем выплаты
        payouts = Payout.objects.filter(worker=worker)
        total_paid = payouts.aggregate(Sum('amount'))['amount__sum'] or 0

        context['worker'] = worker
        context['entries'] = entries.order_by('-date_performed')
        context['payouts'] = payouts.order_by('-date_paid')
        context['total_earned'] = total_earned
        context['total_paid'] = total_paid
        context['balance'] = total_earned - total_paid
        return context

    def form_valid(self, form):
        form.instance.worker = get_object_or_404(User, id=self.kwargs['worker_id'])
        return super().form_valid(form)

    def get_success_url(self):
        return reverse_lazy('worker_payroll_detail', kwargs={'worker_id': self.kwargs['worker_id']})