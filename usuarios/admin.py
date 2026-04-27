from django.contrib import admin
from django.contrib.auth.admin import UserAdmin
from .models import Usuario

# Registra o nosso usuário customizado com os poderes do Django Admin
admin.site.register(Usuario, UserAdmin)