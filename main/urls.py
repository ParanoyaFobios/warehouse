from django.urls import path
from django.contrib.auth.views import LogoutView
from .views import LoginView, LogoutView, IndexView
from . import views


urlpatterns = [
    path('login/', LoginView.as_view(), name='login'),
    path('logout/', LogoutView.as_view(), name='logout'),
    path('users/', views.UserListView.as_view(), name='user_list'),
    path('users/create/', views.CreateUserWithGroupView.as_view(), name='create_user'),
    path('', IndexView.as_view(), name='start-page'),
    path('search/', views.global_search_view, name='global_search'),
    path('barcode/<int:content_type_id>/<int:object_id>/display/', views.barcode_display_page_view, name='barcode_display_page'),
    path('barcode/<int:content_type_id>/<int:object_id>/image/', views.generate_barcode_view, name='generate_barcode_image'),
    # адрес для прокси изображений продуктов, чтобы передавать в KeyCRM
    path('img-proxy/<int:product_id>/', views.product_image_proxy, name='product_image_proxy'),
]