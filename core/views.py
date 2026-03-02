import re
from rest_framework import viewsets, permissions, status
from rest_framework.decorators import api_view, permission_classes
from rest_framework.response import Response
from rest_framework.permissions import AllowAny
from rest_framework_simplejwt.tokens import RefreshToken
from django.contrib.auth import authenticate
from .models import User, ProviderProfile, Service, ServiceRequest
from .serializers import UserSerializer, ProviderProfileSerializer, ServiceSerializer, ServiceRequestSerializer


@api_view(['GET'])
def test_api(request):
    return Response({
        "message": "Backend is working!",
        "status": "success",
        "project": "SideQuest"
    })


@api_view(['POST'])
@permission_classes([AllowAny])
def register(request):
    username = request.data.get('username')
    email = request.data.get('email')
    password = request.data.get('password')
    role = request.data.get('role', 'customer')

    if not username or not password or not email:
        return Response({'error': 'Please provide username, email and password'}, status=status.HTTP_400_BAD_REQUEST)

    if User.objects.filter(username=username).exists():
        return Response({'error': 'Username already exists'}, status=status.HTTP_400_BAD_REQUEST)

    if len(password) < 8:
        return Response({'error': 'Password must be at least 8 characters.'}, status=status.HTTP_400_BAD_REQUEST)
    if not re.search(r'[A-Z]', password):
        return Response({'error': 'Password must contain at least one uppercase letter.'}, status=status.HTTP_400_BAD_REQUEST)
    if not re.search(r'[0-9]', password):
        return Response({'error': 'Password must contain at least one number.'}, status=status.HTTP_400_BAD_REQUEST)
    if not re.search(r'[!@#$%^&*]', password):
        return Response({'error': 'Password must contain at least one symbol (!@#$%^&*).'}, status=status.HTTP_400_BAD_REQUEST)

    user = User.objects.create_user(username=username, email=email, password=password, role=role)

    if role == 'provider':
        ProviderProfile.objects.create(user=user)

    refresh = RefreshToken.for_user(user)
    return Response({
        'token': str(refresh.access_token),
        'refresh': str(refresh),
        'user': UserSerializer(user).data
    }, status=status.HTTP_201_CREATED)


@api_view(['POST'])
@permission_classes([AllowAny])
def login(request):
    username = request.data.get('username')
    password = request.data.get('password')

    user = authenticate(username=username, password=password)

    if not user:
        return Response({'error': 'Invalid credentials'}, status=status.HTTP_401_UNAUTHORIZED)

    refresh = RefreshToken.for_user(user)
    return Response({
        'token': str(refresh.access_token),
        'refresh': str(refresh),
        'user': UserSerializer(user).data
    })


@api_view(['GET'])
def get_current_user(request):
    return Response(UserSerializer(request.user).data)


@api_view(['POST'])
def create_request(request):
    customer = request.user

    if customer.role == 'provider':
        return Response({'error': 'Providers cannot request services.'}, status=status.HTTP_400_BAD_REQUEST)

    service_id = request.data.get('service')
    message = request.data.get('message', '')

    try:
        service = Service.objects.get(id=service_id)
    except Service.DoesNotExist:
        return Response({'error': 'Service not found.'}, status=status.HTTP_404_NOT_FOUND)

    if service.provider.user == customer:
        return Response({'error': 'You cannot request your own service.'}, status=status.HTTP_400_BAD_REQUEST)

    if ServiceRequest.objects.filter(customer=customer, service=service, status__in=['pending', 'accepted']).exists():
        return Response({'error': 'You already have an active request for this service.'}, status=status.HTTP_400_BAD_REQUEST)

    service_request = ServiceRequest.objects.create(
        customer=customer,
        service=service,
        message=message
    )

    return Response(ServiceRequestSerializer(service_request).data, status=status.HTTP_201_CREATED)


class UserViewSet(viewsets.ModelViewSet):
    queryset = User.objects.all()
    serializer_class = UserSerializer


class ProviderProfileViewSet(viewsets.ModelViewSet):
    queryset = ProviderProfile.objects.all()
    serializer_class = ProviderProfileSerializer


class ServiceViewSet(viewsets.ModelViewSet):
    queryset = Service.objects.all()
    serializer_class = ServiceSerializer
    permission_classes = [permissions.IsAuthenticatedOrReadOnly]


class ServiceRequestViewSet(viewsets.ModelViewSet):
    queryset = ServiceRequest.objects.all()
    serializer_class = ServiceRequestSerializer
    permission_classes = [permissions.IsAuthenticated]