from django.urls import path
from . import views

urlpatterns = [
    path('cadastro/', views.cadastro_view, name='cadastro'),
    path('login/', views.login_view, name='login'),
    path('logout/', views.logout_view, name='logout'),
    path('painel/', views.painel_view, name='painel'),
    path('perfil/', views.perfil_view, name='perfil'),
    path('certificados/', views.certificados_view, name='certificados'),
    path('gerar-pdf/<int:inscricao_id>/', views.gerar_certificado_pdf, name='gerar_certificado_pdf'),
    path('ativar/<uidb64>/<token>/', views.ativar_conta_view, name='ativar_conta'),
]