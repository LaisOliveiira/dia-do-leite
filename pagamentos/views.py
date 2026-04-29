from django.shortcuts import render, redirect
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from .models import Pedido
from eventos.models import Evento, Inscricao

@login_required
def comprar_ingressos(request):
    # =========================================================
    # 1. VERIFICA O QUE O UTILIZADOR JÁ POSSUI
    # =========================================================
    
    # Verifica de forma INDEPENDENTE as inscrições (usando 'mini' e 'palestra')
    ja_tem_minicurso = Inscricao.objects.filter(
        usuario=request.user, 
        evento__tipo__nome__icontains='mini'
    ).exists()
    
    ja_tem_palestras = Inscricao.objects.filter(
        usuario=request.user, 
        evento__tipo__nome__icontains='palestra'
    ).exists()

    # Traz TODOS os minicursos cadastrados para o HTML tratar as vagas
    minicursos = Evento.objects.filter(tipo__nome__icontains='mini')

    # =========================================================
    # 2. PROCESSAMENTO DO PEDIDO
    # =========================================================
    if request.method == 'POST':
        pacote_escolhido = request.POST.get('pacote')
        minicurso_id = request.POST.get('minicurso_id')
        
        precos = {'palestras': 50.00, 'minicurso': 50.00, 'combo': 80.00}
        valor = precos.get(pacote_escolhido, 0.00)
        
        # --- TRAVAS DE SEGURANÇA CORRIGIDAS ---
        
        # 1. Tenta comprar Palestra, mas já tem? Bloqueia.
        if pacote_escolhido == 'palestras' and ja_tem_palestras:
            messages.error(request, 'Você já possui acesso às palestras do evento.')
            return redirect('comprar_ingressos')

        # 2. Tenta comprar Minicurso, mas já tem? Bloqueia.
        if pacote_escolhido == 'minicurso' and ja_tem_minicurso:
            messages.error(request, 'Você já atingiu o limite de 1 minicurso por pessoa.')
            return redirect('comprar_ingressos')

        # 3. Tenta comprar Combo, mas já tem um dos dois? Bloqueia.
        if pacote_escolhido == 'combo' and (ja_tem_palestras or ja_tem_minicurso):
            messages.error(request, 'Você já possui parte deste combo. Adquira o item restante separadamente de forma avulsa.')
            return redirect('comprar_ingressos')

        # 4. Esqueceu de selecionar o minicurso na lista? Bloqueia.
        if pacote_escolhido in ['minicurso', 'combo'] and not minicurso_id:
            messages.error(request, 'Selecione qual minicurso você deseja cursar.')
            return redirect('comprar_ingressos')
            
        # --- CRIAÇÃO DO PEDIDO ---
        
        minicurso_obj = Evento.objects.filter(id=minicurso_id).first() if minicurso_id else None

        Pedido.objects.create(
            usuario=request.user,
            pacote=pacote_escolhido,
            minicurso_selecionado=minicurso_obj,
            valor_total=valor
        )
        
        messages.success(request, 'Pedido gerado com sucesso! Prossiga para o pagamento.')
        return redirect('painel')

    # =========================================================
    # 3. RENDERIZAÇÃO DA LOJA
    # =========================================================
    context = {
        'minicursos': minicursos,
        'ja_tem_minicurso': ja_tem_minicurso,
        'ja_tem_palestras': ja_tem_palestras
    }
    
    return render(request, 'pagamentos/comprar_ingressos.html', context)