from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .views import UserViewSet, RideViewSet, RideEventViewSet

# Create router and register viewsets
router = DefaultRouter()
router.register(r'users', UserViewSet)
router.register(r'rides', RideViewSet)
router.register(r'ride-events', RideEventViewSet)

urlpatterns = [
    path('', include(router.urls)),
]
