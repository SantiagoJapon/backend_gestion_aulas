from django.urls import path
from . import views

urlpatterns = [
    #path('register/', views.RegistroUsuarioView.as_view(), name='registro'),
    path('login/', views.login_view, name='login'),
    #path('perfil/', views.perfil_usuario_view, name='perfil'),
]