from django.db import models
from django.conf import settings
from eventos.models import Evento, Inscricao
from django.contrib.auth.models import User
from django.db.models.signals import post_save
from django.dispatch import receiver

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
        ('palestras', 'Palestras'),
        ('minicurso', 'Minicurso Avulso'),
        ('combo', 'Combo Completo (Palestras + Minicurso)'),
    )
    
    STATUS_CHOICES = (
        ('pendente', 'Aguardando Pagamento'),
        ('aprovado', 'Pagamento Aprovado'),
        ('recusado', 'Pagamento Recusado'),
        ('em_analise', 'Em Análise'), 
    )

    usuario = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE)
    pacote = models.CharField(max_length=20, choices=PACOTE_CHOICES)
    minicurso_selecionado = models.ForeignKey(Evento, on_delete=models.SET_NULL, null=True, blank=True)
    valor_total = models.DecimalField(max_digits=8, decimal_places=2)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='pendente')
    codigo_transacao = models.CharField(max_length=100, blank=True, null=True, unique=True)
    link_pagamento = models.URLField(blank=True, null=True)
    data_criacao = models.DateTimeField(auto_now_add=True)
    
    # CAMPOS DO MERCADO PAGO
    qr_code_pix = models.TextField(blank=True, null=True)
    id_transacao_mp = models.CharField(max_length=255, blank=True, null=True)
    
    # FOTO DO PRODUTOR RURAL E PIX MANUAL
    comprovante_produtor = models.FileField(upload_to='comprovantes_produtor/', null=True, blank=True)
    comprovante_pix = models.FileField(upload_to='comprovantes_pix/', null=True, blank=True)

    def __str__(self):
        return f"Pedido #{self.id} - {self.usuario.first_name} - {self.get_pacote_display()}"


# --- GATILHO (SIGNAL) QUE GERA OS INGRESSOS AUTOMATICAMENTE ---
@receiver(post_save, sender=Pedido)
def gerar_inscricao_apos_aprovacao(sender, instance, **kwargs):
    # Verifica se o pedido foi alterado para 'aprovado'
    if instance.status == 'aprovado':
        
        # 1. Gera Inscrição para Palestras (se for pacote palestras ou combo)
        if instance.pacote in ['palestras', 'combo']:
            palestras = Evento.objects.filter(tipo__nome__icontains='palestra')
            for palestra in palestras:
                Inscricao.objects.get_or_create(usuario=instance.usuario, evento=palestra)

        # 2. Gera Inscrição para Minicurso (se for pacote minicurso ou combo)
        if instance.pacote in ['minicurso', 'combo'] and instance.minicurso_selecionado:
            inscricao, criada = Inscricao.objects.get_or_create(
                usuario=instance.usuario,
                evento=instance.minicurso_selecionado
            )
            # Desconta a vaga do minicurso APENAS na hora que a inscrição é criada pela 1ª vez
            if criada and instance.minicurso_selecionado.vagas > 0:
                instance.minicurso_selecionado.vagas -= 1
                instance.minicurso_selecionado.save()