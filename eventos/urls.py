from django.urls import path
from . import views

urlpatterns = [
   
    path('edicoes/', views.lista_edicoes, name='lista_edicoes'),
]