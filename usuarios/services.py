import io
from django.urls import reverse
from django.core.mail import send_mail
from django.utils.http import urlsafe_base64_encode
from django.utils.encoding import force_bytes
from django.contrib.auth.tokens import default_token_generator
from django.conf import settings
from django.http import FileResponse

from reportlab.pdfgen import canvas
from reportlab.lib.pagesizes import A4, landscape
from reportlab.lib.units import cm
from reportlab.lib.colors import HexColor

def enviar_email_ativacao(request, usuario):
    uid = urlsafe_base64_encode(force_bytes(usuario.pk))
    token = default_token_generator.make_token(usuario)
    url_relativa = reverse('ativar_conta', kwargs={'uidb64': uid, 'token': token})
    link_ativacao = request.build_absolute_uri(url_relativa)

    assunto = 'Confirme sua inscrição no XI Dia do Leite'
    mensagem = f"""Olá, {usuario.first_name}!\n\nObrigado por se registar no XI Dia do Leite - IFMG Bambuí.\nPara ativar a sua conta, clique no link abaixo:\n\n{link_ativacao}\n\nEquipa de Organização"""
    
    try:
        send_mail(assunto, mensagem, settings.EMAIL_HOST_USER, [usuario.email], fail_silently=False)
        return True
    except Exception as e:
        print(f"Erro ao enviar email: {e}")
        return False

def gerar_pdf_certificado(inscricao):
    buffer = io.BytesIO()
    p = canvas.Canvas(buffer, pagesize=landscape(A4))
    largura, altura = landscape(A4)

    # Design do Certificado
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