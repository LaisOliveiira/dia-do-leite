from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib.admin.views.decorators import staff_member_required
from django.contrib import messages
from django.contrib.auth import get_user_model
from eventos.models import Evento, Inscricao
from .models import Pedido, Lote
import mercadopago
import json
import os
import csv
from django.http import JsonResponse, HttpResponse
from django.views.decorators.csrf import csrf_exempt
from django.conf import settings
from django.db import transaction
from django.core.mail import send_mail

@login_required
def comprar_ingressos(request):
    lote_ativo = Lote.objects.filter(ativo=True).first()

    if not lote_ativo:
        # <-- MENSAGEM ATUALIZADA AQUI -->
        messages.warning(request, 'Vendas online encerradas! Garanta o seu ingresso diretamente na portaria do evento.')
        return redirect('painel')

    ja_tem_minicurso = Inscricao.objects.filter(usuario=request.user, evento__tipo__nome__icontains='mini').exists()
    ja_tem_palestras = Inscricao.objects.filter(usuario=request.user, evento__tipo__nome__icontains='palestra').exists()
    minicursos = Evento.objects.filter(tipo__nome__icontains='mini')

    if request.method == 'POST':
        pacote_escolhido = request.POST.get('pacote')
        minicurso_id = request.POST.get('minicurso_id')

        # 🛡️ PROTEÇÃO CONTRA PEDIDOS DUPLICADOS (NÃO APAGA NADA, APENAS BLOQUEIA)
        pedido_existente = Pedido.objects.filter(usuario=request.user, status__in=['pendente', 'em_analise']).first()
        if pedido_existente:
            if pedido_existente.status == 'em_analise':
                messages.warning(request, 'Você já possui um pedido em análise. Por favor, aguarde a aprovação.')
            elif pedido_existente.status == 'pendente':
                messages.warning(request, 'Você já possui um pedido pendente. Por favor, finalize o pagamento no seu painel.')
            return redirect('painel')

        # 🛡️ TRAVA PARA NÃO ESQUECEREM O COMPROVANTE PIX
        forma_pagamento = request.POST.get('forma_pagamento')
        comprovante_pix = request.FILES.get('comprovante_pix')
        comprovante_produtor = request.FILES.get('comprovante_produtor')

        if forma_pagamento == 'pix_manual' and not comprovante_pix:
            messages.error(request, 'Você esqueceu de anexar o comprovante do PIX!')
            return redirect('comprar_ingressos')

        valor = 0.00

        # --- LÓGICA DE PREÇOS DO LOTE ATIVO (LOTE NORMAL) ---
        if pacote_escolhido == 'combo':
            valor = lote_ativo.preco_combo
        elif pacote_escolhido == 'palestras':
            valor = lote_ativo.preco_palestras
        elif pacote_escolhido == 'minicurso':
            valor = lote_ativo.preco_minicurso
        # --------------------------------------------------

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

        # 🛡️ PROTEÇÃO CONTRA MANIPULAÇÃO DE ID
        minicurso_obj = None
        if minicurso_id:
            minicurso_obj = minicursos.filter(id=minicurso_id).first()
            if not minicurso_obj:
                messages.error(request, 'O minicurso selecionado é inválido ou não está disponível.')
                return redirect('comprar_ingressos')

        if minicurso_obj and minicurso_obj.vagas <= 0:
            messages.error(request, 'As vagas acabaram de ser preenchidas.')
            return redirect('comprar_ingressos')

        # 🛡️ VALIDAÇÃO DE SEGURANÇA DE UPLOAD (PRODUTOR RURAL E PIX MANUAL)
        extensoes_permitidas = ['.pdf', '.jpg', '.jpeg', '.png']
        tipos_permitidos = ['application/pdf', 'image/jpeg', 'image/png']

        # Valida o arquivo do produtor, se existir
        if comprovante_produtor:
            extensao_prod = os.path.splitext(comprovante_produtor.name)[1].lower()
            if extensao_prod not in extensoes_permitidas or comprovante_produtor.content_type not in tipos_permitidos:
                messages.error(request, 'Arquivo de Produtor Rural inválido! Envie apenas PDF ou imagens (JPG, PNG).')
                return redirect('comprar_ingressos')
            if comprovante_produtor.size > 5 * 1024 * 1024:
                messages.error(request, 'O arquivo de Produtor Rural é muito grande! Máximo de 5MB.')
                return redirect('comprar_ingressos')

        # Valida o arquivo do PIX, se existir
        if comprovante_pix:
            extensao_pix = os.path.splitext(comprovante_pix.name)[1].lower()
            if extensao_pix not in extensoes_permitidas or comprovante_pix.content_type not in tipos_permitidos:
                messages.error(request, 'Comprovante PIX inválido! Envie apenas PDF ou imagens (JPG, PNG).')
                return redirect('comprar_ingressos')
            if comprovante_pix.size > 5 * 1024 * 1024:
                messages.error(request, 'O comprovante PIX é muito grande! Máximo de 5MB.')
                return redirect('comprar_ingressos')

        # Criação segura do registro
        pedido = Pedido.objects.create(
            usuario=request.user,
            pacote=pacote_escolhido,
            minicurso_selecionado=minicurso_obj,
            valor_total=valor,
            status='pendente'
        )

        # --- INTERCEPTOR DE ANÁLISE MANUAL (MENSAGENS TOTALMENTE SEPARADAS) ---
        if comprovante_produtor or comprovante_pix:
            mensagem_sucesso = ""

            # Se enviou os dois juntos
            if comprovante_produtor and comprovante_pix:
                pedido.comprovante_produtor = comprovante_produtor
                pedido.comprovante_pix = comprovante_pix
                mensagem_sucesso = 'Comprovantes de Produtor e PIX recebidos! Em breve aprovaremos seu pedido.'

            # Se enviou apenas o Produtor
            elif comprovante_produtor:
                pedido.comprovante_produtor = comprovante_produtor
                mensagem_sucesso = 'Documento de Produtor Rural enviado com sucesso! Aguarde a validação.'

            # Se enviou apenas o PIX
            elif comprovante_pix:
                pedido.comprovante_pix = comprovante_pix
                mensagem_sucesso = 'Comprovante PIX enviado! Estamos conferindo o seu pagamento.'

            pedido.status = 'em_analise'
            pedido.save()
            messages.success(request, mensagem_sucesso)
            return redirect('painel')

        # === INTEGRAÇÃO COM MERCADO PAGO (Só roda se não houver anexo) ===
        try:
            sdk = mercadopago.SDK(settings.MERCADO_PAGO_ACCESS_TOKEN)

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

            request_options = mercadopago.config.RequestOptions()
            request_options.custom_headers = {
                "x-idempotency-key": f"pedido-{pedido.id}"
            }

            payment_response = sdk.payment().create(
                payment_data,
                request_options
            )
            payment = payment_response["response"]

            if "point_of_interaction" in payment:
                pedido.qr_code_pix = payment["point_of_interaction"]["transaction_data"]["qr_code"]
                pedido.id_transacao_mp = payment["id"]
                pedido.save()

                try:
                    subject = 'Inscrição realizada com sucesso - XI Dia do Leite'
                    nome_usuario = request.user.first_name or request.user.username
                    plain_message = (
                        f"Olá, {nome_usuario}!\n\n"
                        f"Sua inscrição no XI Dia do Leite foi realizada com sucesso!\n"
                        f"O seu código PIX copia e cola já foi gerado. Acesse o seu painel no site para efetuar o pagamento e garantir seus ingressos.\n\n"
                        f"Atenciosamente,\n"
                        f"Equipe de Organização - XI Dia do Leite"
                    )

                    send_mail(
                        subject,
                        plain_message,
                        settings.EMAIL_HOST_USER,
                        [request.user.email],
                        fail_silently=True
                    )
                except Exception as e_mail:
                    print(f"AVISO - Bloqueio de e-mail evitado: {str(e_mail)}")

                messages.success(request, 'PIX gerado! Efetue o pagamento no painel.')
            else:
                messages.warning(request, 'Pedido reservado! O PIX será gerado em instantes.')

        except Exception as e:
            messages.warning(request, 'Pedido reservado! O PIX será gerado em instantes.')

        return redirect('painel')

    return render(request, 'pagamentos/comprar_ingressos.html', {
        'minicursos': minicursos, 'ja_tem_minicurso': ja_tem_minicurso,
        'ja_tem_palestras': ja_tem_palestras, 'lote': lote_ativo
    })

@csrf_exempt
def mercado_pago_webhook(request):
    if request.method == 'POST':
        try:
            dados = json.loads(request.body)
            id_pagamento_mp = dados.get('data', {}).get('id') or dados.get('id')

            if not id_pagamento_mp and 'resource' in dados:
                resource_str = str(dados['resource'])
                id_pagamento_mp = resource_str.split('/')[-1]

            if id_pagamento_mp:
                pedido = Pedido.objects.filter(id_transacao_mp=id_pagamento_mp).first()

                if pedido:
                    sdk = mercadopago.SDK(settings.MERCADO_PAGO_ACCESS_TOKEN)
                    payment_info = sdk.payment().get(id_pagamento_mp)

                    if payment_info["status"] == 200:
                        status_pagamento = payment_info["response"]["status"]

                        if status_pagamento == "approved" and pedido.status != "aprovado":
                            with transaction.atomic():
                                pedido.status = "aprovado"
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

            return JsonResponse({'status': 'ok'}, status=200)

        except Exception as e:
            return JsonResponse({'erro': 'Erro processado'}, status=200)

    return JsonResponse({'erro': 'Método não permitido'}, status=405)

@staff_member_required
def gerador_crachas(request):
    tipo = request.GET.get('tipo', 'participantes')
    crachas = []

    if tipo == 'organizadores':
        User = get_user_model()
        organizadores = User.objects.filter(is_staff=True)
        for org in organizadores:
            nome_cracha = f"{org.first_name} {org.last_name}".strip()
            if not nome_cracha:
                nome_cracha = org.username

            crachas.append({
                'nome': nome_cracha,
                'cargo': 'ORGANIZADOR'
            })
    else:
        pedidos_aprovados = Pedido.objects.filter(
            status__in=['aprovado', 'approved', 'Aprovado', 'APPROVED']
        ).select_related('usuario')

        for pedido in pedidos_aprovados:
            nome_cracha = f"{pedido.usuario.first_name} {pedido.usuario.last_name}".strip()
            if not nome_cracha:
                nome_cracha = pedido.usuario.username

            crachas.append({
                'nome': nome_cracha,
                'cargo': 'PARTICIPANTE'
            })

    crachas.sort(key=lambda x: x['nome'].lower())

    return render(request, 'pagamentos/crachas.html', {'crachas': crachas, 'tipo': tipo})

# <-- NOVA FUNÇÃO DA LISTA DE ASSINATURAS (AGRUPADA) -->
@staff_member_required
def lista_assinaturas(request):
    pedidos_aprovados = Pedido.objects.filter(
        status__in=['aprovado', 'approved', 'Aprovado', 'APPROVED']
    ).select_related('usuario', 'minicurso_selecionado')

    grupos = {
        'Acesso Geral (Palestras)': []
    }

    for pedido in pedidos_aprovados:
        nome = f"{pedido.usuario.first_name} {pedido.usuario.last_name}".strip()
        if not nome:
            nome = pedido.usuario.username

        # Se comprou palestras ou combo, vai pra lista geral
        if pedido.pacote in ['palestras', 'combo']:
            grupos['Acesso Geral (Palestras)'].append(nome)

        # Se comprou minicurso ou combo, cria/vai pra lista específica do minicurso
        if pedido.pacote in ['minicurso', 'combo'] and pedido.minicurso_selecionado:
            nome_mini = f"Minicurso: {pedido.minicurso_selecionado.titulo}"
            if nome_mini not in grupos:
                grupos[nome_mini] = []
            grupos[nome_mini].append(nome)

    # Limpar duplicatas, ordenar e formatar para o template
    listas_finais = {}
    for titulo, nomes in grupos.items():
        nomes_unicos = list(set(nomes)) # Remove nomes duplicados caso a pessoa tenha mais de um pedido aprovado
        nomes_unicos.sort(key=lambda x: x.lower()) # Ordena A-Z

        if nomes_unicos: # Só cria a tabela se tiver pessoas nela
            listas_finais[titulo] = nomes_unicos

    return render(request, 'pagamentos/lista_assinaturas.html', {'listas': listas_finais})


# <-- NOVA FUNÇÃO: RELATÓRIO DE PRESENÇAS CONFIRMADAS (NOME, CPF, EMAIL, ATIVIDADES) -->
@staff_member_required
def baixar_relatorio_cpf(request):
    # Prepara o arquivo para baixar
    response = HttpResponse(content_type='text/csv')
    response['Content-Disposition'] = 'attachment; filename="relatorio_presenca_confirmada.csv"'

    # Adiciona isso para o Excel reconhecer os acentos
    response.write(u'\ufeff'.encode('utf8'))

    # Cria a planilha separada por ponto e vírgula com a nova coluna
    writer = csv.writer(response, delimiter=';')
    writer.writerow(['Nome Completo', 'CPF', 'E-mail', 'Atividades Confirmadas na Portaria'])

    # Puxa as inscrições que foram bipadas (presenca_confirmada=True)
    inscricoes_presentes = Inscricao.objects.filter(
        presenca_confirmada=True
    ).select_related('usuario', 'evento', 'evento__tipo')

    # Dicionário para agrupar as coisas de uma mesma pessoa numa linha só
    participantes = {}

    for inscricao in inscricoes_presentes:
        u_id = inscricao.usuario.id

        # Se é a primeira vez que o sistema vê a pessoa, cria a linha dela
        if u_id not in participantes:
            nome = f"{inscricao.usuario.first_name} {inscricao.usuario.last_name}".strip()
            if not nome:
                nome = inscricao.usuario.username

            participantes[u_id] = {
                'nome': nome,
                'cpf': getattr(inscricao.usuario, 'cpf', 'Não cadastrado'),
                'email': getattr(inscricao.usuario, 'email', 'Não cadastrado'),
                'atividades': []
            }

        # Descobre o que ela fez e adiciona na lista de atividades dela
        tipo_nome = inscricao.evento.tipo.nome.lower()
        if 'mini' in tipo_nome:
            participantes[u_id]['atividades'].append(f"Minicurso: {inscricao.evento.titulo}")
        elif 'palestra' in tipo_nome:
            participantes[u_id]['atividades'].append("Palestras")
        else:
            participantes[u_id]['atividades'].append(inscricao.evento.titulo)

    # Agora escreve todo mundo no Excel
    for u_id, dados in participantes.items():
        # Remove nomes duplicados (caso tenha bipado mais de uma palestra, etc)
        atividades_unicas = list(set(dados['atividades']))

        # Ordena para ficar bonito: Palestras primeiro
        atividades_unicas.sort(reverse=True)

        # Junta os textos. Ex: "Palestras + Minicurso: Queijos"
        texto_atividades = " + ".join(atividades_unicas)

        writer.writerow([dados['nome'], dados['cpf'], dados['email'], texto_atividades])

    return response