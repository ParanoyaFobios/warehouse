from django.urls import path
from . import views

urlpatterns = [
    path('operations/', views.OperationListView.as_view(), name='operation_list'),
    path('operations/create/', views.OperationCreateView.as_view(), name='operation_create'),
    path('operations/<int:pk>/update/', views.OperationUpdateView.as_view(), name='operation_update'),
    path('operations/<int:pk>/delete/', views.OperationDeleteView.as_view(), name='operation_delete'),
    # Tech Card URLs
    path('tech-cards/', views.TechCardListView.as_view(), name='tech_card_list'),
    path('tech-cards/create/', views.TechCardCreateView.as_view(), name='tech_card_create'),
    path('tech-cards/<int:pk>/edit/', views.TechCardUpdateView.as_view(), name='tech_card_update'),
    path('tech-cards/<int:pk>/delete/', views.TechCardDeleteView.as_view(), name='tech_card_delete'),
    path('assign-tech-cards/', views.BulkAssignTechCardView.as_view(), name='bulk_assign_tech_card'),
    # Work Entry URLs
    path('my-work/', views.WorkSelectionView.as_view(), name='worker_cabinet'),
    path('my-work/add/<str:type>/', views.WorkEntryCreateView.as_view(), name='add_work'),
    path('my-work-enteries/', views.MyWorkEntriesListView.as_view(), name='my_work_entries'),
    # API для JS
    path('api/get-operations/', views.get_operations_for_product, name='api_get_operations'),
    # Кабинет менеджера
    path('verify/', views.WorkVerificationListView.as_view(), name='verify_work_list'),
    path('verify/reject/<int:pk>/', views.reject_work_entry, name='reject_work_entry'),
    path('accounting/penalty-bonus/add/', views.PenaltyBonusCreateView.as_view(), name='add_penalty_bonus'),
    # бухгалтерия
    path('accounting/', views.AccountantDashboardView.as_view(), name='accountant_dashboard'),
    path('accounting/worker/<int:worker_id>/', views.WorkerPayrollDetailView.as_view(), name='worker_payroll_detail'),
]