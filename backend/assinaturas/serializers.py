from rest_framework import serializers

from .models import Assinatura, Plano


class PlanoSerializer(serializers.ModelSerializer):
    class Meta:
        model = Plano
        fields = ('id', 'nome', 'preco')


class AssinaturaSerializer(serializers.ModelSerializer):
    plano = PlanoSerializer(read_only=True)
    esta_ativa = serializers.BooleanField(read_only=True)

    class Meta:
        model = Assinatura
        fields = ('status', 'plano', 'data_expiracao', 'esta_ativa')


class CheckoutSerializer(serializers.Serializer):
    plano_id = serializers.PrimaryKeyRelatedField(
        queryset=Plano.objects.filter(ativo=True),
        source='plano',
    )

    def validate_plano_id(self, plano):
        if not plano.stripe_price_id:
            raise serializers.ValidationError(
                'Plano sem preço configurado no gateway de pagamento.'
            )
        return plano
