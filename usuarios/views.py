import re
from django.shortcuts import render, redirect
from django.contrib.auth import authenticate, login, logout
from django.contrib.auth.decorators import login_required
from django.contrib import messages

# Estes são os imports que faltavam para a função ativar_conta_view não quebrar
from django.utils.http import urlsafe_base64_decode
from django.utils.encoding import force_str
from django.contrib.auth.tokens import default_token_generator

from .models import Usuario
from eventos.models import Inscricao
from pagamentos.models import Pedido

# Importamos os nossos novos serviços
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
    if request.method == 'POST':
        nome = request.POST.get('nome')
        email = request.POST.get('email')
        cpf = request.POST.get('cpf')
        telefone = request.POST.get('telefone')
        senha = request.POST.get('senha')
        confirmacao = request.POST.get('confirmacao')

        if senha != confirmacao:
            messages.error(request, 'As senhas não coincidem.')
            return render(request, 'usuarios/cadastro.html')

        if Usuario.objects.filter(email=email).exists() or Usuario.objects.filter(cpf=cpf).exists():
            messages.error(request, 'E-mail ou CPF já cadastrados.')
            return render(request, 'usuarios/cadastro.html')

        if not cpf_valido(cpf):
            messages.error(request, 'O CPF digitado é inválido.')
            return render(request, 'usuarios/cadastro.html')

        usuario = Usuario.objects.create_user(
            username=email, email=email, password=senha, 
            first_name=nome, cpf=cpf, telefone=telefone, perfil='cliente'
        )
        usuario.is_active = False 
        usuario.save()

        # Agora é o serviço que trata do e-mail
        enviou = enviar_email_ativacao(request, usuario)
        
        if enviou:
            messages.success(request, 'Cadastro realizado! Verifique o link de ativação no seu e-mail.')
        else:
            messages.error(request, 'Erro ao enviar e-mail de ativação. Contacte o suporte.')

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
    if request.method == 'POST':
        email = request.POST.get('email')
        senha = request.POST.get('senha')
        usuario = authenticate(request, username=email, password=senha)
        if usuario is not None:
            login(request, usuario)
            if usuario.is_staff or getattr(usuario, 'perfil', '') == 'empresa':
                return redirect('dashboard')
            return redirect('landing_page')
        messages.error(request, 'E-mail ou senha incorretos.')
    return render(request, 'usuarios/login.html')

def logout_view(request):
    logout(request)
    return redirect('landing_page')

@login_required(login_url='/auth/login/')
def painel_view(request):
    # 1. Busca os ingressos já confirmados
    inscricoes = Inscricao.objects.filter(usuario=request.user).select_related('evento')
    
    # 2. Busca os pedidos pendentes da loja
    pedidos = Pedido.objects.filter(usuario=request.user).order_by('-id')
    
    return render(request, 'usuarios/painel.html', {
        'inscricoes': inscricoes,
        'pedidos': pedidos
    })

@login_required(login_url='/auth/login/')
def perfil_view(request):
    if request.method == 'POST':
        usuario = request.user
        usuario.first_name = request.POST.get('nome')
        usuario.cpf = request.POST.get('cpf')
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
        messages.success(request, 'Dados atualizados com sucesso!')
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

    # Agora é o serviço que trata da criação gráfica do PDF
    return gerar_pdf_certificado(inscricao)