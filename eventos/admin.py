from django.contrib import admin
from .models import TipoEvento, Evento, Inscricao
from .models import Edicao, GaleriaFoto

admin.site.register(TipoEvento)
admin.site.register(Evento)
admin.site.register(Inscricao)

class GaleriaInline(admin.TabularInline):
    model = GaleriaFoto
    extra = 3

@admin.register(Edicao)
class EdicaoAdmin(admin.ModelAdmin):
    inlines = [GaleriaInline]