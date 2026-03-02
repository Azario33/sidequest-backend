from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .views import (
    test_api, register, login, get_current_user, create_request, create_service,
    UserViewSet, ProviderProfileViewSet, ServiceViewSet, ServiceRequestViewSet
)

router = DefaultRouter()
router.register(r'users', UserViewSet)
router.register(r'providers', ProviderProfileViewSet)
router.register(r'services', ServiceViewSet)
router.register(r'requests', ServiceRequestViewSet, basename='servicerequest')

urlpatterns = [
    path('test/', test_api),
    path('auth/register/', register),
    path('auth/login/', login),
    path('auth/me/', get_current_user),
    path('requests/create/', create_request),
    path('services/create/', create_service),
    path('', include(router.urls)),
]