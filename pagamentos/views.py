from django.shortcuts import render, redirect
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from eventos.models import Evento, Inscricao
from .models import Pedido, Lote
import mercadopago

@login_required
def comprar_ingressos(request):
    lote_ativo = Lote.objects.filter(ativo=True).first()
    
    if not lote_ativo:
        messages.error(request, 'As vendas estão suspensas. Nenhum lote ativo.')
        return redirect('painel')

    ja_tem_minicurso = Inscricao.objects.filter(usuario=request.user, evento__tipo__nome__icontains='mini').exists()
    ja_tem_palestras = Inscricao.objects.filter(usuario=request.user, evento__tipo__nome__icontains='palestra').exists()
    minicursos = Evento.objects.filter(tipo__nome__icontains='mini')

    if request.method == 'POST':
        pacote_escolhido = request.POST.get('pacote')
        minicurso_id = request.POST.get('minicurso_id')
        
        valor = 0.00
        if pacote_escolhido == 'palestras':
            valor = lote_ativo.preco_palestras
        elif pacote_escolhido == 'minicurso':
            valor = lote_ativo.preco_minicurso
        elif pacote_escolhido == 'combo':
            valor = lote_ativo.preco_combo
        
        if pacote_escolhido == 'palestras' and ja_tem_palestras:
            messages.error(request, 'Você já possui acesso às palestras.')
            return redirect('comprar_ingressos')

        if pacote_escolhido == 'minicurso' and ja_tem_minicurso:
            messages.error(request, 'Você já atingiu o limite de minicursos.')
            return redirect('comprar_ingressos')

        if pacote_escolhido == 'combo' and (ja_tem_palestras or ja_tem_minicurso):
            messages.error(request, 'Você já possui parte deste combo.')
            return redirect('comprar_ingressos')

        if pacote_escolhido in ['minicurso', 'combo'] and not minicurso_id:
            messages.error(request, 'Selecione o minicurso.')
            return redirect('comprar_ingressos')
            
        minicurso_obj = Evento.objects.filter(id=minicurso_id).first() if minicurso_id else None
        
        if minicurso_obj and minicurso_obj.vagas <= 0:
            messages.error(request, 'As vagas acabaram de ser preenchidas.')
            return redirect('comprar_ingressos')

        pedido = Pedido.objects.create(
            usuario=request.user,
            pacote=pacote_escolhido,
            minicurso_selecionado=minicurso_obj,
            valor_total=valor,
            status='pendente'
        )

        try:
            sdk = mercadopago.SDK("TEST-ACCESS-TOKEN") 
            payment_data = {
                "transaction_amount": float(valor),
                "description": f"Inscrição Dia do Leite - Pedido #{pedido.id}",
                "payment_method_id": "pix",
                "payer": {
                    "email": request.user.email,
                    "first_name": request.user.first_name,
                    "identification": {"type": "CPF", "number": request.user.cpf}
                }
            }
            payment_response = sdk.payment().create(payment_data)
            payment = payment_response["response"]

            if "point_of_interaction" in payment:
                pedido.qr_code_pix = payment["point_of_interaction"]["transaction_data"]["qr_code"]
                pedido.id_transacao_mp = payment["id"]
                pedido.save()
                messages.success(request, 'PIX gerado! Efetue o pagamento no painel.')
        except Exception:
            messages.warning(request, 'Pedido reservado! O PIX será gerado em instantes.')

        return redirect('painel')

    return render(request, 'pagamentos/comprar_ingressos.html', {
        'minicursos': minicursos, 'ja_tem_minicurso': ja_tem_minicurso,
        'ja_tem_palestras': ja_tem_palestras, 'lote': lote_ativo 
    })