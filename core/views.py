from django.shortcuts import render, redirect
from django.contrib.auth.decorators import login_required
from django.db.models import Sum, Count

from eventos.models import Evento, Inscricao
from pagamentos.models import Pedido

def landing_page(request):
    eventos = Evento.objects.all()
    
    # TRAVA DE SEGURANÇA: Só procura inscrições se a pessoa estiver logada
    if request.user.is_authenticated:
        minhas_inscricoes = Inscricao.objects.filter(usuario=request.user).values_list('evento_id', flat=True)
        ja_tem_minicurso = Inscricao.objects.filter(usuario=request.user, evento__tipo__nome__icontains='minicurso').exists()
    else:
        # Se for um visitante sem conta, não tem inscrições
        minhas_inscricoes = []
        ja_tem_minicurso = False
    
    return render(request, 'core/landing_page.html', {
        'eventos': eventos,
        'minhas_inscricoes': minhas_inscricoes,
        'ja_tem_minicurso': ja_tem_minicurso
    })


@login_required(login_url='/auth/login/')
def dashboard_view(request):
    # Trava de segurança: Apenas a organização (Staff ou Empresa) pode acessar
    if not request.user.is_staff and request.user.perfil != 'empresa':
        return redirect('painel')
    
    # 1. Total de Inscrições Gerais
    total_inscricoes = Inscricao.objects.count()
    
    # 2. Receita Total (Soma os preços dos eventos de inscrições APROVADAS)
    receita_query = Inscricao.objects.filter(status='aprovado', evento__is_pago=True).aggregate(total=Sum('evento__preco'))
    receita_total = receita_query['total'] if receita_query['total'] else 0.00
    
    # 3. Lista de Eventos e quantos inscritos cada um tem
    eventos_stats = Evento.objects.annotate(
        total_inscritos=Count('inscricao')
    ).order_by('data_evento')

    return render(request, 'core/dashboard.html', {
        'total_inscricoes': total_inscricoes,
        'receita_total': receita_total,
        'eventos': eventos_stats
    })
    