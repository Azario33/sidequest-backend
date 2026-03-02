from rest_framework import serializers
from .models import User, ProviderProfile, Service, ServiceRequest

class UserSerializer(serializers.ModelSerializer):
    class Meta:
        model = User
        fields = ['id', 'username', 'email', 'role', 'phone']

class ProviderProfileSerializer(serializers.ModelSerializer):
    user = UserSerializer(read_only=True)
    class Meta:
        model = ProviderProfile
        fields = ['id', 'user', 'bio', 'service_area', 'latitude', 'longitude', 'is_available']

class ServiceSerializer(serializers.ModelSerializer):
    provider = ProviderProfileSerializer(read_only=True)
    class Meta:
        model = Service
        fields = ['id', 'provider', 'title', 'description', 'category', 'price', 'created_at']

class ServiceRequestSerializer(serializers.ModelSerializer):
    customer = UserSerializer(read_only=True)
    service = ServiceSerializer(read_only=True)
    customer_id = serializers.PrimaryKeyRelatedField(
        queryset=User.objects.all(), source='customer', write_only=True
    )
    service_id = serializers.PrimaryKeyRelatedField(
        queryset=Service.objects.all(), source='service', write_only=True
    )
    class Meta:
        model = ServiceRequest
        fields = ['id', 'customer', 'customer_id', 'service', 'service_id', 'status', 'message', 'created_at']