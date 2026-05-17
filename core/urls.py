from django.urls import path
from . import views
from pagamentos.views import comprar_ingressos
from pagamentos.views import comprar_ingressos, mercado_pago_webhook

urlpatterns = [
    path('', views.landing_page, name='landing_page'),
    
    # Nova rota do painel da Safra Jr:
    path('dashboard/', views.dashboard_view, name='dashboard'),
    
    # Rota correta dos ingressos que já estava aqui:
    path('comprar-ingressos/', comprar_ingressos, name='comprar_ingressos'),
    path('webhook/mercadopago/', mercado_pago_webhook, name='webhook_mp'),
]