from rest_framework import serializers

from .models import User


class UserSerializer(serializers.ModelSerializer):
    """Сериализатор пользователя."""
    class Meta:
        model = User
        fields = ('id', 'email', 'phone', 'role', 'telegram_username')
        read_only_fields = ('id', 'email', 'phone', 'role', 'telegram_username')


class LoginSerializer(serializers.Serializer):
    """Сериализатор для логина по email и паролю."""

    email = serializers.EmailField()
    password = serializers.CharField(write_only=True)

    def validate(self, attrs):
        email = attrs.get('email')
        password = attrs.get('password')
        if not email or not password:
            raise serializers.ValidationError('Необходимо указать email и пароль.')
        return attrs


class RegisterSerializer(serializers.Serializer):
    """Сериализатор регистрации пользователя."""

    email = serializers.EmailField()
    phone = serializers.CharField(max_length=User._meta.get_field("phone").max_length)
    password = serializers.CharField(write_only=True, min_length=8)

    def validate_email(self, value):
        if User.objects.filter(email__iexact=value).exists():
            raise serializers.ValidationError('Пользователь с таким email уже существует.')
        return value

    def validate_phone(self, value):
        if User.objects.filter(phone=value).exists():
            raise serializers.ValidationError('Пользователь с таким телефоном уже существует.')
        return value

    def create(self, validated_data):
        email = validated_data['email']
        phone = validated_data['phone']
        password = validated_data['password']
        user = User.objects.create_user(email=email, phone=phone, password=password)
        return user


class AuthTokensSerializer(serializers.Serializer):
    """Ответ при успешной аутентификации: пара токенов и данные пользователя."""

    access = serializers.CharField()
    refresh = serializers.CharField()
    user = UserSerializer()


class MagicLinkLoginSerializer(serializers.Serializer):
    """Сериализатор для входа по токену magic link."""

    token = serializers.CharField()


class MagicLinkRequestSerializer(serializers.Serializer):
    """Запрос на отправку письма с magic link."""

    email = serializers.EmailField()
