from django.contrib import admin
from .models import TipoEvento, Evento, Inscricao

admin.site.register(TipoEvento)
admin.site.register(Evento)
admin.site.register(Inscricao)