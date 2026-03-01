from django.contrib import admin
from django.contrib.auth.admin import UserAdmin
from .models import User, ProviderProfile, Service, ServiceRequest

admin.site.register(User, UserAdmin)
admin.site.register(ProviderProfile)
admin.site.register(Service)
admin.site.register(ServiceRequest)