from django.contrib import admin
from django.utils.html import format_html
from django.contrib import messages
from .models import Pedido, Lote
from eventos.models import Evento, Inscricao

@admin.register(Lote)
class LoteAdmin(admin.ModelAdmin):
    list_display = ('nome', 'preco_palestras', 'preco_minicurso', 'preco_combo', 'ativo')
    list_filter = ('ativo',)

@admin.register(Pedido)
class PedidoAdmin(admin.ModelAdmin):
    list_display = ('id', 'usuario', 'pacote', 'valor_total', 'status', 'ver_comprovante', 'data_criacao')
    list_filter = ('status', 'pacote', 'data_criacao')
    search_fields = ('usuario__first_name', 'usuario__email', 'id')
    actions = ['aprovar_pedidos', 'recusar_pedidos']

    def ver_comprovante(self, obj):
        if obj.comprovante_produtor:
            return format_html(
                '<a href="{}" target="_blank" style="background-color: #2563eb; color: white; padding: 4px 8px; border-radius: 4px; font-weight: bold; text-decoration: none; text-transform: uppercase; font-size: 10px;">📄 Ver Foto</a>', 
                obj.comprovante_produtor.url
            )
        # O erro estava aqui! Adicionámos o {} e passámos o 'Nenhum' como argumento.
        return format_html('<span style="color: #94a3b8;">{}</span>', 'Nenhum')
    
    ver_comprovante.short_description = "Comprovativo"

    # --- AÇÃO DE APROVAÇÃO (COM GERAÇÃO DE INGRESSOS) ---
    def aprovar_pedidos(self, request, queryset):
        pedidos_aprovados = 0
        
        for pedido in queryset:
            if pedido.status != 'aprovado':
                # 1. Muda o status
                pedido.status = 'aprovado'
                pedido.save()
                
                # 2. GERA OS INGRESSOS (Cópia da lógica do seu Webhook)
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

    # --- AÇÃO DE RECUSA ---
    def recusar_pedidos(self, request, queryset):
        queryset.update(status='recusado')
        self.message_user(request, f"{queryset.count()} pedido(s) foram RECUSADOS!", messages.ERROR)
        
    recusar_pedidos.short_description = "🔴 Recusar pedidos selecionados"

    # --- APROVAÇÃO 1 POR 1 (AO EDITAR O PEDIDO MANUALMENTE) ---
    def save_model(self, request, obj, form, change):
        # Verifica se estamos a editar um pedido que já existe
        if change:
            pedido_antigo = Pedido.objects.get(pk=obj.pk)
            
            # Se o organizador abriu o pedido e mudou o status para "Aprovado"
            if pedido_antigo.status != 'aprovado' and obj.status == 'aprovado':
                
                # GERA OS INGRESSOS AUTOMATICAMENTE!
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
                
        # Deixa o Django fazer o salvamento padrão no banco de dados
        super().save_model(request, obj, form, change)