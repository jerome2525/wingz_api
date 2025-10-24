import django_filters
from django.db.models import Q, F, Case, When, FloatField, Value
from django.db.models.functions import Radians, Sin, Cos, ATan2, Sqrt, Power
from .models import Ride, User
import math


class RideFilter(django_filters.FilterSet):
    """
    Filter for Ride model with advanced filtering and sorting
    """
    status = django_filters.ChoiceFilter(choices=Ride.STATUS_CHOICES)
    rider_email = django_filters.CharFilter(field_name='id_rider__email', lookup_expr='icontains')
    rider_name = django_filters.CharFilter(method='filter_rider_name')
    driver_name = django_filters.CharFilter(method='filter_driver_name')
    date_from = django_filters.DateTimeFilter(field_name='created_at', lookup_expr='gte')
    date_to = django_filters.DateTimeFilter(field_name='created_at', lookup_expr='lte')
    pickup_time_from = django_filters.DateTimeFilter(field_name='pickup_time', lookup_expr='gte')
    pickup_time_to = django_filters.DateTimeFilter(field_name='pickup_time', lookup_expr='lte')
    
    # Sorting parameters
    sort_by = django_filters.ChoiceFilter(
        choices=[
            ('pickup_time', 'Pickup Time'),
            ('distance', 'Distance to Pickup'),
            ('created_at', 'Created At'),
        ],
        method='filter_sort_by'
    )
    
    # GPS coordinates for distance sorting
    lat = django_filters.NumberFilter(method='filter_by_distance')
    lon = django_filters.NumberFilter(method='filter_by_distance')
    
    class Meta:
        model = Ride
        fields = ['status', 'id_rider', 'id_driver', 'rider_name', 'driver_name', 'rider_email',
                 'date_from', 'date_to', 'pickup_time_from', 'pickup_time_to', 'sort_by', 'lat', 'lon']
    
    def filter_rider_name(self, queryset, name, value):
        """Filter by rider's first or last name"""
        return queryset.filter(
            Q(id_rider__first_name__icontains=value) |
            Q(id_rider__last_name__icontains=value)
        )
    
    def filter_driver_name(self, queryset, name, value):
        """Filter by driver's first or last name"""
        return queryset.filter(
            Q(id_driver__first_name__icontains=value) |
            Q(id_driver__last_name__icontains=value)
        )
    
    def filter_sort_by(self, queryset, name, value):
        """Handle sorting by different fields"""
        if value == 'pickup_time':
            return queryset.order_by('pickup_time')
        elif value == 'created_at':
            return queryset.order_by('-created_at')
        elif value == 'distance':
            # Distance sorting will be handled in the view
            return queryset
        return queryset
    
    def filter_by_distance(self, queryset, name, value):
        """Filter by distance (used for sorting)"""
        # This method is called for both lat and lon, but we only need to process once
        return queryset


class UserFilter(django_filters.FilterSet):
    """
    Filter for User model
    """
    role = django_filters.ChoiceFilter(choices=User.ROLE_CHOICES)
    
    class Meta:
        model = User
        fields = ['role']
