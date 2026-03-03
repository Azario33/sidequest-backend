# urls.py
# This file maps URL paths to the correct view functions and viewsets
# All routes here are prefixed with /api/ as defined in server/urls.py

from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .views import (
    test_api, register, login, get_current_user, create_request, create_service,
    UserViewSet, ProviderProfileViewSet, ServiceViewSet, ServiceRequestViewSet
)

# DefaultRouter automatically generates standard CRUD routes for each viewset
# For example, registering 'services' creates:
# GET /api/services/ - list all services
# POST /api/services/ - create a service
# GET /api/services/{id}/ - get a single service
# PUT /api/services/{id}/ - update a service
# DELETE /api/services/{id}/ - delete a service
router = DefaultRouter()
router.register(r'users', UserViewSet)
router.register(r'providers', ProviderProfileViewSet)
router.register(r'services', ServiceViewSet)
# basename is required here because ServiceRequestViewSet uses a dynamic queryset
router.register(r'requests', ServiceRequestViewSet, basename='servicerequest')

urlpatterns = [
    # Simple test route to check the backend is running
    path('test/', test_api),

    # Authentication routes
    path('auth/register/', register),
    path('auth/login/', login),
    path('auth/me/', get_current_user),

    # Custom routes with extra validation logic
    # These are separate from the router because they have custom business rules
    path('requests/create/', create_request),
    path('services/create/', create_service),

    # Includes all the auto-generated router routes
    path('', include(router.urls)),
]