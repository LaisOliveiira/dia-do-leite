from django.contrib import admin
from .models import TipoEvento, Evento, Inscricao
from .models import Edicao, GaleriaFoto

admin.site.register(TipoEvento)
admin.site.register(Evento)
admin.site.register(Inscricao)

class GaleriaFotoInline(admin.TabularInline):
    model = GaleriaFoto
    extra = 30 # Quantos campos em branco aparecem de uma vez para subir as fotos

@admin.register(Edicao)
class EdicaoAdmin(admin.ModelAdmin):
    list_display = ('numero', 'ano', 'ativa')
    inlines = [GaleriaFotoInline] # Isso faz a mágica de juntar as fotos na tela da Edição