from django.urls import path
from . import views

urlpatterns = [
    path('estadisticas/', views.estadisticas_generales_view, name='estadisticas'),
 
]