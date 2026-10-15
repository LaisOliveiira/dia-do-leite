from django.contrib import admin
from django.utils.html import format_html
from django.contrib import messages
from .models import Pedido, Lote
from eventos.models import Evento, Inscricao
from django.db import transaction

@admin.register(Lote)
class LoteAdmin(admin.ModelAdmin):
    list_display = ('nome', 'preco_palestras', 'preco_minicurso', 'preco_combo', 'ativo')
    list_filter = ('ativo',)

@admin.register(Pedido)
class PedidoAdmin(admin.ModelAdmin):
    list_display = ('id', 'get_nome_cliente', 'pacote', 'valor_total', 'status', 'ver_comprovante', 'data_criacao')
    list_filter = ('status', 'pacote', 'data_criacao')
    search_fields = ('usuario__first_name', 'usuario__email', 'id')
    actions = ['aprovar_pedidos', 'recusar_pedidos']

    def get_nome_cliente(self, obj):
        if obj.usuario and obj.usuario.first_name:
            return f"{obj.usuario.first_name} {obj.usuario.last_name or ''}".strip()
        return obj.usuario.username if obj.usuario else "Sem Usuário"
    
    get_nome_cliente.short_description = "Cliente"

    def ver_comprovante(self, obj):
        if obj.comprovante_produtor and obj.comprovante_pix:
            return format_html(
                '<a href="{}" target="_blank" style="background-color: #2563eb; color: white; padding: 4px 8px; border-radius: 4px; font-weight: bold; text-decoration: none; text-transform: uppercase; font-size: 10px; margin-right: 4px;">🌾 PRODUTOR</a>'
                '<a href="{}" target="_blank" style="background-color: #10b981; color: white; padding: 4px 8px; border-radius: 4px; font-weight: bold; text-decoration: none; text-transform: uppercase; font-size: 10px;">💸 PIX</a>',
                obj.comprovante_produtor.url, obj.comprovante_pix.url
            )
        elif obj.comprovante_produtor:
            return format_html(
                '<a href="{}" target="_blank" style="background-color: #2563eb; color: white; padding: 4px 8px; border-radius: 4px; font-weight: bold; text-decoration: none; text-transform: uppercase; font-size: 10px;">🌾 PRODUTOR</a>', 
                obj.comprovante_produtor.url
            )
        elif obj.comprovante_pix:
            return format_html(
                '<a href="{}" target="_blank" style="background-color: #10b981; color: white; padding: 4px 8px; border-radius: 4px; font-weight: bold; text-decoration: none; text-transform: uppercase; font-size: 10px;">💸 PIX</a>', 
                obj.comprovante_pix.url
            )
        return format_html('<span style="color: #94a3b8;">{}</span>', 'Nenhum')
    
    ver_comprovante.short_description = "Comprovativo"

    # --- FUNÇÃO INVISÍVEL: O "LIXEIRO" DE INGRESSOS ---
    def remover_ingressos_do_pedido(self, pedido):
        with transaction.atomic():
            if pedido.pacote in ['palestras', 'combo']:
                palestras = Evento.objects.filter(tipo__nome__icontains='palestra')
                Inscricao.objects.filter(usuario=pedido.usuario, evento__in=palestras).delete()
            
            if pedido.pacote in ['minicurso', 'combo'] and pedido.minicurso_selecionado:
                apagados, _ = Inscricao.objects.filter(usuario=pedido.usuario, evento=pedido.minicurso_selecionado).delete()
                if apagados > 0:
                    pedido.minicurso_selecionado.vagas += 1
                    pedido.minicurso_selecionado.save()

    def aprovar_pedidos(self, request, queryset):
        pedidos_aprovados = 0
        for pedido in queryset:
            if pedido.status != 'aprovado':
                with transaction.atomic():
                    pedido.status = 'aprovado'
                    pedido.save()
                    
                    if pedido.pacote in ['palestras', 'combo']:
                        palestras = Evento.objects.filter(tipo__nome__icontains='palestra')
                        for palestra in palestras:
                            Inscricao.objects.get_or_create(usuario=pedido.usuario, evento=palestra)
                    
                    if pedido.pacote in ['minicurso', 'combo'] and pedido.minicurso_selecionado:
                        inscricao, created = Inscricao.objects.get_or_create(
                            usuario=pedido.usuario, 
                            evento=pedido.minicurso_selecionado
                        )
                        if created and pedido.minicurso_selecionado.vagas > 0:
                            pedido.minicurso_selecionado.vagas -= 1
                            pedido.minicurso_selecionado.save()
                    
                    pedidos_aprovados += 1
                
        if pedidos_aprovados > 0:
            self.message_user(request, f"{pedidos_aprovados} pedido(s) foram APROVADOS e os ingressos foram gerados para os alunos!", messages.SUCCESS)
        else:
            self.message_user(request, "Nenhum pedido novo foi aprovado (talvez já estivessem aprovados).", messages.WARNING)
            
    aprovar_pedidos.short_description = "🟢 Aprovar pedidos e Gerar Ingressos"

    def recusar_pedidos(self, request, queryset):
        for pedido in queryset:
            if pedido.status == 'aprovado':
                self.remover_ingressos_do_pedido(pedido)
            pedido.status = 'recusado'
            pedido.save()
            
        self.message_user(request, f"{queryset.count()} pedido(s) foram RECUSADOS!", messages.ERROR)
        
    recusar_pedidos.short_description = "🔴 Recusar pedidos selecionados"

    def delete_model(self, request, obj):
        self.remover_ingressos_do_pedido(obj)
        super().delete_model(request, obj)

    def delete_queryset(self, request, queryset):
        for obj in queryset:
            self.remover_ingressos_do_pedido(obj)
        super().delete_queryset(request, queryset)

    def save_model(self, request, obj, form, change):
        if change:
            pedido_antigo = Pedido.objects.get(pk=obj.pk)
            
            if pedido_antigo.status != 'aprovado' and obj.status == 'approved':
                pass
            
            # Remove ingressos caso o status saia de 'aprovado'
            if pedido_antigo.status == 'aprovado' and obj.status != 'aprovado':
                self.remover_ingressos_do_pedido(obj)
            
            if pedido_antigo.status != 'aprovado' and obj.status == 'aprovado':
                with transaction.atomic():
                    if obj.pacote in ['palestras', 'combo']:
                        palestras = Evento.objects.filter(tipo__nome__icontains='palestra')
                        for palestra in palestras:
                            Inscricao.objects.get_or_create(usuario=obj.usuario, evento=palestra)
                    
                    if obj.pacote in ['minicurso', 'combo'] and obj.minicurso_selecionado:
                        inscricao, created = Inscricao.objects.get_or_create(
                            usuario=obj.usuario, 
                            evento=obj.minicurso_selecionado
                        )
                        if created and obj.minicurso_selecionado.vagas > 0:
                            obj.minicurso_selecionado.vagas -= 1
                            obj.minicurso_selecionado.save()
                            
                    messages.success(request, f"O pedido foi aprovado manualmente e os ingressos de {obj.usuario.first_name} foram gerados!")
                
        super().save_model(request, obj, form, change)