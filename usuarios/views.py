import re
from django.shortcuts import render, redirect
from django.contrib.auth import authenticate, login, logout
from django.contrib.auth.decorators import login_required
from django.contrib import messages

# Validadores oficiais de E-mail do Django
from django.core.validators import validate_email
from django.core.exceptions import ValidationError

from django.utils.http import urlsafe_base64_decode
from django.utils.encoding import force_str
from django.contrib.auth.tokens import default_token_generator

from .models import Usuario
from eventos.models import Inscricao
from pagamentos.models import Pedido
from .services import enviar_email_ativacao, gerar_pdf_certificado

def cpf_valido(cpf):
    cpf = ''.join(filter(str.isdigit, cpf))
    if len(cpf) != 11 or len(set(cpf)) == 1:
        return False
    for i in range(9, 11):
        value = sum((int(cpf[num]) * ((i+1) - num) for num in range(0, i)))
        digit = ((value * 10) % 11) % 10
        if digit != int(cpf[i]):
            return False
    return True

def cadastro_view(request):
    # 🛡️ PROTEÇÃO: Se a pessoa já estiver logada, redireciona imediatamente
    if request.user.is_authenticated:
        if request.user.is_staff or getattr(request.user, 'perfil', '') == 'empresa':
            return redirect('/admin/') 
        return redirect('landing_page')

    if request.method == 'POST':
        nome = request.POST.get('nome')
        # 🎯 PADRONIZAÇÃO: E-mail sempre em minúsculas e sem espaços
        email = request.POST.get('email', '').strip().lower()
        cpf_digitado = request.POST.get('cpf', '')
        telefone = request.POST.get('telefone')
        senha = request.POST.get('senha')
        confirmacao = request.POST.get('confirmacao')

        cpf = ''.join(filter(str.isdigit, cpf_digitado))

        # 1. Trava anti-vazio
        if not email or not cpf or not senha:
            messages.error(request, 'Preencha todos os campos obrigatórios.')
            return render(request, 'usuarios/cadastro.html')

        # 2. Trava de formato de e-mail
        try:
            validate_email(email)
        except ValidationError:
            messages.error(request, 'O e-mail digitado é inválido. Verifique se o escreveu corretamente (ex: o.seu.nome@gmail.com).')
            return render(request, 'usuarios/cadastro.html')

        if senha != confirmacao:
            messages.error(request, 'As senhas não coincidem.')
            return render(request, 'usuarios/cadastro.html')

        if not cpf_valido(cpf):
            messages.error(request, 'O CPF digitado é inválido.')
            return render(request, 'usuarios/cadastro.html')

        # 3. Verifica se já existe uma conta ATIVA (usando busca insensível a maiúsculas)
        if Usuario.objects.filter(email__iexact=email, is_active=True).exists() or Usuario.objects.filter(cpf=cpf, is_active=True).exists():
            messages.error(request, 'Este E-mail ou CPF já possuem uma conta ativa. Por favor, vá para a página de Login.')
            return render(request, 'usuarios/cadastro.html')
        
        # Apaga contas presas no limbo de ativação
        Usuario.objects.filter(email__iexact=email, is_active=False).delete()
        Usuario.objects.filter(cpf=cpf, is_active=False).delete()

        # 4. Cria o utilizador
        usuario = Usuario.objects.create_user(
            username=email, email=email, password=senha,
            first_name=nome, cpf=cpf, telefone=telefone, perfil='cliente'
        )

        usuario.is_active = False
        usuario.save()

        # Envia e-mail de ativação
        enviou = enviar_email_ativacao(request, usuario)

        if enviou:
            messages.success(request, 'Conta criada com sucesso! Enviámos um e-mail de confirmação. Por favor, verifique a sua caixa de entrada ou a sua pasta de SPAM para ativar a sua conta.')
        else:
            messages.error(request, 'A sua conta foi criada, mas houve um problema ao enviar o e-mail de ativação. Entre em contacto com a organização.')

        return redirect('login')

    return render(request, 'usuarios/cadastro.html')

def ativar_conta_view(request, uidb64, token):
    try:
        uid = force_str(urlsafe_base64_decode(uidb64))
        usuario = Usuario.objects.get(pk=uid)
    except (TypeError, ValueError, OverflowError, Usuario.DoesNotExist):
        usuario = None

    if usuario is not None and default_token_generator.check_token(usuario, token):
        usuario.is_active = True
        usuario.save()
        messages.success(request, 'A sua conta foi ativada com sucesso! Já pode fazer o login.')
        return redirect('login')
    else:
        messages.error(request, 'O link de ativação é inválido ou já expirou.')
        return redirect('login')

def login_view(request):
    # 🛡️ PROTEÇÃO: Se a pessoa já estiver logada, redireciona imediatamente
    if request.user.is_authenticated:
        if request.user.is_staff or getattr(request.user, 'perfil', '') == 'empresa':
            return redirect('/admin/') 
        return redirect('landing_page')

    # Limpeza de mensagens fantasmas
    if request.method == 'GET':
        list(messages.get_messages(request))

    if request.method == 'POST':
        # 🎯 PADRONIZAÇÃO: E-mail sempre em minúsculas e sem espaços
        email_digitado = request.POST.get('email', '').strip().lower()
        senha = request.POST.get('senha')
        
        # 🎯 BUSCA INTELIGENTE: Procura ignorando maiúsculas/minúsculas no banco
        usuario_teste = Usuario.objects.filter(email__iexact=email_digitado).first()

        if usuario_teste:
            # Se a conta existe mas não está ativa
            if not usuario_teste.is_active:
                if usuario_teste.check_password(senha):
                    # Reenvio automático seguro
                    enviar_email_ativacao(request, usuario_teste)
                    messages.error(request, 'A sua conta ainda não foi ativada. Enviámos um novo link de confirmação para o seu e-mail (verifique também o SPAM).')
                else:
                    messages.error(request, 'E-mail ou senha incorretos.')
                return render(request, 'usuarios/login.html')

            # 🎯 AUTENTICAÇÃO SEGURA: Usa o username exato do banco de dados para evitar falhas no Django
            usuario = authenticate(request, username=usuario_teste.username, password=senha)
            
            if usuario is not None:
                login(request, usuario)
                if usuario.is_staff or getattr(usuario, 'perfil', '') == 'empresa':
                    return redirect('/admin/') 
                return redirect('landing_page')
            else:
                messages.error(request, 'E-mail ou senha incorretos.')
        else:
            messages.error(request, 'E-mail ou senha incorretos.')

    return render(request, 'usuarios/login.html')

def logout_view(request):
    logout(request)
    return redirect('landing_page')

@login_required(login_url='/auth/login/')
def painel_view(request):
    inscricoes = Inscricao.objects.filter(
        usuario=request.user,
        status__in=['aprovado', 'gratis']
    ).select_related('evento')
    pedidos = Pedido.objects.filter(usuario=request.user).order_by('-id')

    return render(request, 'usuarios/painel.html', {
        'inscricoes': inscricoes,
        'pedidos': pedidos
    })

@login_required(login_url='/auth/login/')
def perfil_view(request):
    if request.method == 'POST':
        usuario = request.user
        novo_cpf = request.POST.get('cpf')

        if novo_cpf != usuario.cpf:
            if Usuario.objects.filter(cpf=novo_cpf).exists():
                messages.error(request, 'Este CPF já está registado noutra conta.')
                return redirect('perfil')
            if not cpf_valido(novo_cpf):
                messages.error(request, 'O novo CPF digitado é inválido.')
                return redirect('perfil')
            usuario.cpf = novo_cpf

        usuario.first_name = request.POST.get('nome')
        usuario.telefone = request.POST.get('telefone')

        senha_atual = request.POST.get('senha_atual')
        nova_senha = request.POST.get('nova_senha')
        confirmacao = request.POST.get('confirmacao')

        if nova_senha:
            if not usuario.check_password(senha_atual):
                messages.error(request, 'A senha atual está incorreta. Nenhuma alteração foi feita.')
                return redirect('perfil')
            if nova_senha != confirmacao:
                messages.error(request, 'A nova senha e a confirmação não coincidem.')
                return redirect('perfil')
            usuario.set_password(nova_senha)

        usuario.save()
        messages.success(request, 'Dados updated com sucesso!')
        return redirect('perfil')
    return render(request, 'usuarios/perfil.html')

@login_required(login_url='/auth/login/')
def certificados_view(request):
    certificados = Inscricao.objects.filter(usuario=request.user, presenca_confirmada=True)
    return render(request, 'usuarios/certificados.html', {'certificados': certificados})

@login_required(login_url='/auth/login/')
def gerar_certificado_pdf(request, inscricao_id):
    try:
        inscricao = Inscricao.objects.get(
            id=inscricao_id,
            usuario=request.user,
            presenca_confirmada=True
        )
    except Inscricao.DoesNotExist:
        messages.error(request, "Certificado não disponível.")
        return redirect('certificados')

    return gerar_pdf_certificado(inscricao)