from rest_framework import serializers
from .models import UserSession, VitalSignLog

class VitalSignLogSerializer(serializers.ModelSerializer):
    class Meta:
        model = VitalSignLog
        fields = '__all__'

class UserSessionSerializer(serializers.ModelSerializer):
    class Meta:
        model = UserSession
        fields = '__all__'
