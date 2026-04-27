from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from .models import Evento, Inscricao
from .models import Evento, TipoEvento
import requests

@login_required(login_url='/auth/login/')
def criar_evento_view(request):
    # TRAVA DE SEGURANÇA: Só entra se for Admin (Staff) ou Perfil Empresa
    if not (request.user.is_staff or getattr(request.user, 'perfil', '') == 'empresa'):
        messages.error(request, 'Acesso negado. Apenas a organização pode criar eventos.')
        return redirect('landing_page')

    if request.method == 'POST':
        titulo = request.POST.get('titulo')
        descricao = request.POST.get('descricao')
        tipo_id = request.POST.get('tipo')
        data_evento = request.POST.get('data_evento')
        horario_evento = request.POST.get('horario_evento')
        local = request.POST.get('local')
        preco = request.POST.get('preco')
        carga_horaria = request.POST.get('carga_horaria')

        # Busca o tipo de evento (Palestra ou Minicurso) no banco
        tipo = TipoEvento.objects.get(id=tipo_id)

        # Se o preço vier vazio (evento gratuito), gravamos como 0.0
        if not preco:
            preco = 0.0

        # Salva o evento no Banco de Dados!
        Evento.objects.create(
            titulo=titulo,
            descricao=descricao,
            tipo=tipo,
            data_evento=data_evento,
            horario_evento=horario_evento,
            local=local,
            preco=preco,
            carga_horaria=carga_horaria
        )
        
        messages.success(request, 'Evento criado e publicado com sucesso!')
        # Redireciona de volta para a Home para ver o evento novo lá
        return redirect('landing_page') 

    # Se for GET, apenas abre a página enviando os tipos de evento para preencher o <select>
    tipos = TipoEvento.objects.all()
    return render(request, 'eventos/criar_evento.html', {'tipos': tipos})

@login_required(login_url='/auth/login/')
def inscrever_evento_view(request, evento_id):
    evento = get_object_or_404(Evento, id=evento_id)

    # 1. Verifica se o usuário já está inscrito para evitar duplicidade
    if Inscricao.objects.filter(usuario=request.user, evento=evento).exists():
        messages.info(request, f'Você já possui uma inscrição para: {evento.titulo}')
        return redirect('painel')

    # 2. Se o evento for GRATUITO
    if not evento.is_pago:
        Inscricao.objects.create(
            usuario=request.user, 
            evento=evento, 
            status='aprovado'
        )
        messages.success(request, 'Inscrição gratuita confirmada com sucesso!')
        return redirect('painel')

    # 3. Se o evento for PAGO (Integração PicPay)
    else:
        # Cria a inscrição como pendente
        inscricao = Inscricao.objects.create(
            usuario=request.user, 
            evento=evento, 
            status='pendente'
        )
        
        # --- LÓGICA DO PICPAY ---
        # Como ainda não temos os tokens da Safra Jr., vamos simular o link de pagamento.
        # Quando tivermos os tokens, substituiremos este bloco pela chamada real à API.
        
        link_simulado = f"https://picpay.me/safrajr/{evento.preco}"
        inscricao.link_pagamento = link_simulado
        inscricao.save()

        messages.warning(request, 'Inscrição reservada! Por favor, conclua o pagamento para liberar seu QR Code.')
        return redirect('painel')