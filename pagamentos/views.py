from django.shortcuts import render, redirect
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from .models import Pedido
from eventos.models import Evento, Inscricao

@login_required
def comprar_ingressos(request):
    # Verifica de forma independente o que o usuário já possui
    # IMPORTANTE: Verifique se no seu banco os nomes são exatamente 'Palestra' e 'Minicurso'
    ja_tem_minicurso = Inscricao.objects.filter(
        usuario=request.user, 
        evento__tipo__nome__icontains='Minicurso'
    ).exists()
    
    ja_tem_palestras = Inscricao.objects.filter(
        usuario=request.user, 
        evento__tipo__nome__icontains='Palestra'
    ).exists()

    # Mostra minicursos. DICA: Se não aparecer, verifique o campo 'vagas' no Admin.
    minicursos = Evento.objects.filter(tipo__nome__icontains='Minicurso', vagas__gt=0)

    if request.method == 'POST':
        pacote_escolhido = request.POST.get('pacote')
        minicurso_id = request.POST.get('minicurso_id')
        
        precos = {'palestras': 50.00, 'minicurso': 50.00, 'combo': 80.00}
        valor = precos.get(pacote_escolhido, 0.00)
        
        # --- TRAVAS DE SEGURANÇA CORRIGIDAS ---
        
        # Bloqueia apenas se tentar comprar o que já tem
        if pacote_escolhido == 'palestras' and ja_tem_palestras:
            messages.error(request, 'Você já possui acesso às palestras.')
            return redirect('comprar_ingressos')

        if pacote_escolhido == 'minicurso' and ja_tem_minicurso:
            messages.error(request, 'Você já possui um minicurso.')
            return redirect('comprar_ingressos')

        # Bloqueia Combo se já tiver qualquer parte (Palestras ou Minicurso)
        if pacote_escolhido == 'combo' and (ja_tem_palestras or ja_tem_minicurso):
            messages.error(request, 'Você já possui parte deste combo. Adquira o item restante separadamente.')
            return redirect('comprar_ingressos')

        if pacote_escolhido in ['minicurso', 'combo'] and not minicurso_id:
            messages.error(request, 'Selecione um minicurso para este pacote.')
            return redirect('comprar_ingressos')
            
        minicurso_obj = Evento.objects.filter(id=minicurso_id).first() if minicurso_id else None

        Pedido.objects.create(
            usuario=request.user,
            pacote=pacote_escolhido,
            minicurso_selecionado=minicurso_obj,
            valor_total=valor
        )
        
        messages.success(request, 'Pedido gerado! Prossiga para o pagamento.')
        return redirect('painel')

    return render(request, 'pagamentos/comprar_ingressos.html', {
        'minicursos': minicursos,
        'ja_tem_minicurso': ja_tem_minicurso,
        'ja_tem_palestras': ja_tem_palestras
    })