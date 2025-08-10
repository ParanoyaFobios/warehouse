from django.urls import path
from django.contrib.auth.views import LogoutView
from .views import LoginView, LogoutView, IndexView


urlpatterns = [
    path('login/', LoginView.as_view(), name='login'),
    path('logout/', LogoutView.as_view(), name='logout'),
    path('', IndexView.as_view(), name='start-page'),
]