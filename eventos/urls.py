from django.urls import path
from . import views

urlpatterns = [
   
    path('edicoes/', views.lista_edicoes, name='lista_edicoes'),
    path('edicoes/', views.lista_edicoes, name='lista_edicoes'),

    path('portaria/', views.portaria_checkin, name='portaria_checkin'),
]