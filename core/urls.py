from django.urls import path
from . import views

urlpatterns = [
    path('', views.landing_page, name='landing_page'),
    
    # Nova rota do painel da Safra Jr:
    path('dashboard/', views.dashboard_view, name='dashboard'),
]