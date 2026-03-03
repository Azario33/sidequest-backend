# views.py
# This file contains all the API logic for SideQuest
# Each function or class here handles a specific API request from the frontend

import re
from rest_framework import viewsets, permissions, status
from rest_framework.decorators import api_view, permission_classes
from rest_framework.response import Response
from rest_framework.permissions import AllowAny
from rest_framework_simplejwt.tokens import RefreshToken
from django.contrib.auth import authenticate
from .models import User, ProviderProfile, Service, ServiceRequest
from .serializers import UserSerializer, ProviderProfileSerializer, ServiceSerializer, ServiceRequestSerializer


# Simple test endpoint to confirm the backend is running
@api_view(['GET'])
def test_api(request):
    return Response({
        "message": "Backend is working!",
        "status": "success",
        "project": "SideQuest"
    })


# Handles new user registration for both customers and providers
# Validates all fields and password strength before creating the account
@api_view(['POST'])
@permission_classes([AllowAny])
def register(request):
    username = request.data.get('username')
    email = request.data.get('email')
    password = request.data.get('password')
    role = request.data.get('role', 'customer')

    # Check all required fields are present
    if not username or not password or not email:
        return Response({'error': 'Please provide username, email and password'}, status=status.HTTP_400_BAD_REQUEST)

    # Check username is not already taken
    if User.objects.filter(username=username).exists():
        return Response({'error': 'Username already exists'}, status=status.HTTP_400_BAD_REQUEST)

    # Password strength validation
    if len(password) < 8:
        return Response({'error': 'Password must be at least 8 characters.'}, status=status.HTTP_400_BAD_REQUEST)
    if not re.search(r'[A-Z]', password):
        return Response({'error': 'Password must contain at least one uppercase letter.'}, status=status.HTTP_400_BAD_REQUEST)
    if not re.search(r'[0-9]', password):
        return Response({'error': 'Password must contain at least one number.'}, status=status.HTTP_400_BAD_REQUEST)
    if not re.search(r'[!@#$%^&*]', password):
        return Response({'error': 'Password must contain at least one symbol (!@#$%^&*).'}, status=status.HTTP_400_BAD_REQUEST)

    # Create the user account
    user = User.objects.create_user(username=username, email=email, password=password, role=role)

    # If the user is a provider, automatically create a profile for them
    if role == 'provider':
        ProviderProfile.objects.create(user=user)

    # Generate JWT tokens and return them with the user data
    refresh = RefreshToken.for_user(user)
    return Response({
        'token': str(refresh.access_token),
        'refresh': str(refresh),
        'user': UserSerializer(user).data
    }, status=status.HTTP_201_CREATED)


# Handles user login and returns JWT tokens on success
@api_view(['POST'])
@permission_classes([AllowAny])
def login(request):
    username = request.data.get('username')
    password = request.data.get('password')

    # Django's authenticate checks the username and password against the database
    user = authenticate(username=username, password=password)

    if not user:
        return Response({'error': 'Invalid credentials'}, status=status.HTTP_401_UNAUTHORIZED)

    # Generate and return fresh JWT tokens
    refresh = RefreshToken.for_user(user)
    return Response({
        'token': str(refresh.access_token),
        'refresh': str(refresh),
        'user': UserSerializer(user).data
    })


# Returns the currently logged in user's data
# Used by the frontend to restore session on page load
@api_view(['GET'])
def get_current_user(request):
    return Response(UserSerializer(request.user).data)


# Handles a customer submitting a service request
# Includes several validation checks to prevent misuse
@api_view(['POST'])
def create_request(request):
    customer = request.user

    # Providers should not be able to request services
    if customer.role == 'provider':
        return Response({'error': 'Providers cannot request services.'}, status=status.HTTP_400_BAD_REQUEST)

    service_id = request.data.get('service')
    message = request.data.get('message', '')

    # Check the service actually exists
    try:
        service = Service.objects.get(id=service_id)
    except Service.DoesNotExist:
        return Response({'error': 'Service not found.'}, status=status.HTTP_404_NOT_FOUND)

    # Prevent a provider from requesting their own service
    if service.provider.user == customer:
        return Response({'error': 'You cannot request your own service.'}, status=status.HTTP_400_BAD_REQUEST)

    # Block duplicate active requests for the same service
    # Customers can re-request if the previous request was declined or completed
    if ServiceRequest.objects.filter(customer=customer, service=service, status__in=['pending', 'accepted']).exists():
        return Response({'error': 'You already have an active request for this service.'}, status=status.HTTP_400_BAD_REQUEST)

    # Create and return the service request
    service_request = ServiceRequest.objects.create(
        customer=customer,
        service=service,
        message=message
    )

    return Response(ServiceRequestSerializer(service_request).data, status=status.HTTP_201_CREATED)


# Handles a provider creating a new service listing
# Automatically links the service to the logged in provider's profile
@api_view(['POST'])
def create_service(request):
    user = request.user

    # Only providers can create services
    if user.role != 'provider':
        return Response({'error': 'Only providers can create services.'}, status=status.HTTP_403_FORBIDDEN)

    # Get the provider's profile to link the service to
    try:
        provider_profile = ProviderProfile.objects.get(user=user)
    except ProviderProfile.DoesNotExist:
        return Response({'error': 'Provider profile not found.'}, status=status.HTTP_404_NOT_FOUND)

    title = request.data.get('title')
    description = request.data.get('description')
    category = request.data.get('category')
    price = request.data.get('price')

    # All fields are required
    if not title or not description or not category or not price:
        return Response({'error': 'Please fill in all fields.'}, status=status.HTTP_400_BAD_REQUEST)

    # Create the service linked to the provider's profile
    service = Service.objects.create(
        provider=provider_profile,
        title=title,
        description=description,
        category=category,
        price=price
    )

    return Response(ServiceSerializer(service).data, status=status.HTTP_201_CREATED)


# Standard CRUD viewset for users
class UserViewSet(viewsets.ModelViewSet):
    queryset = User.objects.all()
    serializer_class = UserSerializer


# Standard CRUD viewset for provider profiles
class ProviderProfileViewSet(viewsets.ModelViewSet):
    queryset = ProviderProfile.objects.all()
    serializer_class = ProviderProfileSerializer


# Standard CRUD viewset for services
# Read access is public, write access requires authentication
class ServiceViewSet(viewsets.ModelViewSet):
    queryset = Service.objects.all()
    serializer_class = ServiceSerializer
    permission_classes = [permissions.IsAuthenticatedOrReadOnly]


# Viewset for service requests
# Overrides get_queryset so users only see their own data
# Providers see requests for their services, customers see their own requests
class ServiceRequestViewSet(viewsets.ModelViewSet):
    serializer_class = ServiceRequestSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        user = self.request.user

        # Filter requests to only show those belonging to this provider
        if user.role == 'provider':
            try:
                provider_profile = ProviderProfile.objects.get(user=user)
                return ServiceRequest.objects.filter(service__provider=provider_profile)
            except ProviderProfile.DoesNotExist:
                return ServiceRequest.objects.none()

        # Filter requests to only show those made by this customer
        elif user.role == 'customer':
            return ServiceRequest.objects.filter(customer=user)

        # Return nothing if role is unrecognised
        return ServiceRequest.objects.none()