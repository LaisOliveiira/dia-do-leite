from django.contrib.auth.models import AbstractUser
from django.db import models

class Usuario(AbstractUser):
    PERFIL_CHOICES = (
        ('admin', 'Administrador'),
        ('empresa', 'Empresa/Gerente'),
        ('cliente', 'Cliente/Pessoa Comum'),
    )
    perfil = models.CharField(max_length=20, choices=PERFIL_CHOICES, default='cliente')
    email = models.EmailField(unique=True)
    
    cpf = models.CharField(max_length=14, unique=True, null=True, blank=True)
    telefone = models.CharField(max_length=20, null=True, blank=True)
    
    # NOVO CAMPO: O "Ingresso Geral" para as palestras
    passaporte_palestras = models.BooleanField(default=False, help_text="Tem acesso livre a todas as palestras?")

    def __str__(self):
        return self.username