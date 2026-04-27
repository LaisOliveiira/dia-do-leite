import io
import re
from django.shortcuts import render, redirect
from django.urls import reverse
from django.contrib.auth import authenticate, login, logout
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.core.mail import send_mail
from django.utils.http import urlsafe_base64_encode, urlsafe_base64_decode
from django.utils.encoding import force_bytes, force_str
from django.contrib.auth.tokens import default_token_generator
from django.conf import settings
from django.http import FileResponse

# Imports do ReportLab para o PDF
from reportlab.pdfgen import canvas
from reportlab.lib.pagesizes import A4, landscape
from reportlab.lib.units import cm
from reportlab.lib.colors import HexColor

from .models import Usuario
from eventos.models import Inscricao

# FÓRMULA OFICIAL DE VALIDAÇÃO DE CPF
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

        if Usuario.objects.filter(email=email).exists():
            messages.error(request, 'Este e-mail já está em uso.')
            return render(request, 'usuarios/cadastro.html')

        if not cpf_valido(cpf):
            messages.error(request, 'O CPF digitado é inválido.')
            return render(request, 'usuarios/cadastro.html')
            
        if Usuario.objects.filter(cpf=cpf).exists():
            messages.error(request, 'Este CPF já está cadastrado.')
            return render(request, 'usuarios/cadastro.html')

        usuario = Usuario.objects.create_user(
            username=email, email=email, password=senha, 
            first_name=nome, cpf=cpf, telefone=telefone, perfil='cliente'
        )
        usuario.is_active = False 
        usuario.save()

        uid = urlsafe_base64_encode(force_bytes(usuario.pk))
        token = default_token_generator.make_token(usuario)
        
        url_relativa = reverse('ativar_conta', kwargs={'uidb64': uid, 'token': token})
        link_ativacao = request.build_absolute_uri(url_relativa)

        assunto = 'Confirme sua inscrição no XI Dia do Leite'
        mensagem = f"""Olá, {nome}!\n\nObrigado por se registar no XI Dia do Leite - IFMG Bambuí.\nPara ativar a sua conta e ter acesso ao sistema de eventos, clique no link abaixo:\n\n{link_ativacao}\n\nSe você não se cadastrou no nosso sistema, pode ignorar este e-mail.\n\nEquipa de Organização\nSafra Jr."""
        
        try:
            send_mail(assunto, mensagem, settings.EMAIL_HOST_USER, [email], fail_silently=False)
            messages.success(request, 'Cadastro realizado! Enviamos um link de confirmação para o seu e-mail.')
        except Exception as e:
            messages.error(request, 'Conta criada, mas houve um erro ao enviar o e-mail de ativação. Contacte a organização.')
            print(f"Erro ao enviar email: {e}")

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
            if usuario.is_staff or usuario.perfil == 'empresa':
                return redirect('dashboard')
            return redirect('landing_page')
        messages.error(request, 'E-mail ou senha incorretos.')
    return render(request, 'usuarios/login.html')


def logout_view(request):
    logout(request)
    return redirect('landing_page')


@login_required(login_url='/auth/login/')
def painel_view(request):
    inscricoes = Inscricao.objects.filter(usuario=request.user).select_related('evento')
    return render(request, 'usuarios/painel.html', {'inscricoes': inscricoes})


@login_required(login_url='/auth/login/')
def perfil_view(request):
    if request.method == 'POST':
        usuario = request.user
        usuario.first_name = request.POST.get('nome')
        usuario.cpf = request.POST.get('cpf')
        usuario.telefone = request.POST.get('telefone')
        senha = request.POST.get('senha')
        if senha and senha == request.POST.get('confirmacao'):
            usuario.set_password(senha)
            usuario.save()
            return redirect('login')
        usuario.save()
        messages.success(request, 'Dados atualizados!')
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
        messages.error(request, "Certificado não disponível ou acesso negado.")
        return redirect('certificados')

    buffer = io.BytesIO()
    p = canvas.Canvas(buffer, pagesize=landscape(A4))
    largura, altura = landscape(A4)

    p.setStrokeColor(HexColor('#751516'))
    p.setLineWidth(0.5*cm)
    p.rect(0.5*cm, 0.5*cm, largura - 1*cm, altura - 1*cm) 
    p.setLineWidth(0.1*cm)
    p.rect(0.8*cm, 0.8*cm, largura - 1.6*cm, altura - 1.6*cm) 

    p.setFont("Helvetica-BoldOblique", 40)
    p.setFillColor(HexColor('#751516'))
    p.drawCentredString(largura/2, altura - 5*cm, "CERTIFICADO")

    p.setFont("Helvetica", 18)
    p.setFillColor(HexColor('#333333'))
    p.drawCentredString(largura/2, altura - 7*cm, "A Organização do XI Dia do Leite certifica que")

    p.setFont("Helvetica-Bold", 30)
    p.setFillColor(HexColor('#000000'))
    p.drawCentredString(largura/2, altura - 9.5*cm, inscricao.usuario.first_name.upper())

    p.setFont("Helvetica", 16)
    p.setFillColor(HexColor('#333333'))
    data_formatada = inscricao.evento.data_evento.strftime('%d/%m/%Y') if inscricao.evento.data_evento else ''
    texto = f"participou da atividade '{inscricao.evento.titulo}', realizada em {data_formatada},"
    p.drawCentredString(largura/2, altura - 11.5*cm, texto)
    
    texto2 = f"com carga horária total de {inscricao.evento.carga_horaria} horas."
    p.drawCentredString(largura/2, altura - 12.5*cm, texto2)

    p.setFont("Helvetica-Oblique", 12)
    p.drawCentredString(largura/2, 4*cm, "Bambuí - MG, 04 de Julho de 2026.")

    p.setStrokeColor(HexColor('#000000'))
    p.setLineWidth(1)
    p.line(largura/2 - 5*cm, 6*cm, largura/2 + 5*cm, 6*cm)
    p.setFont("Helvetica", 10)
    p.drawCentredString(largura/2, 5.5*cm, "Coordenação Safra Jr.")

    p.showPage()
    p.save()

    buffer.seek(0)
    return FileResponse(buffer, as_attachment=True, filename=f'Certificado_{inscricao.evento.titulo}.pdf')