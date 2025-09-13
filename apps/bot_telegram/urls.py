from django.urls import path
from . import views

urlpatterns = [
    path('webhook/', views.webhook_telegram_view, name='webhook-telegram'),
]