from django.urls import path
from . import views
from pagamentos.views import comprar_ingressos

urlpatterns = [
    path('', views.landing_page, name='landing_page'),
    
    # Nova rota do painel da Safra Jr:
    path('dashboard/', views.dashboard_view, name='dashboard'),
    
    # Rota correta dos ingressos que já estava aqui:
    path('comprar-ingressos/', comprar_ingressos, name='comprar_ingressos'),
]