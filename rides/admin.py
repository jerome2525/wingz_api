from django.contrib import admin
from django.contrib.auth.admin import UserAdmin
from .models import User, Ride, RideEvent


@admin.register(User)
class CustomUserAdmin(admin.ModelAdmin):
    """
    Custom User admin interface
    """
    list_display = ('id_user', 'django_user', 'first_name', 'last_name', 'role', 'phone_number', 'email')
    list_filter = ('role',)
    search_fields = ('email', 'first_name', 'last_name', 'phone_number')
    ordering = ('-id_user',)
    
    fieldsets = (
        ('Personal info', {'fields': ('django_user', 'first_name', 'last_name', 'phone_number', 'role', 'email')}),
    )


class RideEventInline(admin.TabularInline):
    """
    Inline admin for RideEvent
    """
    model = RideEvent
    extra = 0
    readonly_fields = ('created_at',)


@admin.register(Ride)
class RideAdmin(admin.ModelAdmin):
    """
    Ride admin interface
    """
    list_display = ('id_ride', 'status', 'rider_name', 'driver_name', 'pickup_time', 'created_at')
    list_filter = ('status', 'created_at', 'pickup_time')
    search_fields = ('id_rider__first_name', 'id_rider__last_name', 'id_driver__first_name', 'id_driver__last_name')
    ordering = ('-created_at',)
    inlines = [RideEventInline]
    
    fieldsets = (
        ('Ride Information', {
            'fields': ('id_ride', 'status', 'id_rider', 'id_driver')
        }),
        ('Location', {
            'fields': ('pickup_latitude', 'pickup_longitude', 'dropoff_latitude', 'dropoff_longitude')
        }),
        ('Timing', {
            'fields': ('pickup_time', 'created_at', 'updated_at')
        }),
    )
    
    readonly_fields = ('id_ride', 'created_at', 'updated_at')
    
    def rider_name(self, obj):
        return f"{obj.id_rider.first_name} {obj.id_rider.last_name}"
    rider_name.short_description = 'Rider'
    
    def driver_name(self, obj):
        if obj.id_driver:
            return f"{obj.id_driver.first_name} {obj.id_driver.last_name}"
        return "Not assigned"
    driver_name.short_description = 'Driver'


@admin.register(RideEvent)
class RideEventAdmin(admin.ModelAdmin):
    """
    RideEvent admin interface
    """
    list_display = ('id_ride_event', 'id_ride', 'description', 'created_at')
    list_filter = ('created_at', 'id_ride__status')
    search_fields = ('description', 'id_ride__id_ride')
    ordering = ('-created_at',)
    
    fieldsets = (
        ('Event Information', {
            'fields': ('id_ride_event', 'id_ride', 'description', 'created_at')
        }),
    )
    
    readonly_fields = ('id_ride_event', 'created_at')