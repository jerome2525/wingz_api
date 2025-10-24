from django.db import models
from django.contrib.auth.models import User as DjangoUser
from django.core.validators import RegexValidator
from django.db.models import Q
from datetime import datetime, timedelta
import math


class User(models.Model):
    """
    Custom User model extending Django's AbstractUser
    """
    ROLE_CHOICES = [
        ('admin', 'Admin'),
        ('rider', 'Rider'),
        ('driver', 'Driver'),
    ]
    
    id_user = models.AutoField(primary_key=True)
    role = models.CharField(max_length=20, choices=ROLE_CHOICES, default='rider')
    first_name = models.CharField(max_length=100)
    last_name = models.CharField(max_length=100)
    email = models.EmailField(unique=True)
    phone_number = models.CharField(
        max_length=15,
        validators=[RegexValidator(
            regex=r'^\+?1?\d{9,15}$',
            message="Phone number must be entered in the format: '+999999999'. Up to 15 digits allowed."
        )]
    )
    
    # Link to Django's built-in User model
    django_user = models.OneToOneField(DjangoUser, on_delete=models.CASCADE, related_name='profile', null=True, blank=True)
    
    class Meta:
        db_table = 'users'
        verbose_name = 'User'
        verbose_name_plural = 'Users'
    
    def __str__(self):
        return f"{self.first_name} {self.last_name} ({self.role})"


class Ride(models.Model):
    """
    Ride model for tracking ride information
    """
    STATUS_CHOICES = [
        ('requested', 'Requested'),
        ('accepted', 'Accepted'),
        ('en-route', 'En Route'),
        ('pickup', 'Pickup'),
        ('dropoff', 'Dropoff'),
        ('completed', 'Completed'),
        ('cancelled', 'Cancelled'),
    ]
    
    id_ride = models.AutoField(primary_key=True)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='requested')
    id_rider = models.ForeignKey(
        User, 
        on_delete=models.CASCADE, 
        related_name='rides_as_rider',
        db_column='id_rider'
    )
    id_driver = models.ForeignKey(
        User, 
        on_delete=models.SET_NULL, 
        null=True, 
        blank=True,
        related_name='rides_as_driver',
        db_column='id_driver'
    )
    pickup_latitude = models.FloatField()
    pickup_longitude = models.FloatField()
    dropoff_latitude = models.FloatField()
    dropoff_longitude = models.FloatField()
    pickup_time = models.DateTimeField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        db_table = 'rides'
        verbose_name = 'Ride'
        verbose_name_plural = 'Rides'
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['pickup_time'], name='rides_pickup_time_idx'),
            models.Index(fields=['pickup_latitude', 'pickup_longitude'], name='rides_pickup_coords_idx'),
            models.Index(fields=['created_at'], name='rides_created_at_idx'),
            models.Index(fields=['status'], name='rides_status_idx'),
        ]
    
    def __str__(self):
        return f"Ride {self.id_ride} - {self.status} ({self.id_rider.first_name})"
    
    def calculate_distance_to_pickup(self, lat, lon):
        """
        Calculate distance from given coordinates to pickup location using Haversine formula
        Returns distance in kilometers
        """
        R = 6371  # Earth's radius in kilometers
        
        lat1_rad = math.radians(self.pickup_latitude)
        lat2_rad = math.radians(lat)
        delta_lat = math.radians(lat - self.pickup_latitude)
        delta_lon = math.radians(lon - self.pickup_longitude)
        
        a = (math.sin(delta_lat / 2) ** 2 + 
             math.cos(lat1_rad) * math.cos(lat2_rad) * 
             math.sin(delta_lon / 2) ** 2)
        c = 2 * math.atan2(math.sqrt(a), math.sqrt(1 - a))
        
        return R * c
    
    def get_todays_events(self):
        """
        Get ride events from the last 24 hours
        """
        yesterday = datetime.now() - timedelta(days=1)
        return self.events.filter(created_at__gte=yesterday)


class RideEvent(models.Model):
    """
    Ride Event model for tracking ride events and status changes
    """
    id_ride_event = models.AutoField(primary_key=True)
    id_ride = models.ForeignKey(
        Ride, 
        on_delete=models.CASCADE, 
        related_name='events',
        db_column='id_ride'
    )
    description = models.CharField(max_length=255)
    created_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        db_table = 'ride_events'
        verbose_name = 'Ride Event'
        verbose_name_plural = 'Ride Events'
        ordering = ['-created_at']
    
    def __str__(self):
        return f"Event {self.id_ride_event} - {self.description}"