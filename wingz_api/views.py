from rest_framework.decorators import api_view
from rest_framework.response import Response
from rest_framework import status
from drf_spectacular.utils import extend_schema

@extend_schema(
    summary="API Overview",
    description="Welcome endpoint providing API information and available endpoints",
    tags=["General"]
)
@api_view(['GET'])
def api_overview(request):
    """
    API Overview - Welcome endpoint
    
    Returns information about the Wingz API including available endpoints and versions.
    """
    api_urls = {
        'Welcome': 'Welcome to Wingz API!',
        'API Documentation': {
            'Swagger UI': '/api/docs/',
            'ReDoc': '/api/redoc/',
            'Schema': '/api/schema/'
        },
        'Endpoints': {
            'Users': '/api/v1/users/',
            'Rides': '/api/v1/rides/',
            'Ride Events': '/api/v1/ride-events/',
            'Admin': '/admin/'
        },
        'Status': 'API is running successfully',
        'Versions': {
            'Django': '5.2.7',
            'DRF': '3.15.2'
        }
    }
    return Response(api_urls)

@extend_schema(
    summary="Health Check",
    description="Check if the API is running and healthy",
    tags=["General"]
)
@api_view(['GET'])
def health_check(request):
    """
    Health check endpoint
    
    Returns the current status of the API service.
    """
    return Response({
        'status': 'healthy',
        'message': 'Wingz API is running',
        'timestamp': request.META.get('HTTP_DATE', 'N/A')
    })
