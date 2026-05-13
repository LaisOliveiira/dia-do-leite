from django.db import models
from django.conf import settings
import uuid

class TipoEvento(models.Model):
    nome = models.CharField(max_length=100)
    
    def __str__(self):
        return self.nome

class Evento(models.Model):
    titulo = models.CharField(max_length=255)
    descricao = models.TextField()
    data_evento = models.DateField()
    horario_evento = models.TimeField()
    local = models.CharField(max_length=255)
    responsavel = models.CharField(max_length=255)
    
    tipo = models.ForeignKey(TipoEvento, on_delete=models.RESTRICT)
    is_pago = models.BooleanField(default=False, verbose_name="Evento Pago?")
    preco = models.DecimalField(max_digits=8, decimal_places=2, default=0.00)
    carga_horaria = models.IntegerField(help_text="Horas para sair no certificado", default=0)
    vagas = models.IntegerField(default=0, help_text="Limite de vagas. Ex: 20 para minicursos. Deixe 0 para ilimitado (Palestras).")

    def __str__(self):
        return self.titulo

class Inscricao(models.Model):
    STATUS_PAGAMENTO = (
        ('gratis', 'Gratuito'),
        ('pendente', 'Aguardando Pagamento'),
        ('aprovado', 'Pagamento Aprovado'),
        ('recusado', 'Pagamento Recusado'),
    )

    codigo_ingresso = models.UUIDField(default=uuid.uuid4, editable=False, unique=True)
    
    usuario = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE)
    evento = models.ForeignKey(Evento, on_delete=models.CASCADE)
    
    status = models.CharField(max_length=20, choices=STATUS_PAGAMENTO, default='gratis')
    id_transacao_picpay = models.CharField(max_length=100, blank=True, null=True)
    link_pagamento = models.URLField(blank=True, null=True)
    presenca_confirmada = models.BooleanField(default=False)

    class Meta:
        unique_together = ('usuario', 'evento') 

    def __str__(self):
        return f"{self.usuario.username} - {self.evento.titulo}"

class Edicao(models.Model):
    numero = models.CharField(max_length=20, help_text="Ex: Edição X, Edição IX")
    ano = models.IntegerField()
    ativa = models.BooleanField(default=True)

    def __str__(self):
        return self.numero

class GaleriaFoto(models.Model):
    edicao = models.ForeignKey(Edicao, on_delete=models.CASCADE, related_name='fotos')
    imagem = models.ImageField(upload_to='galeria/%Y/%m/')
    legenda = models.CharField(max_length=255, blank=True, null=True)

    def __str__(self):
        return f"Foto da {self.edicao.numero}"