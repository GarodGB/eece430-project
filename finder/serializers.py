from rest_framework import serializers
from accounts.models import Pharmacy


class PharmacyPublicSerializer(serializers.ModelSerializer):
    class Meta:
        model = Pharmacy
        fields = ['id', 'name', 'address', 'phone', 'latitude', 'longitude']
