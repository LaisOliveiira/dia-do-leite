from django.db import models
from django.conf import settings
from eventos.models import Evento
from django.contrib.auth.models import User

class Lote(models.Model):
    nome = models.CharField(max_length=50, help_text="Ex: Lote 1, Lote 2, Último Lote")
    preco_palestras = models.DecimalField(max_digits=8, decimal_places=2, verbose_name="Preço Passaporte Palestras")
    preco_minicurso = models.DecimalField(max_digits=8, decimal_places=2, verbose_name="Preço Minicurso Avulso")
    preco_combo = models.DecimalField(max_digits=8, decimal_places=2, verbose_name="Preço Combo (Palestras + 1 Minicurso)")
    ativo = models.BooleanField(default=False, help_text="Marque para ativar este lote. Os outros serão desativados automaticamente.")

    class Meta:
        verbose_name = "Lote de Venda"
        verbose_name_plural = "Lotes de Venda"

    def save(self, *args, **kwargs):
        # Mágica: Se este lote está a ser salvo como ativo, desativa todos os outros!
        if self.ativo:
            Lote.objects.exclude(pk=self.pk).update(ativo=False)
        super().save(*args, **kwargs)

    def __str__(self):
        status = "🟢 ATIVO" if self.ativo else "🔴 Inativo"
        return f"{self.nome} - {status}"

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