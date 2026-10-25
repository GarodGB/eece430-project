from rest_framework import serializers
from .models import User


class UserSerializer(serializers.ModelSerializer):
    pharmacy_name = serializers.CharField(source='pharmacy.name', read_only=True)

    class Meta:
        model = User
        fields = ['id', 'username', 'first_name', 'last_name', 'role', 'pharmacy', 'pharmacy_name']