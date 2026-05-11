from django.shortcuts import render, redirect
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from eventos.models import Evento, Inscricao
from .models import Pedido, Lote

@login_required
def comprar_ingressos(request):
    # =========================================================
    # 1. BUSCA O LOTE ATIVO NO BANCO DE DADOS
    # =========================================================
    lote_ativo = Lote.objects.filter(ativo=True).first()
    
    if not lote_ativo:
        messages.error(request, 'As vendas estão temporariamente suspensas. Nenhum lote ativo.')
        return redirect('painel')

    # =========================================================
    # 2. VERIFICA O QUE O UTILIZADOR JÁ POSSUI
    # =========================================================
    ja_tem_minicurso = Inscricao.objects.filter(
        usuario=request.user, 
        evento__tipo__nome__icontains='mini'
    ).exists()
    
    ja_tem_palestras = Inscricao.objects.filter(
        usuario=request.user, 
        evento__tipo__nome__icontains='palestra'
    ).exists()

    minicursos = Evento.objects.filter(tipo__nome__icontains='mini')

    # =========================================================
    # 3. PROCESSAMENTO DO PEDIDO
    # =========================================================
    if request.method == 'POST':
        pacote_escolhido = request.POST.get('pacote')
        minicurso_id = request.POST.get('minicurso_id')
        
        # Define o valor puxando do Lote Ativo
        valor = 0.00
        if pacote_escolhido == 'palestras':
            valor = lote_ativo.preco_palestras
        elif pacote_escolhido == 'minicurso':
            valor = lote_ativo.preco_minicurso
        elif pacote_escolhido == 'combo':
            valor = lote_ativo.preco_combo
        
        # --- TRAVAS DE SEGURANÇA ---
        if pacote_escolhido == 'palestras' and ja_tem_palestras:
            messages.error(request, 'Você já possui acesso às palestras do evento.')
            return redirect('comprar_ingressos')

        if pacote_escolhido == 'minicurso' and ja_tem_minicurso:
            messages.error(request, 'Você já atingiu o limite de 1 minicurso por pessoa.')
            return redirect('comprar_ingressos')

        if pacote_escolhido == 'combo' and (ja_tem_palestras or ja_tem_minicurso):
            messages.error(request, 'Você já possui parte deste combo. Adquira o item restante separadamente.')
            return redirect('comprar_ingressos')

        if pacote_escolhido in ['minicurso', 'combo'] and not minicurso_id:
            messages.error(request, 'Selecione qual minicurso você deseja cursar.')
            return redirect('comprar_ingressos')
            
        minicurso_obj = Evento.objects.filter(id=minicurso_id).first() if minicurso_id else None
        
        # Trava para garantir que não vende se acabarem as vagas na hora do clique
        if minicurso_obj and minicurso_obj.vagas <= 0:
            messages.error(request, 'Lamentamos, mas as últimas vagas acabaram de ser preenchidas.')
            return redirect('comprar_ingressos')

        # --- CRIAÇÃO DO PEDIDO ---
        Pedido.objects.create(
            usuario=request.user,
            pacote=pacote_escolhido,
            minicurso_selecionado=minicurso_obj,
            valor_total=valor
        )
        
        messages.success(request, 'Pedido gerado com sucesso! Prossiga para o pagamento.')
        return redirect('painel')

    # =========================================================
    # 4. RENDERIZAÇÃO DA LOJA (Enviando o Lote para o HTML)
    # =========================================================
    return render(request, 'pagamentos/comprar_ingressos.html', {
        'minicursos': minicursos,
        'ja_tem_minicurso': ja_tem_minicurso,
        'ja_tem_palestras': ja_tem_palestras,
        'lote': lote_ativo 
    })