import csv
from django.http import HttpResponse
from django.contrib import admin
from .models import TipoEvento, Evento, Inscricao, Edicao, GaleriaFoto

admin.site.register(TipoEvento)

# --- Tabela de Inscrições Inteligente ---
@admin.register(Inscricao)
class InscricaoAdmin(admin.ModelAdmin):
    list_display = ('usuario', 'evento', 'codigo_ingresso', 'presenca_confirmada')
    list_filter = ('evento', 'presenca_confirmada')
    search_fields = ('usuario__first_name', 'usuario__email', 'usuario__cpf', 'codigo_ingresso')
    list_editable = ('presenca_confirmada',) 

# --- Botão de Exportação Inteligente e Separada ---
@admin.register(Evento)
class EventoAdmin(admin.ModelAdmin):
    list_display = ('titulo', 'tipo', 'data_evento', 'vagas')
    list_filter = ('tipo', 'data_evento')
    search_fields = ('titulo',)
    actions = ['exportar_lista_presenca']

    def exportar_lista_presenca(self, request, queryset):
        response = HttpResponse(content_type='text/csv')
        response['Content-Disposition'] = 'attachment; filename="lista_presenca_organizada.csv"'
        response.write(u'\ufeff'.encode('utf8')) # Garante a leitura correta de acentos no Excel

        writer = csv.writer(response, delimiter=';')
        
        # Separa internamente o que é palestra e o que é minicurso
        palestras_selecionadas = queryset.filter(tipo__nome__icontains='palestra')
        minicursos_selecionados = queryset.exclude(tipo__nome__icontains='palestra')
        
        # 1. SEÇÃO UNIFICADA DE PALESTRAS (Sem nomes duplicados)
        if palestras_selecionadas.exists():
            writer.writerow(['--- LISTA GERAL DE PALESTRAS ---'])
            writer.writerow(['Nome Completo', 'Ingresso', 'Presença Confirmada'])
            
            inscricoes_palestras = Inscricao.objects.filter(evento__in=palestras_selecionadas).select_related('usuario')
            
            # Conjunto para rastrear quem já foi adicionado e evitar repetições
            usuarios_processados = set()
            for inscricao in inscricoes_palestras:
                aluno = inscricao.usuario
                if aluno.id not in usuarios_processados:
                    usuarios_processados.add(aluno.id)
                    writer.writerow([
                        aluno.first_name,
                        inscricao.codigo_ingresso,
                        "SIM" if inscricao.presenca_confirmada else "NÃO"
                    ])
            
            # Espaçamento estético caso existam minicursos abaixo
            if minicursos_selecionados.exists():
                writer.writerow([])
                writer.writerow([])

        # 2. SEÇÕES ISOLADAS PARA CADA MINICURSO
        for minicurso in minicursos_selecionados:
            writer.writerow([f'--- MINICURSO: {minicurso.titulo} ---'])
            writer.writerow(['Nome Completo', 'Ingresso', 'Presença Confirmada'])
            
            inscricoes_mini = Inscricao.objects.filter(evento=minicurso).select_related('usuario')
            for inscricao in inscricoes_mini:
                aluno = inscricao.usuario
                writer.writerow([
                    aluno.first_name,
                    inscricao.codigo_ingresso,
                    "SIM" if inscricao.presenca_confirmada else "NÃO"
                ])
                
            # Linha em branco de separação entre minicursos diferentes
            writer.writerow([])

        return response
    
    exportar_lista_presenca.short_description = "📋 Baixar Lista de Presença Organizada (Excel/CSV)"

# --- Configurações da Galeria ---
class GaleriaFotoInline(admin.TabularInline):
    model = GaleriaFoto
    extra = 30

@admin.register(Edicao)
class EdicaoAdmin(admin.ModelAdmin):
    list_display = ('numero', 'ano', 'ativa')
    inlines = [GaleriaFotoInline]