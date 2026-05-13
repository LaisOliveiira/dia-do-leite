from django.contrib import admin
from .models import Pedido, Lote

@admin.register(Lote)
class LoteAdmin(admin.ModelAdmin):
    list_display = ('nome', 'preco_palestras', 'preco_minicurso', 'preco_combo', 'ativo')
    list_filter = ('ativo',)

@admin.register(Pedido)
class PedidoAdmin(admin.ModelAdmin):
    # Correção aqui: Usamos 'status' e 'data_criacao' que são os nomes exatos do seu model!
    list_display = ('id', 'usuario', 'pacote', 'valor_total', 'status', 'data_criacao')
    list_filter = ('status', 'pacote')
    search_fields = ('usuario__username', 'usuario__first_name', 'usuario__email')