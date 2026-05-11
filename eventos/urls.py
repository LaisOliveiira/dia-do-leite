from django.urls import path
from . import views

urlpatterns = [
    path('inscrever/<int:evento_id>/', views.inscrever_evento_view, name='inscrever_evento'),
    path('edicoes/', views.lista_edicoes, name='lista_edicoes'),
]