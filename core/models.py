# models.py
# This file defines all the database models for SideQuest
# Each class represents a table in the MySQL database

from django.db import models
from django.contrib.auth.models import AbstractUser


# Custom user model extending Django's built in AbstractUser
# Added a role field to distinguish between customers and providers
class User(AbstractUser):
    CUSTOMER = 'customer'
    PROVIDER = 'provider'

    # Role choices for the user
    ROLE_CHOICES = [
        (CUSTOMER, 'Customer'),
        (PROVIDER, 'Provider'),
    ]

    # Defaults to customer if no role is provided on registration
    role = models.CharField(max_length=10, choices=ROLE_CHOICES, default=CUSTOMER)

    # Optional phone number, not required
    phone = models.CharField(max_length=20, blank=True, null=True)

    def __str__(self):
        return f"{self.username} ({self.role})"


# Profile model for providers only
# Automatically created when a user registers as a provider
# Stores extra info like bio, location and availability
class ProviderProfile(models.Model):
    # One provider profile per user account
    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name='provider_profile')

    # Short description of the provider and their skills
    bio = models.TextField(blank=True, null=True)

    # The area the provider works in e.g. Halifax, NS
    service_area = models.CharField(max_length=255, blank=True, null=True)

    # GPS coordinates stored for future Google Maps integration
    latitude = models.DecimalField(max_digits=9, decimal_places=6, blank=True, null=True)
    longitude = models.DecimalField(max_digits=9, decimal_places=6, blank=True, null=True)

    # Lets providers toggle whether they are taking new jobs
    is_available = models.BooleanField(default=True)

    def __str__(self):
        return f"{self.user.username}'s Profile"


# Represents a service listing created by a provider
# For example: Pipe Repair - Plumbing - $50
class Service(models.Model):
    # Links to the provider who created this service
    provider = models.ForeignKey(ProviderProfile, on_delete=models.CASCADE, related_name='services')

    title = models.CharField(max_length=255)
    description = models.TextField()
    category = models.CharField(max_length=100)

    # Price is optional in case the provider wants to discuss it first
    price = models.DecimalField(max_digits=8, decimal_places=2, blank=True, null=True)

    # Timestamp set automatically when the service is created
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.title} by {self.provider.user.username}"


# Represents a customer requesting a specific service from a provider
# Tracks the full lifecycle of a job from request to completion
class ServiceRequest(models.Model):
    PENDING = 'pending'
    ACCEPTED = 'accepted'
    DECLINED = 'declined'
    COMPLETED = 'completed'

    STATUS_CHOICES = [
        (PENDING, 'Pending'),
        (ACCEPTED, 'Accepted'),
        (DECLINED, 'Declined'),
        (COMPLETED, 'Completed'),
    ]

    # The customer making the request
    customer = models.ForeignKey(User, on_delete=models.CASCADE, related_name='requests')

    # The service being requested
    service = models.ForeignKey(Service, on_delete=models.CASCADE, related_name='requests')

    # Starts as pending, provider can accept, decline or mark complete
    status = models.CharField(max_length=10, choices=STATUS_CHOICES, default=PENDING)

    # Optional message the customer can send to the provider
    message = models.TextField(blank=True, null=True)

    # Timestamp set automatically when the request is submitted
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.customer.username} -> {self.service.title} ({self.status})"