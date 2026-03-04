# admin.py
# Configures the Django admin panel for SideQuest
# Each ModelAdmin class controls how that model appears and behaves in the admin

from django.contrib import admin
from django.contrib.auth.admin import UserAdmin
from .models import User, ProviderProfile, Service, ServiceRequest, Notification


# Custom User admin — extends Django's built-in UserAdmin
# Adds role and phone to the list view and filters
@admin.register(User)
class CustomUserAdmin(UserAdmin):
    # Columns shown in the user list
    list_display = ['username', 'email', 'role', 'phone', 'is_active', 'date_joined']

    # Filters shown in the right sidebar
    list_filter = ['role', 'is_active', 'is_staff']

    # Fields searchable via the search bar
    search_fields = ['username', 'email', 'phone']

    # Default sort order
    ordering = ['-date_joined']

    # Add role and phone into the user detail form sections
    fieldsets = UserAdmin.fieldsets + (
        ('SideQuest Info', {'fields': ('role', 'phone')}),
    )


# Provider Profile admin
@admin.register(ProviderProfile)
class ProviderProfileAdmin(admin.ModelAdmin):
    list_display = ['get_username', 'service_area', 'is_available', 'get_email']
    list_filter = ['is_available']
    search_fields = ['user__username', 'user__email', 'service_area']

    # These fields should not be editable from the admin
    readonly_fields = ['user']

    def get_username(self, obj):
        return obj.user.username
    get_username.short_description = 'Username'

    def get_email(self, obj):
        return obj.user.email
    get_email.short_description = 'Email'


# Service admin
@admin.register(Service)
class ServiceAdmin(admin.ModelAdmin):
    list_display = ['title', 'category', 'price', 'get_provider', 'created_at']
    list_filter = ['category']
    search_fields = ['title', 'description', 'provider__user__username']
    ordering = ['-created_at']

    # Prevent accidental edits to ownership and timestamp
    readonly_fields = ['provider', 'created_at']

    def get_provider(self, obj):
        return obj.provider.user.username
    get_provider.short_description = 'Provider'


# Service Request admin
@admin.register(ServiceRequest)
class ServiceRequestAdmin(admin.ModelAdmin):
    list_display = ['get_service', 'get_customer', 'status', 'created_at']
    list_filter = ['status']
    search_fields = ['customer__username', 'service__title']
    ordering = ['-created_at']

    # Prevent changing who made the request or what service it was for
    readonly_fields = ['customer', 'service', 'created_at']

    def get_service(self, obj):
        return obj.service.title
    get_service.short_description = 'Service'

    def get_customer(self, obj):
        return obj.customer.username
    get_customer.short_description = 'Customer'


# Notification admin
@admin.register(Notification)
class NotificationAdmin(admin.ModelAdmin):
    list_display = ['get_recipient', 'message', 'is_read', 'created_at']
    list_filter = ['is_read']
    search_fields = ['recipient__username', 'message']
    ordering = ['-created_at']

    # Notifications should be read-only — no manual creation or editing
    readonly_fields = ['recipient', 'message', 'request', 'created_at']

    def get_recipient(self, obj):
        return obj.recipient.username
    get_recipient.short_description = 'Recipient'