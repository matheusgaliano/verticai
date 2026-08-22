from django.conf import settings
from django.contrib.auth import get_user_model
from django.contrib.auth.password_validation import validate_password
from django.core.exceptions import ValidationError as DjangoValidationError
from django.db import transaction
from rest_framework import serializers

from editais.serializers import CargoSerializer

from .models import Disponibilidade, Perfil, Preparacao

User = get_user_model()


class UserRegisterSerializer(serializers.ModelSerializer):
    password = serializers.CharField(write_only=True, style={'input_type': 'password'})

    class Meta:
        model = User
        fields = ('id', 'username', 'email', 'password')

    def validate_email(self, email):
        if email and User.objects.filter(email__iexact=email).exists():
            raise serializers.ValidationError('Já existe uma conta com este e-mail.')
        return email

    def validate_password(self, senha):
        # AUTH_PASSWORD_VALIDATORS não roda sozinho em create_user(); aplicamos aqui.
        try:
            validate_password(senha)
        except DjangoValidationError as exc:
            raise serializers.ValidationError(list(exc.messages)) from exc
        return senha

    def create(self, validated_data):
        return User.objects.create_user(
            username=validated_data['username'],
            email=validated_data.get('email', ''),
            password=validated_data['password'],
        )


class DisponibilidadeSerializer(serializers.ModelSerializer):
    class Meta:
        model = Disponibilidade
        fields = ('id', 'dia_semana', 'horas_disponiveis')
        read_only_fields = ('id',)


class PreparacaoSerializer(serializers.ModelSerializer):
    disponibilidades = DisponibilidadeSerializer(many=True, required=False)
    cargo_detalhe = CargoSerializer(source='cargo', read_only=True)

    class Meta:
        model = Preparacao
        fields = (
            'id', 'cargo', 'cargo_detalhe', 'data_inicio',
            'meta_horas_semanais', 'disponibilidades',
        )
        read_only_fields = ('id', 'data_inicio')

    def validate_disponibilidades(self, disponibilidades):
        dias = [item['dia_semana'] for item in disponibilidades]
        if len(dias) != len(set(dias)):
            raise serializers.ValidationError('Há dias da semana repetidos.')
        return disponibilidades

    @transaction.atomic
    def create(self, validated_data):
        disponibilidades = validated_data.pop('disponibilidades', [])
        preparacao = Preparacao.objects.create(**validated_data)
        self._sincronizar_disponibilidades(preparacao, disponibilidades)
        return preparacao

    @transaction.atomic
    def update(self, instance, validated_data):
        # DRF não sabe gravar relações aninhadas sozinho: tratamos explicitamente.
        disponibilidades = validated_data.pop('disponibilidades', None)

        for campo, valor in validated_data.items():
            setattr(instance, campo, valor)
        instance.save()

        if disponibilidades is not None:
            self._sincronizar_disponibilidades(instance, disponibilidades)

        return instance

    @staticmethod
    def _sincronizar_disponibilidades(preparacao, disponibilidades):
        """Substitui a agenda semanal pela informada (semântica de PUT)."""
        preparacao.disponibilidades.all().delete()
        Disponibilidade.objects.bulk_create([
            Disponibilidade(preparacao=preparacao, **item) for item in disponibilidades
        ])


# ---------------------------------------------------------------------------
# Minha Conta
# ---------------------------------------------------------------------------


class MinhaContaSerializer(serializers.ModelSerializer):
    """Perfil do usuário logado: campos nativos do User + campos de Perfil."""

    telefone = serializers.CharField(
        source='perfil.telefone', required=False, allow_blank=True, max_length=20,
    )
    foto_perfil = serializers.ImageField(
        source='perfil.foto_perfil', required=False, allow_null=True, use_url=True,
    )

    class Meta:
        model = User
        fields = ('id', 'username', 'email', 'telefone', 'foto_perfil')

    def validate_email(self, email):
        if email and User.objects.filter(email__iexact=email).exclude(pk=self.instance.pk).exists():
            raise serializers.ValidationError('Já existe uma conta com este e-mail.')
        return email

    def validate_foto_perfil(self, arquivo):
        if arquivo is None:
            return arquivo
        limite = settings.MAX_UPLOAD_AVATAR_SIZE
        if arquivo.size > limite:
            raise serializers.ValidationError(
                f'Imagem maior que o limite de {limite // (1024 * 1024)} MB.'
            )
        return arquivo

    @transaction.atomic
    def update(self, instance, validated_data):
        # DRF não sabe gravar em dois models a partir de um source pontilhado
        # sozinho para write; tratamos o "perfil" explicitamente.
        perfil_data = validated_data.pop('perfil', {})

        for campo, valor in validated_data.items():
            setattr(instance, campo, valor)
        instance.save()

        if perfil_data:
            perfil, _ = Perfil.objects.get_or_create(usuario=instance)
            for campo, valor in perfil_data.items():
                setattr(perfil, campo, valor)
            perfil.save()

        return instance


class TrocarSenhaSerializer(serializers.Serializer):
    senha_atual = serializers.CharField(write_only=True, style={'input_type': 'password'})
    nova_senha = serializers.CharField(write_only=True, style={'input_type': 'password'})

    def validate_senha_atual(self, senha):
        if not self.context['request'].user.check_password(senha):
            raise serializers.ValidationError('Senha atual incorreta.')
        return senha

    def validate_nova_senha(self, senha):
        try:
            validate_password(senha, user=self.context['request'].user)
        except DjangoValidationError as exc:
            raise serializers.ValidationError(list(exc.messages)) from exc
        return senha

    def save(self):
        user = self.context['request'].user
        user.set_password(self.validated_data['nova_senha'])
        user.save(update_fields=['password'])
        return user
