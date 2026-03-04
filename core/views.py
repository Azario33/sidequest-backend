# views.py
# This file contains all the API logic for SideQuest
# Each function or class here handles a specific API request from the frontend

import re
import random
from datetime import timedelta
from django.utils import timezone
from django.core.mail import send_mail
from rest_framework import viewsets, permissions, status
from rest_framework.decorators import api_view, permission_classes
from rest_framework.response import Response
from rest_framework.permissions import AllowAny
from rest_framework_simplejwt.tokens import RefreshToken
from django.contrib.auth import authenticate
from .models import User, ProviderProfile, Service, ServiceRequest, PasswordResetCode
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


# Allows a customer to cancel a pending request
# Only the customer who made the request can cancel it, and only if it is still pending
@api_view(['PATCH'])
def cancel_request(request, request_id):
    customer = request.user

    # Only customers can cancel requests
    if customer.role != 'customer':
        return Response({'error': 'Only customers can cancel requests.'}, status=status.HTTP_403_FORBIDDEN)

    # Check the request exists
    try:
        service_request = ServiceRequest.objects.get(id=request_id)
    except ServiceRequest.DoesNotExist:
        return Response({'error': 'Request not found.'}, status=status.HTTP_404_NOT_FOUND)

    # Make sure this customer owns the request
    if service_request.customer != customer:
        return Response({'error': 'You can only cancel your own requests.'}, status=status.HTTP_403_FORBIDDEN)

    # Only pending requests can be cancelled
    if service_request.status != 'pending':
        return Response({'error': 'Only pending requests can be cancelled.'}, status=status.HTTP_400_BAD_REQUEST)

    # Mark the request as declined (cancelled)
    service_request.status = 'declined'
    service_request.save()

    return Response(ServiceRequestSerializer(service_request).data)


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


# Allows a provider to edit an existing service they own
# Only the provider who created the service can edit it
@api_view(['PATCH'])
def update_service(request, service_id):
    user = request.user

    # Only providers can edit services
    if user.role != 'provider':
        return Response({'error': 'Only providers can edit services.'}, status=status.HTTP_403_FORBIDDEN)

    # Check the service exists
    try:
        service = Service.objects.get(id=service_id)
    except Service.DoesNotExist:
        return Response({'error': 'Service not found.'}, status=status.HTTP_404_NOT_FOUND)

    # Make sure this provider owns the service
    if service.provider.user != user:
        return Response({'error': 'You can only edit your own services.'}, status=status.HTTP_403_FORBIDDEN)

    # Only update fields that were actually sent in the request
    title = request.data.get('title')
    description = request.data.get('description')
    category = request.data.get('category')
    price = request.data.get('price')

    if title is not None:
        service.title = title
    if description is not None:
        service.description = description
    if category is not None:
        service.category = category
    if price is not None:
        service.price = price

    service.save()

    return Response(ServiceSerializer(service).data)


# Allows a provider to update their own profile
# Handles bio, service area and availability updates
@api_view(['PATCH'])
def update_provider_profile(request):
    user = request.user

    # Only providers have a profile to update
    if user.role != 'provider':
        return Response({'error': 'Only providers can update a profile.'}, status=status.HTTP_403_FORBIDDEN)

    try:
        profile = ProviderProfile.objects.get(user=user)
    except ProviderProfile.DoesNotExist:
        return Response({'error': 'Provider profile not found.'}, status=status.HTTP_404_NOT_FOUND)

    # Only update fields that were actually sent in the request
    bio = request.data.get('bio')
    service_area = request.data.get('service_area')
    is_available = request.data.get('is_available')

    if bio is not None:
        profile.bio = bio
    if service_area is not None:
        profile.service_area = service_area
    if is_available is not None:
        profile.is_available = is_available

    profile.save()

    return Response(ProviderProfileSerializer(profile).data)


# Allows any logged in user (customer or provider) to update their email and/or password
# Password changes return fresh JWT tokens so the user stays logged in
@api_view(['PATCH'])
def update_account_settings(request):
    user = request.user

    email = request.data.get('email')
    new_password = request.data.get('new_password')

    # Update email if provided, checking it isn't already taken by another account
    if email:
        if User.objects.filter(email=email).exclude(id=user.id).exists():
            return Response({'error': 'Email is already in use.'}, status=status.HTTP_400_BAD_REQUEST)
        user.email = email

    # Update password if provided, applying the same strength rules as registration
    if new_password:
        if len(new_password) < 8:
            return Response({'error': 'Password must be at least 8 characters.'}, status=status.HTTP_400_BAD_REQUEST)
        if not re.search(r'[A-Z]', new_password):
            return Response({'error': 'Password must contain at least one uppercase letter.'}, status=status.HTTP_400_BAD_REQUEST)
        if not re.search(r'[0-9]', new_password):
            return Response({'error': 'Password must contain at least one number.'}, status=status.HTTP_400_BAD_REQUEST)
        if not re.search(r'[!@#$%^&*]', new_password):
            return Response({'error': 'Password must contain at least one symbol (!@#$%^&*).'}, status=status.HTTP_400_BAD_REQUEST)
        user.set_password(new_password)

    user.save()

    # Return fresh JWT tokens so the session stays valid after a password change
    refresh = RefreshToken.for_user(user)
    return Response({
        'message': 'Account updated successfully.',
        'user': UserSerializer(user).data,
        'token': str(refresh.access_token),
        'refresh': str(refresh),
    })


# Sends a 6-digit reset code to the user's email address
# The code expires after 15 minutes for security
@api_view(['POST'])
@permission_classes([AllowAny])
def request_password_reset(request):
    email = request.data.get('email')

    if not email:
        return Response({'error': 'Please provide an email address.'}, status=status.HTTP_400_BAD_REQUEST)

    # Check an account with this email exists
    try:
        user = User.objects.get(email=email)
    except User.DoesNotExist:
        # Return success even if email not found to prevent email enumeration attacks
        return Response({'message': 'If an account with that email exists, a reset code has been sent.'})

    # Delete any existing reset codes for this user before creating a new one
    PasswordResetCode.objects.filter(user=user).delete()

    # Generate a random 6-digit code
    code = str(random.randint(100000, 999999))

    # Save the code with a 15 minute expiry
    PasswordResetCode.objects.create(
        user=user,
        code=code,
        expires_at=timezone.now() + timedelta(minutes=15)
    )

    # Send the code to the user's email
    send_mail(
        subject='Your SideQuest Password Reset Code',
        message=f'Hi {user.username},\n\nYour password reset code is: {code}\n\nThis code expires in 15 minutes.\n\nIf you did not request this, please ignore this email.\n\n— The SideQuest Team',
        from_email=None,  # Uses DEFAULT_FROM_EMAIL from settings
        recipient_list=[email],
    )

    return Response({'message': 'If an account with that email exists, a reset code has been sent.'})


# Verifies the reset code and sets the new password
@api_view(['POST'])
@permission_classes([AllowAny])
def confirm_password_reset(request):
    email = request.data.get('email')
    code = request.data.get('code')
    new_password = request.data.get('new_password')

    if not email or not code or not new_password:
        return Response({'error': 'Please provide email, code and new password.'}, status=status.HTTP_400_BAD_REQUEST)

    # Find the reset code record
    try:
        reset = PasswordResetCode.objects.get(user__email=email, code=code)
    except PasswordResetCode.DoesNotExist:
        return Response({'error': 'Invalid reset code.'}, status=status.HTTP_400_BAD_REQUEST)

    # Check the code has not expired
    if reset.expires_at < timezone.now():
        reset.delete()
        return Response({'error': 'Reset code has expired. Please request a new one.'}, status=status.HTTP_400_BAD_REQUEST)

    # Password strength validation
    if len(new_password) < 8:
        return Response({'error': 'Password must be at least 8 characters.'}, status=status.HTTP_400_BAD_REQUEST)
    if not re.search(r'[A-Z]', new_password):
        return Response({'error': 'Password must contain at least one uppercase letter.'}, status=status.HTTP_400_BAD_REQUEST)
    if not re.search(r'[0-9]', new_password):
        return Response({'error': 'Password must contain at least one number.'}, status=status.HTTP_400_BAD_REQUEST)
    if not re.search(r'[!@#$%^&*]', new_password):
        return Response({'error': 'Password must contain at least one symbol (!@#$%^&*).'}, status=status.HTTP_400_BAD_REQUEST)

    # Set the new password and delete the used reset code
    user = reset.user
    user.set_password(new_password)
    user.save()
    reset.delete()

    return Response({'message': 'Password reset successfully. You can now log in.'})


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