from django.db import models
from django.conf import settings
from eventos.models import Evento

class Pedido(models.Model):
    PACOTE_CHOICES = (
        ('palestras', 'Todas as Palestras (R$ 50,00)'),
        ('minicurso', 'Apenas 1 Minicurso (R$ 50,00)'),
        ('combo', 'Combo: Todas as Palestras + 1 Minicurso (R$ 80,00)'),
    )
    
    STATUS_CHOICES = (
        ('pendente', 'Aguardando Pagamento'),
        ('aprovado', 'Pagamento Aprovado'),
        ('recusado', 'Pagamento Recusado'),
    )

    usuario = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE)
    pacote = models.CharField(max_length=20, choices=PACOTE_CHOICES)
    
    # Campo obrigatório se a pessoa escolher "Minicurso" ou "Combo"
    minicurso_selecionado = models.ForeignKey(Evento, on_delete=models.SET_NULL, null=True, blank=True)
    
    valor_total = models.DecimalField(max_digits=8, decimal_places=2)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='pendente')
    
    # Dados para a futura Integração PicPay
    codigo_transacao = models.CharField(max_length=100, blank=True, null=True, unique=True)
    link_pagamento = models.URLField(blank=True, null=True)
    data_criacao = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"Pedido #{self.id} - {self.usuario.first_name} - {self.get_pacote_display()}"