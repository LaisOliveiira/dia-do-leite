from django.contrib import admin
from django.urls import path, include
from eventos import views as eventos_views
# --- ADICIONE ESTES DOIS IMPORTS ---
from django.conf import settings
from django.conf.urls.static import static

urlpatterns = [
    path('admin/', admin.site.urls),
    path('', include('core.urls')),
    path('auth/', include('usuarios.urls')),
    path('eventos/', include('eventos.urls')),
    path('dashboard/novo-evento/', eventos_views.criar_evento_view, name='criar_evento'),
]

# --- ADICIONE ESTA CONDIÇÃO NO FINAL DO FICHEIRO ---
if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)