from django.shortcuts import render, redirect
from django.contrib.auth.decorators import login_required
from eventos.models import Evento, Inscricao
from django.db.models import Sum, Count

def landing_page(request):
    eventos_destaque = Evento.objects.all().order_by('data_evento')[:3]
    return render(request, 'core/landing_page.html', {'eventos': eventos_destaque})

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