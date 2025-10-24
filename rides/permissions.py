from rest_framework import permissions
from .models import User


class IsOwnerOrReadOnly(permissions.BasePermission):
    """
    Custom permission to only allow owners of an object to edit it.
    """
    def has_object_permission(self, request, view, obj):
        # Read permissions for any request
        if request.method in permissions.SAFE_METHODS:
            return True
        
        # Write permissions only for the owner
        return obj.id == request.user.id


class IsDriverOrRider(permissions.BasePermission):
    """
    Custom permission to allow drivers and riders to access their own data.
    """
    def has_permission(self, request, view):
        if not request.user or not request.user.is_authenticated:
            return False
        
        try:
            custom_user = User.objects.get(django_user=request.user)
            # Allow admin to access everything
            if custom_user.role == 'admin':
                return True
            # Allow drivers and riders
            return custom_user.role in ['driver', 'rider']
        except User.DoesNotExist:
            return False
    
    def has_object_permission(self, request, view, obj):
        try:
            custom_user = User.objects.get(django_user=request.user)
            
            # Admin can access everything
            if custom_user.role == 'admin':
                return True
            
            # For Ride objects
            if hasattr(obj, 'id_rider') and hasattr(obj, 'id_driver'):
                # Rider can access their own rides
                if custom_user.role == 'rider' and obj.id_rider == custom_user:
                    return True
                # Driver can access rides they're assigned to
                if custom_user.role == 'driver' and obj.id_driver == custom_user:
                    return True
            
            # For RideEvent objects
            if hasattr(obj, 'id_ride'):
                ride = obj.id_ride
                if custom_user.role == 'rider' and ride.id_rider == custom_user:
                    return True
                if custom_user.role == 'driver' and ride.id_driver == custom_user:
                    return True
            
            return False
        except User.DoesNotExist:
            return False


class IsDriver(permissions.BasePermission):
    """
    Custom permission to only allow drivers.
    """
    def has_permission(self, request, view):
        if not request.user.is_authenticated:
            return False
        
        try:
            custom_user = User.objects.get(django_user=request.user)
            return custom_user.role == 'driver'
        except User.DoesNotExist:
            return False


class IsRider(permissions.BasePermission):
    """
    Custom permission to only allow riders.
    """
    def has_permission(self, request, view):
        if not request.user.is_authenticated:
            return False
        
        try:
            custom_user = User.objects.get(django_user=request.user)
            return custom_user.role == 'rider'
        except User.DoesNotExist:
            return False


class IsAdmin(permissions.BasePermission):
    """
    Custom permission to only allow admins.
    """
    def has_permission(self, request, view):
        if not request.user.is_authenticated:
            return False
        
        try:
            custom_user = User.objects.get(django_user=request.user)
            return custom_user.role == 'admin'
        except User.DoesNotExist:
            return False


class AllowAnyOrAdmin(permissions.BasePermission):
    """
    Custom permission to allow any user for certain actions (like registration)
    or admin users for all actions.
    """
    def has_permission(self, request, view):
        # Allow registration (POST) for any user
        if request.method == 'POST' and view.action == 'create':
            return True
        
        # Check if user is authenticated
        if not request.user or not request.user.is_authenticated:
            return False
        
        # Get the custom user object to check role
        try:
            custom_user = User.objects.get(django_user=request.user)
            return custom_user.role == 'admin'
        except User.DoesNotExist:
            return False