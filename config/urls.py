from django.contrib import admin
from django.urls import path, include
from eventos import views as eventos_views
from pagamentos import views as pagamentos_views  # <-- NOVO IMPORT ADICIONADO AQUI

from django.conf import settings
from django.conf.urls.static import static

# --- TRAVA DE SEGURANÇA DO PAINEL ADMIN ---
# Bloqueia o /admin para a equipe. Apenas quem é "Superusuário" consegue entrar.
admin.site.has_permission = lambda request: request.user.is_active and request.user.is_superuser
# ------------------------------------------

urlpatterns = [
    path('admin/', admin.site.urls),
    path('', include('core.urls')),
    path('auth/', include('usuarios.urls')),
    path('eventos/', include('eventos.urls')),
    path('dashboard/novo-evento/', eventos_views.criar_evento_view, name='criar_evento'),

    # <-- NOVA ROTA DOS CRACHÁS AQUI -->
    path('gerador-crachas/', pagamentos_views.gerador_crachas, name='gerador_crachas'),
    path('lista-assinaturas/', pagamentos_views.lista_assinaturas, name='lista_assinaturas'),
    path('relatorio-cpf/', pagamentos_views.baixar_relatorio_cpf, name='baixar_relatorio_cpf'),
]

# --- ADICIONE ESTA CONDIÇÃO NO FINAL DO FICHEIRO ---
if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)

