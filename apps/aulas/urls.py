from django.urls import path
from . import views

urlpatterns = [
    path('', views.AulaListView.as_view(), name='lista-aulas'),
    # Comentamos temporalmente hasta crear las vistas
    # path('tipos/', views.TipoAulaListView.as_view(), name='tipos-aula'),
    # path('disponibilidad/', views.disponibilidad_aulas_view, name='disponibilidad-aulas'),
]