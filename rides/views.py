from rest_framework import viewsets, status
from rest_framework.decorators import action, api_view, permission_classes
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated, AllowAny
from rest_framework.pagination import PageNumberPagination
from django_filters.rest_framework import DjangoFilterBackend
from rest_framework.filters import SearchFilter, OrderingFilter
from drf_spectacular.utils import extend_schema, extend_schema_view, OpenApiParameter, OpenApiExample
from drf_spectacular.types import OpenApiTypes
from django.db.models import Prefetch
from django.views.decorators.csrf import csrf_exempt
from django.utils.decorators import method_decorator
from datetime import datetime, timedelta
import logging
from django.contrib.auth import authenticate
from rest_framework.authtoken.models import Token
from .models import User, Ride, RideEvent
from .serializers import (
    UserSerializer, UserCreateSerializer,
    RideSerializer, RideCreateSerializer, RideStatusUpdateSerializer,
    RideEventSerializer, UserCreationError, LoginSerializer
)
from .permissions import IsOwnerOrReadOnly, IsDriverOrRider, IsAdmin, AllowAnyOrAdmin
from .filters import RideFilter, UserFilter


class StandardResultsSetPagination(PageNumberPagination):
    """
    Custom pagination class for consistent pagination across the API
    """
    page_size = 20
    page_size_query_param = 'page_size'
    max_page_size = 100


class UserPagination(PageNumberPagination):
    """
    Custom pagination class specifically for User endpoints
    """
    page_size = 10
    page_size_query_param = 'page_size'
    max_page_size = 50
    page_query_param = 'page'


@method_decorator(csrf_exempt, name='dispatch')
@extend_schema_view(
    create=extend_schema(
        summary="Create User",
        description="""Create a new user account with strict validation and role-based permissions.

**Validation Requirements:**
- Password: 8+ characters with uppercase, lowercase, digit, and special character
- Email: Valid email format (e.g., user@example.com)
- Phone: International format with + prefix (e.g., +639150176020)

**Role Types:**
- **Admin**: Full system access, manage all users and settings
- **Rider**: Book rides, view history, rate drivers
- **Driver**: Accept rides, update status, manage availability

**Use Cases:**
- Register new customers (rider role)
- Onboard service providers (driver role)
- Create system administrators (admin role)

**Error Handling:**
- **409 Conflict**: Email/phone already exists
- **400 Bad Request**: Validation errors
- **500 Internal Server Error**: Unexpected errors
- All errors include structured response with error codes and details""",
        examples=[
            OpenApiExample(
                "Admin User",
                summary="Create Admin User",
                description="Admin users have full system access - can manage all users, rides, events, and system settings. Perfect for system administrators and managers.",
                value={
                    "role": "admin",
                    "first_name": "David",
                    "last_name": "Smith",
                    "email": "david@yahoo.com",
                    "phone_number": "+639150176020",
                    "password": "JeromeJerome2015$",
                    "password_confirm": "JeromeJerome2015$"
                },
                request_only=True,
            ),
            OpenApiExample(
                "Rider User",
                summary="Create Rider User",
                description="Rider users are customers who book rides. They can request rides, view ride history, rate drivers, and manage their profile. This is the most common user type.",
                value={
                    "role": "rider",
                    "first_name": "John",
                    "last_name": "Doe",
                    "email": "john.doe@example.com",
                    "phone_number": "+1234567890",
                    "password": "SecurePass123!",
                    "password_confirm": "SecurePass123!"
                },
                request_only=True,
            ),
            OpenApiExample(
                "Driver User",
                summary="Create Driver User",
                description="Driver users provide ride services. They can accept ride requests, update ride status, view assigned rides, and manage their availability. Requires vehicle and license verification.",
                value={
                    "role": "driver",
                    "first_name": "Jane",
                    "last_name": "Wilson",
                    "email": "jane.wilson@example.com",
                    "phone_number": "+1987654321",
                    "password": "DriverPass456@",
                    "password_confirm": "DriverPass456@"
                },
                request_only=True,
            )
        ]
    ),
    list=extend_schema(
        summary="List Users",
        description="""Get a paginated list of users with advanced filtering, search, and sorting capabilities.

**Pagination:**
- Default: 10 users per page
- Maximum: 50 users per page
- Use `page` parameter for navigation
- Use `page_size` parameter to customize results per page

**Filtering & Search:**
- **role**: Filter by user role (admin, rider, driver)
- **search**: Search across first name, last name, and email fields
- **ordering**: Sort results by various fields

**Use Cases:**
- Browse all users with pagination
- Find users by role (e.g., all drivers)
- Search for specific users by name or email
- Sort users for administrative purposes

**Performance:**
- Optimized queries with select_related
- Efficient pagination for large datasets
- Comprehensive logging for monitoring""",
        parameters=[
            OpenApiParameter(
                name='page',
                type=OpenApiTypes.INT,
                location=OpenApiParameter.QUERY,
                description='Page number for pagination (starts from 1)'
            ),
            OpenApiParameter(
                name='page_size',
                type=OpenApiTypes.INT,
                location=OpenApiParameter.QUERY,
                description='Number of users per page (max 50)'
            ),
            OpenApiParameter(
                name='role',
                type=OpenApiTypes.STR,
                location=OpenApiParameter.QUERY,
                description='Filter by user role',
                enum=['admin', 'rider', 'driver']
            ),
            OpenApiParameter(
                name='search',
                type=OpenApiTypes.STR,
                location=OpenApiParameter.QUERY,
                description='Search by first name, last name, or email (case-insensitive)'
            ),
            OpenApiParameter(
                name='ordering',
                type=OpenApiTypes.STR,
                location=OpenApiParameter.QUERY,
                description='Sort results by field (prefix with - for descending)',
                enum=['first_name', 'last_name', 'id_user', '-first_name', '-last_name', '-id_user']
            )
        ],
        examples=[
            OpenApiExample(
                "Get all users (first page)",
                summary="Default pagination",
                description="Get the first 10 users with default sorting",
                value={}
            ),
            OpenApiExample(
                "Get drivers only",
                summary="Filter by role",
                description="Get all users with driver role",
                value={"role": "driver"}
            ),
            OpenApiExample(
                "Search users",
                summary="Search functionality",
                description="Search for users containing 'john' in name or email",
                value={"search": "john"}
            ),
            OpenApiExample(
                "Custom pagination",
                summary="Custom page size",
                description="Get 25 users per page, sorted by first name",
                value={"page_size": 25, "ordering": "first_name"}
            )
        ]
    ),
    retrieve=extend_schema(
        summary="Get User",
        description="""Retrieve a specific user by their unique ID with comprehensive validation and error handling.

**Use Cases:**
- View user profile details
- Get user information for administrative purposes
- Retrieve user data for editing or verification

**Error Handling:**
- **404 Not Found**: User with specified ID does not exist
- **400 Bad Request**: Invalid user ID format
- **500 Internal Server Error**: Unexpected errors

**Response:**
- Complete user information including role, contact details, and timestamps
- Structured error responses with error codes and details"""
    ),
    update=extend_schema(
        summary="Update User",
        description="""Update user information with full validation and comprehensive error handling.

**Validation Requirements:**
- All fields must be provided (full update)
- Password: 8+ characters with uppercase, lowercase, digit, and special character
- Password Confirm: Must match the password field
- Email: Valid email format and must be unique
- Phone: International format with + prefix

**Password Update:**
- Both `password` and `password_confirm` fields are required when updating password
- Password confirmation must match the password
- Password is securely hashed and stored

**Use Cases:**
- Complete user profile updates
- Administrative user modifications
- User data corrections
- Password changes

**Error Handling:**
- **404 Not Found**: User with specified ID does not exist
- **400 Bad Request**: Validation errors or invalid data
- **409 Conflict**: Email/phone already exists
- **500 Internal Server Error**: Unexpected errors"""
    ),
    partial_update=extend_schema(
        summary="Partial Update User",
        description="""Partially update user information with validation and comprehensive error handling.

**Validation Requirements:**
- Only provided fields are updated
- Password: 8+ characters with uppercase, lowercase, digit, and special character (if provided)
- Password Confirm: Must match the password field (if password is provided)
- Email: Valid email format and must be unique (if provided)
- Phone: International format with + prefix (if provided)

**Password Update:**
- Both `password` and `password_confirm` fields are required when updating password
- Password confirmation must match the password
- Password is securely hashed and stored
- Other fields can be updated independently

**Use Cases:**
- Update specific user fields
- Quick profile modifications
- Selective data updates
- Password changes only
- Email updates only

**Error Handling:**
- **404 Not Found**: User with specified ID does not exist
- **400 Bad Request**: Validation errors or invalid data
- **409 Conflict**: Email/phone already exists
- **500 Internal Server Error**: Unexpected errors"""
    ),
    destroy=extend_schema(
        summary="Delete User",
        description="""Delete a user account with comprehensive validation and logging.

**Use Cases:**
- Remove user accounts
- Administrative account cleanup
- User account deactivation

**Error Handling:**
- **404 Not Found**: User with specified ID does not exist
- **400 Bad Request**: Invalid user ID format
- **500 Internal Server Error**: Unexpected errors

**Response:**
- Confirmation of successful deletion
- Structured error responses with error codes and details

**Note:**
- This action is irreversible
- Associated data may be affected depending on business rules"""
    ),
    drivers=extend_schema(
        summary="Get All Drivers",
        description="""Retrieve all users with driver role with comprehensive validation and logging.

**Use Cases:**
- Get list of all available drivers
- Driver management and monitoring
- Administrative driver oversight

**Response:**
- Complete list of all drivers
- Performance metrics and metadata
- Structured error responses with error codes

**Performance:**
- Optimized queries for driver retrieval
- Query execution time tracking
- Comprehensive logging for monitoring"""
    ),
    riders=extend_schema(
        summary="Get All Riders",
        description="""Retrieve all users with rider role with comprehensive validation and logging.

**Use Cases:**
- Get list of all registered riders
- Rider management and monitoring
- Administrative rider oversight

**Response:**
- Complete list of all riders
- Performance metrics and metadata
- Structured error responses with error codes

**Performance:**
- Optimized queries for rider retrieval
- Query execution time tracking
- Comprehensive logging for monitoring"""
    )
)
class UserViewSet(viewsets.ModelViewSet):
    """
    ViewSet for User model with comprehensive validation and documentation
    """
    queryset = User.objects.all()
    serializer_class = UserSerializer
    permission_classes = [AllowAnyOrAdmin]  # Allow registration for all, admin for others
    pagination_class = UserPagination
    filter_backends = [DjangoFilterBackend, SearchFilter, OrderingFilter]
    filterset_class = UserFilter
    search_fields = ['first_name', 'last_name', 'email']
    ordering_fields = ['first_name', 'last_name', 'id_user']
    ordering = ['-id_user']
    
    def get_serializer_class(self):
        if self.action == 'create':
            return UserCreateSerializer
        return UserSerializer
    
    def create(self, request, *args, **kwargs):
        """
        Create user with comprehensive error handling and structured responses
        """
        try:
            serializer = self.get_serializer(data=request.data)
            serializer.is_valid(raise_exception=True)
            user = serializer.save()
            
            # Return success response with user data
            response_data = {
                "success": True,
                "message": "User created successfully",
                "data": {
                    "id": user.id_user,
                    "role": user.role,
                    "first_name": user.first_name,
                    "last_name": user.last_name,
                    "email": user.email,
                    "phone_number": user.phone_number,
                    "created_at": user.django_user.date_joined.isoformat() if user.django_user else None
                }
            }
            
            return Response(response_data, status=status.HTTP_201_CREATED)
            
        except UserCreationError as e:
            # Handle our custom errors
            error_response = {
                "success": False,
                "message": e.message,
                "error_code": e.error_code,
                "details": e.details,
                "timestamp": datetime.now().isoformat()
            }
            
            # Determine appropriate HTTP status code based on error type
            if e.error_code in ["EMAIL_EXISTS", "PHONE_EXISTS", "USERNAME_EXISTS"]:
                status_code = status.HTTP_409_CONFLICT
            elif e.error_code == "VALIDATION_ERROR":
                status_code = status.HTTP_400_BAD_REQUEST
            elif e.error_code == "DATA_CONFLICT":
                status_code = status.HTTP_409_CONFLICT
            else:
                status_code = status.HTTP_500_INTERNAL_SERVER_ERROR
            
            return Response(error_response, status=status_code)
            
        except Exception as e:
            # Handle unexpected errors
            error_response = {
                "success": False,
                "message": "An unexpected error occurred while creating the user.",
                "error_code": "UNEXPECTED_ERROR",
                "details": {"error": str(e)},
                "timestamp": datetime.now().isoformat()
            }
            
            return Response(error_response, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
    
    def list(self, request, *args, **kwargs):
        """
        List users with comprehensive validation, logging, and error handling
        """
        logger = logging.getLogger(__name__)
        
        try:
            # Log the request
            logger.info(f"User list request received - IP: {request.META.get('REMOTE_ADDR', 'Unknown')}, "
                       f"Params: {dict(request.query_params)}")
            
            # Validate query parameters
            page_size = request.query_params.get('page_size')
            if page_size:
                try:
                    page_size_int = int(page_size)
                    if page_size_int > 50:
                        logger.warning(f"Page size too large: {page_size_int}, capping at 50")
                        request.query_params = request.query_params.copy()
                        request.query_params['page_size'] = '50'
                except ValueError:
                    logger.warning(f"Invalid page_size parameter: {page_size}")
                    return Response({
                        "success": False,
                        "message": "Invalid page_size parameter. Must be a number.",
                        "error_code": "INVALID_PAGE_SIZE",
                        "details": {"page_size": page_size},
                        "timestamp": datetime.now().isoformat()
                    }, status=status.HTTP_400_BAD_REQUEST)
            
            # Validate role parameter
            role = request.query_params.get('role')
            if role and role not in ['admin', 'rider', 'driver']:
                logger.warning(f"Invalid role parameter: {role}")
                return Response({
                    "success": False,
                    "message": "Invalid role parameter. Must be one of: admin, rider, driver",
                    "error_code": "INVALID_ROLE",
                    "details": {"role": role, "valid_roles": ['admin', 'rider', 'driver']},
                    "timestamp": datetime.now().isoformat()
                }, status=status.HTTP_400_BAD_REQUEST)
            
            # Validate ordering parameter
            ordering = request.query_params.get('ordering')
            if ordering and ordering not in ['first_name', 'last_name', 'id_user', '-first_name', '-last_name', '-id_user']:
                logger.warning(f"Invalid ordering parameter: {ordering}")
                return Response({
                    "success": False,
                    "message": "Invalid ordering parameter. Must be one of: first_name, last_name, id_user, -first_name, -last_name, -id_user",
                    "error_code": "INVALID_ORDERING",
                    "details": {"ordering": ordering, "valid_options": ['first_name', 'last_name', 'id_user', '-first_name', '-last_name', '-id_user']},
                    "timestamp": datetime.now().isoformat()
                }, status=status.HTTP_400_BAD_REQUEST)
            
            # Get filtered queryset
            queryset = self.filter_queryset(self.get_queryset())
            
            # Log query performance
            start_time = datetime.now()
            page = self.paginate_queryset(queryset)
            end_time = datetime.now()
            query_time = (end_time - start_time).total_seconds()
            
            if page is not None:
                serializer = self.get_serializer(page, many=True, context={'request': request})
                paginated_response = self.get_paginated_response(serializer.data)
                
                # Add metadata to response
                response_data = paginated_response.data
                response_data['metadata'] = {
                    "query_time_seconds": round(query_time, 3),
                    "total_results": queryset.count(),
                    "filters_applied": {
                        "role": role,
                        "search": request.query_params.get('search'),
                        "ordering": ordering
                    },
                    "timestamp": datetime.now().isoformat()
                }
                
                logger.info(f"User list request completed successfully - "
                           f"Results: {len(page)}, Query time: {query_time:.3f}s")
                
                return Response(response_data)
            
            # Non-paginated response
            serializer = self.get_serializer(queryset, many=True, context={'request': request})
            
            response_data = {
                "results": serializer.data,
                "metadata": {
                    "query_time_seconds": round(query_time, 3),
                    "total_results": queryset.count(),
                    "filters_applied": {
                        "role": role,
                        "search": request.query_params.get('search'),
                        "ordering": ordering
                    },
                    "timestamp": datetime.now().isoformat()
                }
            }
            
            logger.info(f"User list request completed successfully - "
                       f"Results: {len(serializer.data)}, Query time: {query_time:.3f}s")
            
            return Response(response_data)
            
        except Exception as e:
            logger.error(f"Unexpected error in user list: {str(e)}", exc_info=True)
            error_response = {
                "success": False,
                "message": "An unexpected error occurred while retrieving users.",
                "error_code": "UNEXPECTED_ERROR",
                "details": {"error": str(e)},
                "timestamp": datetime.now().isoformat()
            }
            
            return Response(error_response, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
    
    def retrieve(self, request, *args, **kwargs):
        """
        Retrieve a specific user with comprehensive validation and logging
        """
        logger = logging.getLogger(__name__)
        
        try:
            # Log the request
            user_id = kwargs.get('pk')
            logger.info(f"User retrieve request received - ID: {user_id}, IP: {request.META.get('REMOTE_ADDR', 'Unknown')}")
            
            # Validate user ID
            if not user_id:
                logger.warning("User retrieve request with missing ID")
                return Response({
                    "success": False,
                    "message": "User ID is required.",
                    "error_code": "MISSING_USER_ID",
                    "details": {"user_id": user_id},
                    "timestamp": datetime.now().isoformat()
                }, status=status.HTTP_400_BAD_REQUEST)
            
            # Check if user exists
            try:
                user = self.get_object()
            except User.DoesNotExist:
                logger.warning(f"User not found with ID: {user_id}")
                return Response({
                    "success": False,
                    "message": "User not found.",
                    "error_code": "USER_NOT_FOUND",
                    "details": {"user_id": user_id},
                    "timestamp": datetime.now().isoformat()
                }, status=status.HTTP_404_NOT_FOUND)
            
            # Serialize user data
            serializer = self.get_serializer(user, context={'request': request})
            
            # Log successful retrieval
            logger.info(f"User retrieved successfully - ID: {user_id}, Role: {user.role}")
            
            # Return success response with metadata
            response_data = {
                "success": True,
                "message": "User retrieved successfully",
                "data": serializer.data,
                "metadata": {
                    "user_id": user.id_user,
                    "role": user.role,
                    "timestamp": datetime.now().isoformat()
                }
            }
            
            return Response(response_data, status=status.HTTP_200_OK)
            
        except Exception as e:
            logger.error(f"Unexpected error retrieving user: {str(e)}", exc_info=True)
            error_response = {
                "success": False,
                "message": "An unexpected error occurred while retrieving the user.",
                "error_code": "UNEXPECTED_ERROR",
                "details": {"error": str(e)},
                "timestamp": datetime.now().isoformat()
            }
            
            return Response(error_response, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
    
    def update(self, request, *args, **kwargs):
        """
        Update user with comprehensive validation and logging
        """
        logger = logging.getLogger(__name__)
        
        try:
            user_id = kwargs.get('pk')
            logger.info(f"User update request received - ID: {user_id}, IP: {request.META.get('REMOTE_ADDR', 'Unknown')}")
            
            # Check if user exists
            try:
                user = self.get_object()
            except User.DoesNotExist:
                logger.warning(f"User not found for update - ID: {user_id}")
                return Response({
                    "success": False,
                    "message": "User not found.",
                    "error_code": "USER_NOT_FOUND",
                    "details": {"user_id": user_id},
                    "timestamp": datetime.now().isoformat()
                }, status=status.HTTP_404_NOT_FOUND)
            
            # Validate and update user
            serializer = self.get_serializer(user, data=request.data)
            if serializer.is_valid():
                # Check if password is being updated
                password_updated = 'password' in request.data
                
                updated_user = serializer.save()
                
                if password_updated:
                    logger.info(f"User updated successfully with password change - ID: {user_id}, Role: {updated_user.role}")
                else:
                    logger.info(f"User updated successfully - ID: {user_id}, Role: {updated_user.role}")
                
                response_data = {
                    "success": True,
                    "message": "User updated successfully",
                    "data": {
                        "id": updated_user.id_user,
                        "role": updated_user.role,
                        "first_name": updated_user.first_name,
                        "last_name": updated_user.last_name,
                        "email": updated_user.email,
                        "phone_number": updated_user.phone_number,
                        "updated_at": datetime.now().isoformat()
                    },
                    "metadata": {
                        "password_updated": password_updated,
                        "timestamp": datetime.now().isoformat()
                    }
                }
                
                return Response(response_data, status=status.HTTP_200_OK)
            else:
                logger.warning(f"User update validation failed - ID: {user_id}, Errors: {serializer.errors}")
                return Response({
                    "success": False,
                    "message": "Validation failed.",
                    "error_code": "VALIDATION_ERROR",
                    "details": serializer.errors,
                    "timestamp": datetime.now().isoformat()
                }, status=status.HTTP_400_BAD_REQUEST)
                
        except Exception as e:
            logger.error(f"Unexpected error updating user: {str(e)}", exc_info=True)
            error_response = {
                "success": False,
                "message": "An unexpected error occurred while updating the user.",
                "error_code": "UNEXPECTED_ERROR",
                "details": {"error": str(e)},
                "timestamp": datetime.now().isoformat()
            }
            
            return Response(error_response, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
    
    def partial_update(self, request, *args, **kwargs):
        """
        Partially update user with comprehensive validation and logging
        """
        logger = logging.getLogger(__name__)
        
        try:
            user_id = kwargs.get('pk')
            logger.info(f"User partial update request received - ID: {user_id}, IP: {request.META.get('REMOTE_ADDR', 'Unknown')}")
            
            # Check if user exists
            try:
                user = self.get_object()
            except User.DoesNotExist:
                logger.warning(f"User not found for partial update - ID: {user_id}")
                return Response({
                    "success": False,
                    "message": "User not found.",
                    "error_code": "USER_NOT_FOUND",
                    "details": {"user_id": user_id},
                    "timestamp": datetime.now().isoformat()
                }, status=status.HTTP_404_NOT_FOUND)
            
            # Validate and partially update user
            serializer = self.get_serializer(user, data=request.data, partial=True)
            if serializer.is_valid():
                # Check if password is being updated
                password_updated = 'password' in request.data
                
                updated_user = serializer.save()
                
                if password_updated:
                    logger.info(f"User partially updated successfully with password change - ID: {user_id}, Updated fields: {list(request.data.keys())}")
                else:
                    logger.info(f"User partially updated successfully - ID: {user_id}, Updated fields: {list(request.data.keys())}")
                
                response_data = {
                    "success": True,
                    "message": "User updated successfully",
                    "data": {
                        "id": updated_user.id_user,
                        "role": updated_user.role,
                        "first_name": updated_user.first_name,
                        "last_name": updated_user.last_name,
                        "email": updated_user.email,
                        "phone_number": updated_user.phone_number,
                        "updated_at": datetime.now().isoformat()
                    },
                    "metadata": {
                        "updated_fields": list(request.data.keys()),
                        "password_updated": password_updated,
                        "timestamp": datetime.now().isoformat()
                    }
                }
                
                return Response(response_data, status=status.HTTP_200_OK)
            else:
                logger.warning(f"User partial update validation failed - ID: {user_id}, Errors: {serializer.errors}")
                return Response({
                    "success": False,
                    "message": "Validation failed.",
                    "error_code": "VALIDATION_ERROR",
                    "details": serializer.errors,
                    "timestamp": datetime.now().isoformat()
                }, status=status.HTTP_400_BAD_REQUEST)
                
        except Exception as e:
            logger.error(f"Unexpected error partially updating user: {str(e)}", exc_info=True)
            error_response = {
                "success": False,
                "message": "An unexpected error occurred while updating the user.",
                "error_code": "UNEXPECTED_ERROR",
                "details": {"error": str(e)},
                "timestamp": datetime.now().isoformat()
            }
            
            return Response(error_response, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
    
    def destroy(self, request, *args, **kwargs):
        """
        Delete user with comprehensive validation and logging
        """
        logger = logging.getLogger(__name__)
        
        try:
            user_id = kwargs.get('pk')
            logger.info(f"User delete request received - ID: {user_id}, IP: {request.META.get('REMOTE_ADDR', 'Unknown')}")
            
            # Check if user exists
            try:
                user = self.get_object()
            except User.DoesNotExist:
                logger.warning(f"User not found for deletion - ID: {user_id}")
                return Response({
                    "success": False,
                    "message": "User not found.",
                    "error_code": "USER_NOT_FOUND",
                    "details": {"user_id": user_id},
                    "timestamp": datetime.now().isoformat()
                }, status=status.HTTP_404_NOT_FOUND)
            
            # Store user info for logging
            user_info = {
                "id": user.id_user,
                "role": user.role,
                "email": user.email,
                "first_name": user.first_name,
                "last_name": user.last_name
            }
            
            # Delete the user
            user.delete()
            
            logger.info(f"User deleted successfully - ID: {user_id}, Role: {user_info['role']}, Email: {user_info['email']}")
            
            response_data = {
                "success": True,
                "message": "User deleted successfully",
                "data": {
                    "deleted_user": user_info,
                    "deleted_at": datetime.now().isoformat()
                },
                "timestamp": datetime.now().isoformat()
            }
            
            return Response(response_data, status=status.HTTP_200_OK)
            
        except Exception as e:
            logger.error(f"Unexpected error deleting user: {str(e)}", exc_info=True)
            error_response = {
                "success": False,
                "message": "An unexpected error occurred while deleting the user.",
                "error_code": "UNEXPECTED_ERROR",
                "details": {"error": str(e)},
                "timestamp": datetime.now().isoformat()
            }
            
            return Response(error_response, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
    
    @action(detail=False, methods=['get'])
    def drivers(self, request):
        """
        Get all drivers with comprehensive validation and logging
        """
        logger = logging.getLogger(__name__)
        
        try:
            # Log the request
            logger.info(f"Drivers list request received - IP: {request.META.get('REMOTE_ADDR', 'Unknown')}")
            
            # Get all drivers
            drivers = User.objects.filter(role='driver')
            
            # Log query performance
            start_time = datetime.now()
            serializer = self.get_serializer(drivers, many=True, context={'request': request})
            end_time = datetime.now()
            query_time = (end_time - start_time).total_seconds()
            
            logger.info(f"Drivers list request completed successfully - "
                       f"Results: {len(serializer.data)}, Query time: {query_time:.3f}s")
            
            response_data = {
                "success": True,
                "message": "Drivers retrieved successfully",
                "data": serializer.data,
                "metadata": {
                    "total_drivers": len(serializer.data),
                    "query_time_seconds": round(query_time, 3),
                    "timestamp": datetime.now().isoformat()
                }
            }
            
            return Response(response_data, status=status.HTTP_200_OK)
            
        except Exception as e:
            logger.error(f"Unexpected error retrieving drivers: {str(e)}", exc_info=True)
            error_response = {
                "success": False,
                "message": "An unexpected error occurred while retrieving drivers.",
                "error_code": "UNEXPECTED_ERROR",
                "details": {"error": str(e)},
                "timestamp": datetime.now().isoformat()
            }
            
            return Response(error_response, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
    
    @action(detail=False, methods=['get'])
    def riders(self, request):
        """
        Get all riders with comprehensive validation and logging
        """
        logger = logging.getLogger(__name__)
        
        try:
            # Log the request
            logger.info(f"Riders list request received - IP: {request.META.get('REMOTE_ADDR', 'Unknown')}")
            
            # Get all riders
            riders = User.objects.filter(role='rider')
            
            # Log query performance
            start_time = datetime.now()
            serializer = self.get_serializer(riders, many=True, context={'request': request})
            end_time = datetime.now()
            query_time = (end_time - start_time).total_seconds()
            
            logger.info(f"Riders list request completed successfully - "
                       f"Results: {len(serializer.data)}, Query time: {query_time:.3f}s")
            
            response_data = {
                "success": True,
                "message": "Riders retrieved successfully",
                "data": serializer.data,
                "metadata": {
                    "total_riders": len(serializer.data),
                    "query_time_seconds": round(query_time, 3),
                    "timestamp": datetime.now().isoformat()
                }
            }
            
            return Response(response_data, status=status.HTTP_200_OK)
            
        except Exception as e:
            logger.error(f"Unexpected error retrieving riders: {str(e)}", exc_info=True)
            error_response = {
                "success": False,
                "message": "An unexpected error occurred while retrieving riders.",
                "error_code": "UNEXPECTED_ERROR",
                "details": {"error": str(e)},
                "timestamp": datetime.now().isoformat()
            }
            
            return Response(error_response, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


@method_decorator(csrf_exempt, name='dispatch')
@extend_schema_view(
    create=extend_schema(
        summary="Create Ride",
        description="""Create a new ride request with comprehensive validation and automatic event logging.

**Authentication Required:** Admin users only

**Features:**
- Create ride requests for any rider
- Automatic event creation ("Ride requested by [Rider Name]")
- Comprehensive input validation
- GPS coordinate validation
- Future pickup time validation
- Performance optimized with minimal queries

**Required Fields:**
- **id_rider**: ID of the rider requesting the ride
- **pickup_latitude/longitude**: GPS coordinates for pickup location
- **dropoff_latitude/longitude**: GPS coordinates for dropoff location
- **pickup_time**: When the ride should be picked up (must be in the future)

**Optional Fields:**
- **status**: Will default to "requested"
- **driver_id**: Will be null (no driver assigned initially)

**Validation Rules:**
- GPS coordinates must be valid (latitude: -90 to 90, longitude: -180 to 180)
- Pickup time must be in the future
- Rider must exist in the system
- All coordinates are required

**Use Cases:**
- Create ride requests for customers
- Test the ride booking system
- Simulate ride requests from different locations
- Create rides for different time periods""",
        examples=[
            OpenApiExample(
                "New York Ride",
                summary="Manhattan to Central Park",
                description="A typical NYC ride from Wall Street to Central Park area",
                value={
                    "id_rider": 2,
                    "pickup_latitude": 40.7128,
                    "pickup_longitude": -74.0060,
                    "dropoff_latitude": 40.7589,
                    "dropoff_longitude": -73.9851,
                    "pickup_time": "2025-10-24T15:00:00Z"
                },
                request_only=True,
            ),
            OpenApiExample(
                "London Ride",
                summary="Westminster to London Bridge",
                description="A London ride from Westminster to London Bridge area",
                value={
                    "id_rider": 2,
                    "pickup_latitude": 51.5074,
                    "pickup_longitude": -0.1278,
                    "dropoff_latitude": 51.5014,
                    "dropoff_longitude": -0.1419,
                    "pickup_time": "2025-10-24T16:00:00Z"
                },
                request_only=True,
            ),
            OpenApiExample(
                "Tokyo Ride",
                summary="Shibuya to Tokyo Skytree",
                description="A Tokyo ride from Shibuya to Tokyo Skytree area",
                value={
                    "id_rider": 2,
                    "pickup_latitude": 35.6762,
                    "pickup_longitude": 139.6503,
                    "dropoff_latitude": 35.6586,
                    "dropoff_longitude": 139.7454,
                    "pickup_time": "2025-10-24T17:00:00Z"
                },
                request_only=True,
            ),
            OpenApiExample(
                "Paris Ride",
                summary="Eiffel Tower to Louvre",
                description="A Paris ride from Eiffel Tower to Louvre Museum",
                value={
                    "id_rider": 2,
                    "pickup_latitude": 48.8566,
                    "pickup_longitude": 2.3522,
                    "dropoff_latitude": 48.8606,
                    "dropoff_longitude": 2.3376,
                    "pickup_time": "2025-10-24T18:00:00Z"
                },
                request_only=True,
            ),
            OpenApiExample(
                "Sydney Ride",
                summary="Opera House to Harbour Bridge",
                description="A Sydney ride from Opera House to Harbour Bridge area",
                value={
                    "id_rider": 2,
                    "pickup_latitude": -33.8568,
                    "pickup_longitude": 151.2153,
                    "dropoff_latitude": -33.8523,
                    "dropoff_longitude": 151.2108,
                    "pickup_time": "2025-10-24T19:00:00Z"
                },
                request_only=True,
            ),
        ]
    ),
    list=extend_schema(
        summary="List Rides",
        description="""Get a paginated list of rides with advanced filtering, sorting, and performance optimizations.

**🚀 Key Features:**
- **Distance Calculation**: Calculate distances from your location to all ride pickup points
- **Smart Sorting**: Sort rides by distance, pickup time, or creation date
- **Advanced Filtering**: Filter by status, dates, rider email, and more
- **Performance Optimized**: Uses only 2 database queries for maximum speed
- **Today's Events**: Includes ride events from the last 24 hours

**📍 Distance Calculation Examples:**
The API calculates distances using the Haversine formula. When you provide `lat` and `lon` parameters, it shows how far each ride's pickup location is from your coordinates. **Both parameters are optional** - if not provided, `distance_to_pickup` will be null.

**Test Coordinates for Different Cities:**
- **New York**: `lat=40.7150&lon=-74.0080` (near Manhattan)
- **London**: `lat=51.5100&lon=-0.1300` (near Westminster)
- **Tokyo**: `lat=35.6800&lon=139.6500` (near Shibuya)
- **Paris**: `lat=48.8600&lon=2.3500` (near Eiffel Tower)
- **Sydney**: `lat=-33.8700&lon=151.2100` (near Opera House)

**🎯 Example Usage:**
- **Basic request**: `GET /api/v1/rides/` (no coordinates needed)
- **With distance**: `?lat=40.7150&lon=-74.0080` (shows distances)
- **Find closest rides**: `?lat=40.7150&lon=-74.0080&sort_by=distance`
- **Filter by status**: `?status=requested&lat=40.7150&lon=-74.0080`
- **Today's rides only**: `?date_from=2025-10-24T00:00:00Z&date_to=2025-10-24T23:59:59Z`

**📊 Response Format:**
Each ride includes `distance_to_pickup` field showing kilometers from your location (null if no coordinates provided).""",
        parameters=[
            OpenApiParameter(
                name='status',
                type=OpenApiTypes.STR,
                location=OpenApiParameter.QUERY,
                description='Filter by ride status',
                enum=[choice[0] for choice in Ride.STATUS_CHOICES]
            ),
            OpenApiParameter(
                name='rider_email',
                type=OpenApiTypes.STR,
                location=OpenApiParameter.QUERY,
                description='Filter by rider email (partial match)'
            ),
            OpenApiParameter(
                name='date_from',
                type=OpenApiTypes.DATETIME,
                location=OpenApiParameter.QUERY,
                description='Filter rides created from this date (ISO 8601 format: YYYY-MM-DDTHH:MM:SSZ)',
                examples=[
                    OpenApiExample('Today Start', value='2025-10-24T00:00:00Z'),
                    OpenApiExample('Yesterday', value='2025-10-23T00:00:00Z'),
                ]
            ),
            OpenApiParameter(
                name='date_to',
                type=OpenApiTypes.DATETIME,
                location=OpenApiParameter.QUERY,
                description='Filter rides created until this date (ISO 8601 format: YYYY-MM-DDTHH:MM:SSZ)',
                examples=[
                    OpenApiExample('Today End', value='2025-10-24T23:59:59Z'),
                    OpenApiExample('End of Week', value='2025-10-27T23:59:59Z'),
                ]
            ),
            OpenApiParameter(
                name='pickup_time_from',
                type=OpenApiTypes.DATETIME,
                location=OpenApiParameter.QUERY,
                description='Filter rides with pickup time from this date (ISO 8601 format: YYYY-MM-DDTHH:MM:SSZ)',
                examples=[
                    OpenApiExample('Morning', value='2025-10-24T06:00:00Z'),
                    OpenApiExample('Afternoon', value='2025-10-24T12:00:00Z'),
                ]
            ),
            OpenApiParameter(
                name='pickup_time_to',
                type=OpenApiTypes.DATETIME,
                location=OpenApiParameter.QUERY,
                description='Filter rides with pickup time until this date (ISO 8601 format: YYYY-MM-DDTHH:MM:SSZ)',
                examples=[
                    OpenApiExample('Evening', value='2025-10-24T18:00:00Z'),
                    OpenApiExample('End of Day', value='2025-10-24T23:59:59Z'),
                ]
            ),
            OpenApiParameter(
                name='sort_by',
                type=OpenApiTypes.STR,
                location=OpenApiParameter.QUERY,
                description='Sort rides by field. Use with lat/lon for distance sorting.',
                enum=['pickup_time', 'distance', 'created_at'],
                examples=[
                    OpenApiExample('Distance', value='distance', description='Sort by distance (requires lat & lon)'),
                    OpenApiExample('Pickup Time', value='pickup_time', description='Sort by pickup time'),
                    OpenApiExample('Created Date', value='created_at', description='Sort by creation date'),
                ]
            ),
            OpenApiParameter(
                name='lat',
                type=OpenApiTypes.NUMBER,
                location=OpenApiParameter.QUERY,
                description='Latitude for distance calculation and sorting. Used with lon to calculate distances to all ride pickup locations. Optional - if not provided, distance_to_pickup will be null.',
                required=False,
                examples=[
                    OpenApiExample('New York', value=40.7150, description='Near Manhattan, NYC'),
                    OpenApiExample('London', value=51.5100, description='Near Westminster, London'),
                    OpenApiExample('Tokyo', value=35.6800, description='Near Shibuya, Tokyo'),
                    OpenApiExample('Paris', value=48.8600, description='Near Eiffel Tower, Paris'),
                    OpenApiExample('Sydney', value=-33.8700, description='Near Opera House, Sydney'),
                ]
            ),
            OpenApiParameter(
                name='lon',
                type=OpenApiTypes.NUMBER,
                location=OpenApiParameter.QUERY,
                description='Longitude for distance calculation and sorting. Used with lat to calculate distances to all ride pickup locations. Optional - if not provided, distance_to_pickup will be null.',
                required=False,
                examples=[
                    OpenApiExample('New York', value=-74.0080, description='Near Manhattan, NYC'),
                    OpenApiExample('London', value=-0.1300, description='Near Westminster, London'),
                    OpenApiExample('Tokyo', value=139.6500, description='Near Shibuya, Tokyo'),
                    OpenApiExample('Paris', value=2.3500, description='Near Eiffel Tower, Paris'),
                    OpenApiExample('Sydney', value=151.2100, description='Near Opera House, Sydney'),
                ]
            ),
            OpenApiParameter(
                name='page',
                type=OpenApiTypes.INT,
                location=OpenApiParameter.QUERY,
                description='Page number for pagination'
            ),
            OpenApiParameter(
                name='page_size',
                type=OpenApiTypes.INT,
                location=OpenApiParameter.QUERY,
                description='Number of items per page (max 100)'
            ),
        ]
    )
)
class RideViewSet(viewsets.ModelViewSet):
    """
    Advanced ViewSet for Ride model with performance optimizations
    """
    queryset = Ride.objects.all()
    serializer_class = RideSerializer
    permission_classes = [IsAdmin]  # Only admin can access rides
    pagination_class = StandardResultsSetPagination
    filter_backends = [DjangoFilterBackend, SearchFilter, OrderingFilter]
    filterset_class = RideFilter
    search_fields = ['id_rider__first_name', 'id_rider__last_name', 'id_driver__first_name', 'id_driver__last_name']
    ordering_fields = ['created_at', 'pickup_time', 'status']
    ordering = ['-created_at']
    
    def get_serializer_class(self):
        if self.action == 'create':
            return RideCreateSerializer
        elif self.action in ['update_status', 'partial_update']:
            return RideStatusUpdateSerializer
        return RideSerializer
    
    def get_queryset(self):
        """
        Optimized queryset with select_related and prefetch_related for performance
        Ensures only 2 queries total: 1 for rides+users, 1 for all events
        """
        # Base queryset with optimizations - no user filtering for development
        queryset = Ride.objects.select_related(
            'id_rider', 'id_driver'
        ).prefetch_related(
            # Prefetch all events for the ride - single query for all events
            Prefetch(
                'events',
                queryset=RideEvent.objects.all().order_by('-created_at')
            )
        )
        
        return queryset
    
    def list(self, request, *args, **kwargs):
        """
        Optimized list method with custom sorting, performance enhancements, and comprehensive logging
        """
        logger = logging.getLogger(__name__)
        
        try:
            # Log request details
            logger.info(f"Rides list requested by user: {request.user}")
            logger.info(f"Request parameters: {request.query_params}")
            
            # Validate pagination parameters
            page_size = request.query_params.get('page_size')
            if page_size:
                try:
                    page_size = int(page_size)
                    if page_size > 100:
                        logger.warning(f"Page size {page_size} exceeds maximum, capping at 100")
                        page_size = 100
                except ValueError:
                    logger.warning(f"Invalid page_size parameter: {page_size}")
                    return Response(
                        {"error": "Invalid page_size parameter. Must be an integer."},
                        status=status.HTTP_400_BAD_REQUEST
                    )
            
            # Validate sorting parameters
            sort_by = request.query_params.get('sort_by')
            if sort_by and sort_by not in ['pickup_time', 'distance', 'created_at']:
                logger.warning(f"Invalid sort_by parameter: {sort_by}")
                return Response(
                    {"error": "Invalid sort_by parameter. Must be 'pickup_time', 'distance', or 'created_at'."},
                    status=status.HTTP_400_BAD_REQUEST
                )
            
            # Validate GPS coordinates for distance sorting
            lat = request.query_params.get('lat')
            lon = request.query_params.get('lon')
            if sort_by == 'distance':
                if not lat or not lon:
                    logger.warning("Distance sorting requested but GPS coordinates missing")
                    return Response(
                        {"error": "GPS coordinates (lat, lon) are required for distance sorting."},
                        status=status.HTTP_400_BAD_REQUEST
                    )
                try:
                    lat_float = float(lat)
                    lon_float = float(lon)
                    if not (-90 <= lat_float <= 90) or not (-180 <= lon_float <= 180):
                        logger.warning(f"Invalid GPS coordinates: lat={lat}, lon={lon}")
                        return Response(
                            {"error": "Invalid GPS coordinates. Latitude must be between -90 and 90, longitude between -180 and 180."},
                            status=status.HTTP_400_BAD_REQUEST
                        )
                except (ValueError, TypeError):
                    logger.warning(f"Invalid GPS coordinates format: lat={lat}, lon={lon}")
                    return Response(
                        {"error": "Invalid GPS coordinates format. Must be valid numbers."},
                        status=status.HTTP_400_BAD_REQUEST
                    )
            
            # Get filtered queryset
            queryset = self.filter_queryset(self.get_queryset())
            logger.info(f"Filtered queryset count: {queryset.count()}")
            
            # Handle distance sorting
            if sort_by == 'distance' and lat and lon:
                try:
                    lat_float = float(lat)
                    lon_float = float(lon)
                    logger.info(f"Applying distance sorting from coordinates: {lat_float}, {lon_float}")
                    
                    # Check if dataset is too large for Python sorting
                    queryset_count = queryset.count()
                    max_sort_limit = 10000  # Configurable limit for memory safety
                    
                    if queryset_count > max_sort_limit:
                        logger.warning(f"Dataset too large for distance sorting: {queryset_count} records (limit: {max_sort_limit})")
                        return Response(
                            {
                                "error": f"Too many results for distance sorting. Please add filters to reduce results to under {max_sort_limit}.",
                                "current_count": queryset_count,
                                "max_limit": max_sort_limit,
                                "suggestion": "Try adding filters like status, date_from, date_to, or pickup_time_from to reduce the dataset size."
                            },
                            status=status.HTTP_400_BAD_REQUEST
                        )
                    
                    # Sort by distance using Python (optimized for reasonable dataset sizes)
                    logger.info(f"Sorting {queryset_count} records by distance")
                    rides_list = list(queryset)
                    rides_list.sort(key=lambda ride: ride.calculate_distance_to_pickup(lat_float, lon_float))
                    
                    # Manual pagination for distance sorting
                    page = self.paginate_queryset(rides_list)
                    if page is not None:
                        serializer = self.get_serializer(page, many=True, context={'request': request})
                        result = self.get_paginated_response(serializer.data)
                        logger.info(f"Rides list successful with distance sorting. Count: {len(serializer.data)}")
                        return result
                    
                    serializer = self.get_serializer(rides_list, many=True, context={'request': request})
                    logger.info(f"Rides list successful with distance sorting. Count: {len(serializer.data)}")
                    return Response(serializer.data)
                except Exception as e:
                    logger.error(f"Error in distance sorting: {str(e)}")
                    return Response(
                        {"error": "Error occurred during distance sorting"},
                        status=status.HTTP_500_INTERNAL_SERVER_ERROR
                    )
            
            # Standard pagination for other sorting options
            page = self.paginate_queryset(queryset)
            if page is not None:
                serializer = self.get_serializer(page, many=True, context={'request': request})
                result = self.get_paginated_response(serializer.data)
                logger.info(f"Rides list successful. Count: {len(serializer.data)}")
                return result
            
            serializer = self.get_serializer(queryset, many=True, context={'request': request})
            logger.info(f"Rides list successful. Count: {len(serializer.data)}")
            return Response(serializer.data)
            
        except Exception as e:
            logger.error(f"Error in rides list: {str(e)}")
            return Response(
                {"error": "Internal server error occurred while fetching rides"},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )


@method_decorator(csrf_exempt, name='dispatch')
@extend_schema_view(
    list=extend_schema(
        summary="List Ride Events",
        description="""Get all ride events with advanced filtering, pagination, and sorting capabilities.

**Authentication Required:** Admin users only

**Features:**
- Filter events by specific ride ID
- Pagination support (20 items per page default)
- Sort by creation date (newest first by default)
- Comprehensive logging and error handling

**Use Cases:**
- View all events for a specific ride
- Monitor ride activity and status changes
- Audit trail for ride management
- Debug ride issues

**Performance:**
- Optimized queries with proper indexing
- Pagination to handle large event datasets
- Efficient filtering and sorting

**Error Handling:**
- **401 Unauthorized**: Authentication required
- **403 Forbidden**: Admin access required
- **400 Bad Request**: Invalid parameters
- **500 Internal Server Error**: Unexpected errors""",
        parameters=[
            OpenApiParameter(
                name='id_ride__id_ride',
                type=OpenApiTypes.INT,
                location=OpenApiParameter.QUERY,
                description='Filter by specific ride ID'
            ),
            OpenApiParameter(
                name='page',
                type=OpenApiTypes.INT,
                location=OpenApiParameter.QUERY,
                description='Page number for pagination (default: 1)'
            ),
            OpenApiParameter(
                name='page_size',
                type=OpenApiTypes.INT,
                location=OpenApiParameter.QUERY,
                description='Number of items per page (max 100, default: 20)'
            ),
            OpenApiParameter(
                name='ordering',
                type=OpenApiTypes.STR,
                location=OpenApiParameter.QUERY,
                description='Sort by field (created_at, -created_at, id_ride_event, -id_ride_event)',
                enum=['created_at', '-created_at', 'id_ride_event', '-id_ride_event']
            ),
        ]
    ),
    create=extend_schema(
        summary="Create Ride Event",
        description="""Create a custom event for a specific ride with comprehensive validation and logging.

**Authentication Required:** Admin users only

**Features:**
- Create custom events for any ride
- Automatic timestamp generation
- Comprehensive input validation
- Detailed logging and error handling

**Use Cases:**
- Add manual notes to rides
- Log custom status updates
- Create maintenance events
- Add administrative comments

**Validation:**
- Ride ID must exist and be valid
- Description is required (max 255 characters)
- Automatic timestamp assignment

**Error Handling:**
- **401 Unauthorized**: Authentication required
- **403 Forbidden**: Admin access required
- **400 Bad Request**: Invalid data or missing fields
- **404 Not Found**: Ride ID does not exist
- **500 Internal Server Error**: Unexpected errors""",
        request=RideEventSerializer,
        responses={
            201: RideEventSerializer,
            400: OpenApiTypes.OBJECT,
            401: OpenApiTypes.OBJECT,
            403: OpenApiTypes.OBJECT,
            404: OpenApiTypes.OBJECT,
            500: OpenApiTypes.OBJECT
        }
    )
)
class RideEventViewSet(viewsets.ModelViewSet):
    """
    ViewSet for RideEvent model - supports both reading and creating events
    Admin access required for all operations
    """
    queryset = RideEvent.objects.all()
    serializer_class = RideEventSerializer
    permission_classes = [IsAdmin]  # Only admin can access ride events
    filter_backends = [DjangoFilterBackend, OrderingFilter]
    filterset_fields = ['id_ride__id_ride']
    ordering_fields = ['created_at', 'id_ride_event']
    ordering = ['-created_at']
    pagination_class = StandardResultsSetPagination
    
    def get_queryset(self):
        """Return all events for development - no user filtering"""
        return self.queryset
    
    def list(self, request, *args, **kwargs):
        """List ride events with comprehensive logging and validation"""
        logger = logging.getLogger(__name__)
        
        try:
            # Log request details
            logger.info(f"Ride events list requested by user: {request.user}")
            logger.info(f"Request parameters: {request.query_params}")
            
            # Validate pagination parameters
            page_size = request.query_params.get('page_size')
            if page_size:
                try:
                    page_size = int(page_size)
                    if page_size > 100:
                        logger.warning(f"Page size {page_size} exceeds maximum, capping at 100")
                        page_size = 100
                except ValueError:
                    logger.warning(f"Invalid page_size parameter: {page_size}")
                    return Response(
                        {"error": "Invalid page_size parameter. Must be an integer."},
                        status=status.HTTP_400_BAD_REQUEST
                    )
            
            # Validate ordering parameter
            ordering = request.query_params.get('ordering')
            if ordering and ordering not in ['created_at', '-created_at', 'id_ride_event', '-id_ride_event']:
                logger.warning(f"Invalid ordering parameter: {ordering}")
                return Response(
                    {"error": "Invalid ordering parameter. Must be 'created_at', '-created_at', 'id_ride_event', or '-id_ride_event'."},
                    status=status.HTTP_400_BAD_REQUEST
                )
            
            # Get filtered and ordered queryset using DRF's built-in methods
            queryset = self.filter_queryset(self.get_queryset())
            logger.info(f"Filtered queryset count: {queryset.count()}")
            
            # Apply pagination
            page = self.paginate_queryset(queryset)
            if page is not None:
                serializer = self.get_serializer(page, many=True)
                result = self.get_paginated_response(serializer.data)
                logger.info(f"Ride events list successful. Count: {len(serializer.data)}")
                return result
            
            serializer = self.get_serializer(queryset, many=True)
            logger.info(f"Ride events list successful. Count: {len(serializer.data)}")
            return Response(serializer.data)
            
        except Exception as e:
            logger.error(f"Error in ride events list: {str(e)}")
            return Response(
                {"error": "Internal server error occurred while fetching ride events"},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )
    
    def create(self, request, *args, **kwargs):
        """Create ride event with comprehensive validation and logging"""
        logger = logging.getLogger(__name__)
        
        try:
            # Log request details
            logger.info(f"Ride event creation requested by user: {request.user}")
            logger.info(f"Request data: {request.data}")
            
            # Validate required fields
            if not request.data.get('description'):
                logger.warning("Ride event creation failed: Missing description")
                return Response(
                    {"error": "Description is required"},
                    status=status.HTTP_400_BAD_REQUEST
                )
            
            if not request.data.get('id_ride'):
                logger.warning("Ride event creation failed: Missing id_ride")
                return Response(
                    {"error": "Ride ID (id_ride) is required"},
                    status=status.HTTP_400_BAD_REQUEST
                )
            
            # Validate ride exists
            try:
                ride_id = int(request.data.get('id_ride'))
                from .models import Ride
                ride = Ride.objects.get(id_ride=ride_id)
                logger.info(f"Validated ride exists: {ride_id}")
            except (ValueError, Ride.DoesNotExist):
                logger.warning(f"Ride event creation failed: Invalid or non-existent ride ID: {request.data.get('id_ride')}")
                return Response(
                    {"error": "Invalid or non-existent ride ID"},
                    status=status.HTTP_404_NOT_FOUND
                )
            
            # Validate description length
            description = request.data.get('description')
            if len(description) > 255:
                logger.warning(f"Ride event creation failed: Description too long ({len(description)} chars)")
                return Response(
                    {"error": "Description must be 255 characters or less"},
                    status=status.HTTP_400_BAD_REQUEST
                )
            
            # Create the event
            serializer = self.get_serializer(data=request.data)
            if serializer.is_valid():
                event = serializer.save()
                logger.info(f"Ride event created successfully: {event.id_ride_event}")
                return Response(serializer.data, status=status.HTTP_201_CREATED)
            else:
                logger.warning(f"Ride event creation failed: Validation errors: {serializer.errors}")
                return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
                
        except Exception as e:
            logger.error(f"Error in ride event creation: {str(e)}", exc_info=True)
            return Response(
                {"error": f"Internal server error occurred while creating ride event: {str(e)}"},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )


class LoginView(viewsets.GenericViewSet):
    """
    Login view for user authentication
    """
    serializer_class = LoginSerializer
    permission_classes = [AllowAny]
    
    @extend_schema(
        summary="User Login",
        description="""Authenticate user and return authentication token.

**Authentication:**
- Email and password required
- Returns authentication token for API access
- Token must be included in Authorization header for protected endpoints

**Use Cases:**
- User login for API access
- Get authentication token
- Access protected endpoints

**Error Handling:**
- **400 Bad Request**: Missing email or password
- **401 Unauthorized**: Invalid credentials
- **500 Internal Server Error**: Unexpected errors

**Response:**
- Authentication token
- User information
- Token expiration details""",
        request=LoginSerializer,
        examples=[
            OpenApiExample(
                "Admin Login",
                summary="Admin User Login",
                description="Login with admin credentials",
                value={
                    "email": "david@yahoo.com",
                    "password": "JeromeJerome2015$"
                },
                request_only=True,
            ),
            OpenApiExample(
                "Regular User Login",
                summary="Regular User Login",
                description="Login with regular user credentials",
                value={
                    "email": "john.doe@example.com",
                    "password": "SecurePass123!"
                },
                request_only=True,
            )
        ]
    )
    def create(self, request):
        """
        User login endpoint with comprehensive validation and logging
        """
        logger = logging.getLogger(__name__)
        
        try:
            # Log the request with detailed information
            client_ip = request.META.get('REMOTE_ADDR', 'Unknown')
            user_agent = request.META.get('HTTP_USER_AGENT', 'Unknown')
            logger.info(f"Login attempt from IP: {client_ip}, User-Agent: {user_agent}")
            
            # Validate required fields
            email = request.data.get('email')
            password = request.data.get('password')
            
            if not email or not password:
                logger.warning(f"Login attempt with missing credentials from IP: {client_ip}")
                return Response({
                    "success": False,
                    "message": "Email and password are required.",
                    "error_code": "MISSING_CREDENTIALS",
                    "details": {"email": email, "password": "***"},
                    "timestamp": datetime.now().isoformat()
                }, status=status.HTTP_400_BAD_REQUEST)
            
            # Log email validation
            logger.info(f"Attempting login for email: {email}")
            
            # Authenticate user
            user = authenticate(username=email, password=password)
            
            if not user:
                logger.warning(f"Login failed - invalid credentials for email: {email} from IP: {client_ip}")
                return Response({
                    "success": False,
                    "message": "Invalid email or password.",
                    "error_code": "INVALID_CREDENTIALS",
                    "details": {"email": email},
                    "timestamp": datetime.now().isoformat()
                }, status=status.HTTP_401_UNAUTHORIZED)
            
            # Log successful authentication
            logger.info(f"Authentication successful for Django user ID: {user.id}")
            
            # Get or create token
            token, created = Token.objects.get_or_create(user=user)
            logger.info(f"Token {'created' if created else 'retrieved'} for user: {email}")
            
            # Get custom user data
            try:
                custom_user = User.objects.get(django_user=user)
                user_data = {
                    "id": custom_user.id_user,
                    "role": custom_user.role,
                    "first_name": custom_user.first_name,
                    "last_name": custom_user.last_name,
                    "email": custom_user.email,
                    "phone_number": custom_user.phone_number
                }
                logger.info(f"Custom user data retrieved - ID: {custom_user.id_user}, Role: {custom_user.role}")
            except User.DoesNotExist:
                logger.error(f"Custom user not found for Django user: {user.id} (email: {email})")
                return Response({
                    "success": False,
                    "message": "User account not properly configured.",
                    "error_code": "USER_CONFIG_ERROR",
                    "details": {"email": email},
                    "timestamp": datetime.now().isoformat()
                }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
            
            # Log successful login with comprehensive details
            logger.info(f"Login successful for user: {email}, Role: {custom_user.role}, "
                       f"User ID: {custom_user.id_user}, Token: {token.key[:8]}..., "
                       f"IP: {client_ip}")
            
            response_data = {
                "success": True,
                "message": "Login successful",
                "data": {
                    "token": token.key,
                    "user": user_data,
                    "token_created": created,
                    "login_time": datetime.now().isoformat()
                },
                "timestamp": datetime.now().isoformat()
            }
            
            return Response(response_data, status=status.HTTP_200_OK)
            
        except Exception as e:
            logger.error(f"Unexpected error during login: {str(e)}", exc_info=True)
            error_response = {
                "success": False,
                "message": "An unexpected error occurred during login.",
                "error_code": "UNEXPECTED_ERROR",
                "details": {"error": str(e)},
                "timestamp": datetime.now().isoformat()
            }
            
            return Response(error_response, status=status.HTTP_500_INTERNAL_SERVER_ERROR)