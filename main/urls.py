from django.urls import path
from django.contrib.auth.views import LogoutView
from .views import LoginView, LogoutView, IndexView
from . import views


urlpatterns = [
    path('login/', LoginView.as_view(), name='login'),
    path('logout/', LogoutView.as_view(), name='logout'),
    path('users/create/', views.CreateUserWithGroupView.as_view(), name='create_user'),
    path('', IndexView.as_view(), name='start-page'),
    path('barcode/<int:content_type_id>/<int:object_id>/', views.generate_barcode_view, name='generate_barcode'),
    path('search/', views.global_search_view, name='global_search'),
]