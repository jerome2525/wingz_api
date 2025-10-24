from rest_framework import serializers
from .models import User, Ride, RideEvent
from datetime import datetime, timedelta
import re
import logging
from django.core.exceptions import ValidationError
from django.db import IntegrityError
from rest_framework import status
from rest_framework.response import Response
from rest_framework.authtoken.models import Token

# Set up logging
logger = logging.getLogger(__name__)


class UserCreationError(Exception):
    """Custom exception for user creation errors"""
    def __init__(self, message, error_code=None, details=None):
        self.message = message
        self.error_code = error_code
        self.details = details
        super().__init__(self.message)


def validate_password_strength(password):
    """
    Validate password strength:
    - At least 8 characters
    - At least one uppercase letter
    - At least one lowercase letter
    - At least one digit
    - At least one special character
    """
    if len(password) < 8:
        raise ValidationError("Password must be at least 8 characters long.")
    
    if not re.search(r'[A-Z]', password):
        raise ValidationError("Password must contain at least one uppercase letter.")
    
    if not re.search(r'[a-z]', password):
        raise ValidationError("Password must contain at least one lowercase letter.")
    
    if not re.search(r'\d', password):
        raise ValidationError("Password must contain at least one digit.")
    
    if not re.search(r'[!@#$%^&*(),.?":{}|<>]', password):
        raise ValidationError("Password must contain at least one special character.")
    
    return password


def validate_email_format(email):
    """
    Validate email format
    """
    pattern = r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$'
    if not re.match(pattern, email):
        raise ValidationError("Enter a valid email address.")
    return email


def validate_phone_format(phone):
    """
    Validate phone number format (strict international format only)
    """
    # Check if phone contains only valid characters: digits, +, spaces, hyphens, parentheses
    if not re.match(r'^[\d\+\s\-\(\)]+$', phone):
        raise ValidationError("Phone number can only contain digits, +, spaces, hyphens, and parentheses.")
    
    # Remove all non-digit characters except +
    cleaned_phone = re.sub(r'[^\d+]', '', phone)
    
    # Must start with + and have exactly 10-15 digits after +
    if not cleaned_phone.startswith('+'):
        raise ValidationError("Phone number must start with + (international format).")
    
    # Extract digits after +
    digits_only = cleaned_phone[1:]  # Remove the +
    
    # Check if it has exactly 10-15 digits
    if not re.match(r'^\d{10,15}$', digits_only):
        raise ValidationError("Phone number must have 10-15 digits after the + sign.")
    
    # Additional validation: check for common invalid patterns
    if len(digits_only) < 10:
        raise ValidationError("Phone number must have at least 10 digits.")
    
    if len(digits_only) > 15:
        raise ValidationError("Phone number cannot have more than 15 digits.")
    
    # Check for obviously invalid patterns (all same digits, etc.)
    if len(set(digits_only)) == 1:  # All digits are the same
        raise ValidationError("Phone number cannot have all identical digits.")
    
    return cleaned_phone


class UserSerializer(serializers.ModelSerializer):
    """
    Serializer for User model with password update support
    """
    full_name = serializers.SerializerMethodField()
    password = serializers.CharField(
        write_only=True, 
        required=False,
        min_length=8,
        help_text="Password must be at least 8 characters with uppercase, lowercase, digit, and special character",
        style={'input_type': 'password'}
    )
    password_confirm = serializers.CharField(
        write_only=True,
        required=False,
        help_text="Confirm your password",
        style={'input_type': 'password'}
    )
    
    class Meta:
        model = User
        fields = [
            'id_user', 'role', 'first_name', 'last_name', 
            'email', 'phone_number', 'full_name', 'password', 'password_confirm'
        ]
        read_only_fields = ['id_user']
    
    def get_full_name(self, obj):
        return f"{obj.first_name} {obj.last_name}"
    
    def validate_password(self, value):
        """Validate password strength"""
        return validate_password_strength(value)
    
    def validate(self, attrs):
        """Validate password confirmation and other fields"""
        # Check if password is being updated
        if 'password' in attrs or 'password_confirm' in attrs:
            # Both password and password_confirm must be provided together
            if 'password' in attrs and 'password_confirm' not in attrs:
                raise serializers.ValidationError({
                    'password_confirm': 'Password confirmation is required when updating password.'
                })
            if 'password_confirm' in attrs and 'password' not in attrs:
                raise serializers.ValidationError({
                    'password': 'Password is required when providing password confirmation.'
                })
            
            # If both are provided, check if they match
            if 'password' in attrs and 'password_confirm' in attrs:
                if attrs['password'] != attrs['password_confirm']:
                    raise serializers.ValidationError({
                        'password_confirm': 'Password and password confirmation do not match.'
                    })
                
                # Remove password_confirm from validated data as it's not a model field
                attrs.pop('password_confirm')
        
        return attrs
    
    def update(self, instance, validated_data):
        """Update user instance with password and email handling"""
        # Handle password update
        if 'password' in validated_data:
            password = validated_data.pop('password')
            # Update the Django user's password
            if instance.django_user:
                instance.django_user.set_password(password)
                instance.django_user.save()
                logger.info(f"Password updated for user ID: {instance.id_user}")
        
        # Handle email update
        if 'email' in validated_data:
            new_email = validated_data['email']
            # Update the Django user's email and username
            if instance.django_user:
                instance.django_user.email = new_email
                instance.django_user.username = new_email  # Username is set to email
                instance.django_user.save()
                logger.info(f"Email updated for user ID: {instance.id_user}, New email: {new_email}")
        
        # Update other fields
        for attr, value in validated_data.items():
            setattr(instance, attr, value)
        
        instance.save()
        return instance


class UserCreateSerializer(serializers.ModelSerializer):
    """
    Serializer for creating new users with strict validation
    """
    password = serializers.CharField(
        write_only=True, 
        min_length=8,
        help_text="Password must be at least 8 characters with uppercase, lowercase, digit, and special character",
        style={'input_type': 'password'}
    )
    password_confirm = serializers.CharField(
        write_only=True,
        help_text="Confirm your password",
        style={'input_type': 'password'}
    )
    email = serializers.EmailField(
        help_text="Valid email address (e.g., david@yahoo.com)"
    )
    phone_number = serializers.CharField(
        help_text="Phone number in international format (e.g., +639150176020)"
    )
    first_name = serializers.CharField(
        help_text="User's first name"
    )
    last_name = serializers.CharField(
        help_text="User's last name"
    )
    role = serializers.ChoiceField(
        choices=User.ROLE_CHOICES,
        help_text="""User role determines permissions and access level:
        
        • **admin**: Full system access
          - Manage all users, rides, and events
          - View system analytics and reports
          - Configure system settings
          - Access admin dashboard
          
        • **rider**: Customer role for booking rides
          - Request and book rides
          - View ride history and status
          - Rate and review drivers
          - Manage personal profile
          
        • **driver**: Service provider role
          - Accept and manage ride requests
          - Update ride status (en-route, pickup, dropoff)
          - View assigned rides and earnings
          - Manage availability status"""
    )
    
    class Meta:
        model = User
        fields = [
            'role', 'first_name', 'last_name', 
            'email', 'phone_number', 'password', 'password_confirm'
        ]
    
    def validate_password(self, value):
        """Validate password strength"""
        return validate_password_strength(value)
    
    def validate_email(self, value):
        """Validate email format"""
        return validate_email_format(value)
    
    def validate_phone_number(self, value):
        """Validate phone number format"""
        return validate_phone_format(value)
    
    def validate(self, attrs):
        if attrs['password'] != attrs['password_confirm']:
            raise serializers.ValidationError("Passwords don't match")
        return attrs
    
    def create(self, validated_data):
        """
        Create user with comprehensive error handling
        """
        try:
            validated_data.pop('password_confirm')
            password = validated_data.pop('password')
            
            # Log user creation attempt
            logger.info(f"Attempting to create user with email: {validated_data.get('email')}")
            
            # Check if email already exists
            if User.objects.filter(email=validated_data['email']).exists():
                logger.warning(f"User creation failed - email already exists: {validated_data['email']}")
                raise UserCreationError(
                    message="A user with this email address already exists.",
                    error_code="EMAIL_EXISTS",
                    details={"email": validated_data['email']}
                )
            
            # Check if phone already exists
            if User.objects.filter(phone_number=validated_data['phone_number']).exists():
                logger.warning(f"User creation failed - phone already exists: {validated_data['phone_number']}")
                raise UserCreationError(
                    message="A user with this phone number already exists.",
                    error_code="PHONE_EXISTS",
                    details={"phone_number": validated_data['phone_number']}
                )
            
            # Create the custom User instance
            try:
                user = User.objects.create(**validated_data)
                logger.info(f"Custom user created successfully with ID: {user.id_user}")
            except IntegrityError as e:
                logger.error(f"Database integrity error creating custom user: {str(e)}")
                if 'email' in str(e):
                    raise UserCreationError(
                        message="A user with this email address already exists.",
                        error_code="EMAIL_EXISTS",
                        details={"email": validated_data['email']}
                    )
                elif 'phone_number' in str(e):
                    raise UserCreationError(
                        message="A user with this phone number already exists.",
                        error_code="PHONE_EXISTS",
                        details={"phone_number": validated_data['phone_number']}
                    )
                else:
                    raise UserCreationError(
                        message="Unable to create user due to data conflict.",
                        error_code="DATA_CONFLICT",
                        details={"error": str(e)}
                    )
            
            # Create Django User for authentication
            try:
                from django.contrib.auth.models import User as DjangoUser
                django_user = DjangoUser.objects.create_user(
                    username=validated_data['email'],  # Use email as username
                    email=validated_data['email'],
                    password=password,
                    first_name=validated_data['first_name'],
                    last_name=validated_data['last_name']
                )
                logger.info(f"Django user created successfully with ID: {django_user.id}")
            except IntegrityError as e:
                logger.error(f"Database integrity error creating Django user: {str(e)}")
                # Clean up the custom user if Django user creation fails
                user.delete()
                raise UserCreationError(
                    message="Unable to create authentication account due to username conflict.",
                    error_code="USERNAME_EXISTS",
                    details={"username": validated_data['email']}
                )
            except Exception as e:
                logger.error(f"Unexpected error creating Django user: {str(e)}")
                # Clean up the custom user if Django user creation fails
                user.delete()
                raise UserCreationError(
                    message="Unable to create authentication account.",
                    error_code="AUTH_CREATION_FAILED",
                    details={"error": str(e)}
                )
            
            # Link the Django user to our custom user
            try:
                user.django_user = django_user
                user.save()
                logger.info(f"User creation completed successfully for: {validated_data['email']}")
            except Exception as e:
                logger.error(f"Error linking Django user to custom user: {str(e)}")
                # Clean up both users if linking fails
                user.delete()
                django_user.delete()
                raise UserCreationError(
                    message="Unable to complete user setup.",
                    error_code="LINKING_FAILED",
                    details={"error": str(e)}
                )
            
            # Generate authentication token for the Django user
            try:
                token, created = Token.objects.get_or_create(user=django_user)
                logger.info(f"Authentication token {'created' if created else 'retrieved'} for user: {validated_data['email']}")
            except Exception as e:
                logger.error(f"Error creating authentication token: {str(e)}")
                # Don't fail user creation if token creation fails
                logger.warning("User created successfully but token creation failed")
            
            return user
            
        except UserCreationError:
            # Re-raise our custom errors
            raise
        except ValidationError as e:
            logger.error(f"Validation error during user creation: {str(e)}")
            raise UserCreationError(
                message="Invalid data provided.",
                error_code="VALIDATION_ERROR",
                details={"errors": str(e)}
            )
        except Exception as e:
            logger.error(f"Unexpected error during user creation: {str(e)}")
            raise UserCreationError(
                message="An unexpected error occurred while creating the user.",
                error_code="UNEXPECTED_ERROR",
                details={"error": str(e)}
            )


class RideEventSerializer(serializers.ModelSerializer):
    """
    Serializer for RideEvent model
    """
    id_ride = serializers.IntegerField(source='id_ride.id_ride', read_only=True)
    id_ride_input = serializers.IntegerField(write_only=True, required=False, source='id_ride')
    
    class Meta:
        model = RideEvent
        fields = ['id_ride_event', 'id_ride', 'id_ride_input', 'description', 'created_at']
        read_only_fields = ['id_ride_event', 'created_at', 'id_ride']
    
    def create(self, validated_data):
        # Convert id_ride integer to Ride object
        ride_id = validated_data.pop('id_ride')
        try:
            ride = Ride.objects.get(id_ride=ride_id)
        except Ride.DoesNotExist:
            raise serializers.ValidationError(f"Ride with id {ride_id} does not exist")
        
        # Create the event with the Ride object
        return RideEvent.objects.create(id_ride=ride, **validated_data)
    
    def update(self, instance, validated_data):
        # Handle id_ride update if provided
        if 'id_ride' in validated_data:
            ride_id = validated_data.pop('id_ride')
            try:
                ride = Ride.objects.get(id_ride=ride_id)
                instance.id_ride = ride
            except Ride.DoesNotExist:
                raise serializers.ValidationError(f"Ride with id {ride_id} does not exist")
        
        # Update other fields
        for attr, value in validated_data.items():
            setattr(instance, attr, value)
        
        instance.save()
        return instance


class RideSerializer(serializers.ModelSerializer):
    """
    Serializer for Ride model
    """
    rider = UserSerializer(source='id_rider', read_only=True)
    driver = UserSerializer(source='id_driver', read_only=True)
    events = RideEventSerializer(many=True, read_only=True)
    todays_ride_events = serializers.SerializerMethodField()
    distance_to_pickup = serializers.SerializerMethodField()
    rider_id = serializers.IntegerField(write_only=True, source='id_rider_id')
    driver_id = serializers.IntegerField(write_only=True, source='id_driver_id', required=False)
    
    class Meta:
        model = Ride
        fields = [
            'id_ride', 'status', 'rider', 'driver', 'events', 'todays_ride_events',
            'pickup_latitude', 'pickup_longitude', 
            'dropoff_latitude', 'dropoff_longitude',
            'pickup_time', 'created_at', 'updated_at', 'distance_to_pickup',
            'rider_id', 'driver_id'
        ]
        read_only_fields = ['id_ride', 'created_at', 'updated_at', 'todays_ride_events', 'distance_to_pickup']
    
    def get_todays_ride_events(self, obj):
        """
        Get ride events from today (since midnight) using prefetched events
        This is now efficient because events are already loaded via prefetch_related
        """
        from datetime import datetime, timedelta
        from django.utils import timezone
        
        # Get start of today (00:00:00) instead of exactly 24 hours ago
        now = timezone.now()
        start_of_today = now.replace(hour=0, minute=0, second=0, microsecond=0)
        
        # Filter prefetched events in Python - no additional database query
        # Use list() to ensure we're working with the prefetched data
        all_events = list(obj.events.all())
        todays_events = [event for event in all_events if event.created_at >= start_of_today]
        return RideEventSerializer(todays_events, many=True).data
    
    def get_distance_to_pickup(self, obj):
        """
        Calculate distance to pickup location if GPS coordinates provided
        """
        request = self.context.get('request')
        if request and hasattr(request, 'query_params'):
            lat = request.query_params.get('lat')
            lon = request.query_params.get('lon')
            if lat and lon:
                try:
                    return round(obj.calculate_distance_to_pickup(float(lat), float(lon)), 2)
                except (ValueError, TypeError):
                    pass
        return None


class RideCreateSerializer(serializers.ModelSerializer):
    """
    Serializer for creating new rides
    """
    class Meta:
        model = Ride
        fields = [
            'id_rider', 'pickup_latitude', 'pickup_longitude',
            'dropoff_latitude', 'dropoff_longitude', 'pickup_time'
        ]
    
    def create(self, validated_data):
        # Set initial status
        validated_data['status'] = 'requested'
        
        # Create ride
        ride = Ride.objects.create(**validated_data)
        
        # Create initial event
        RideEvent.objects.create(
            id_ride=ride,
            description=f"Ride requested by {ride.id_rider.first_name}"
        )
        
        return ride


class RideStatusUpdateSerializer(serializers.ModelSerializer):
    """
    Serializer for updating ride status
    """
    class Meta:
        model = Ride
        fields = ['status']
    
    def update(self, instance, validated_data):
        old_status = instance.status
        new_status = validated_data.get('status')
        
        # Update the ride
        instance = super().update(instance, validated_data)
        
        # Create event for status change
        RideEvent.objects.create(
            id_ride=instance,
            description=f"Ride status changed from {old_status} to {new_status}"
        )
        
        return instance


class LoginSerializer(serializers.Serializer):
    """
    Serializer for user login
    """
    email = serializers.EmailField(
        help_text="User email address"
    )
    password = serializers.CharField(
        write_only=True,
        style={'input_type': 'password'},
        help_text="User password"
    )
    
    class Meta:
        fields = ['email', 'password']
