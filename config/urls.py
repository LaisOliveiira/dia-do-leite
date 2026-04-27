from django.contrib import admin
from django.urls import path, include
from eventos import views as eventos_views

urlpatterns = [
    path('admin/', admin.site.urls),
    path('', include('core.urls')),
    path('auth/', include('usuarios.urls')),
    
    # Nova rota para os eventos e inscrições:
    path('eventos/', include('eventos.urls')),

    path('dashboard/novo-evento/', eventos_views.criar_evento_view, name='criar_evento'),
]