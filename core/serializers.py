# serializers.py
# Serializers convert model instances to JSON so the frontend can use the data
# They also handle validation when data is sent from the frontend to the backend

from rest_framework import serializers
from .models import User, ProviderProfile, Service, ServiceRequest, Notification


# Converts User model data to JSON
# Only exposes safe fields - password is never included
class UserSerializer(serializers.ModelSerializer):
    class Meta:
        model = User
        fields = ['id', 'username', 'email', 'role', 'phone']


# Converts ProviderProfile data to JSON
# Nests the full User object inside so the frontend gets all provider info in one response
class ProviderProfileSerializer(serializers.ModelSerializer):
    user = UserSerializer(read_only=True)

    class Meta:
        model = ProviderProfile
        fields = ['id', 'user', 'bio', 'service_area', 'latitude', 'longitude', 'is_available']


# Converts Service data to JSON
# Nests the full ProviderProfile so the frontend knows who offers each service
class ServiceSerializer(serializers.ModelSerializer):
    provider = ProviderProfileSerializer(read_only=True)

    class Meta:
        model = Service
        fields = ['id', 'provider', 'title', 'description', 'category', 'price', 'created_at']


# Converts ServiceRequest data to JSON
# Handles both reading (full nested objects) and writing (IDs only)
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


# Converts Notification data to JSON
class NotificationSerializer(serializers.ModelSerializer):
    class Meta:
        model = Notification
        fields = ['id', 'message', 'is_read', 'request', 'created_at']