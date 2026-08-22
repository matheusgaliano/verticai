from django.contrib.auth import get_user_model
from django.contrib.auth.password_validation import validate_password
from django.core.exceptions import ValidationError as DjangoValidationError
from django.db import transaction
from rest_framework import serializers

from editais.serializers import CargoSerializer

from .models import Disponibilidade, Preparacao

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
