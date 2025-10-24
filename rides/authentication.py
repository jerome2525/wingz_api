from rest_framework.authentication import TokenAuthentication
from rest_framework.exceptions import AuthenticationFailed


class CustomTokenAuthentication(TokenAuthentication):
    """
    Custom token authentication that works with both formats:
    - "Token abc123..." (standard format)
    - "abc123..." (Swagger format)
    """
    keyword = 'Token'
    
    def authenticate(self, request):
        auth_header = request.META.get('HTTP_AUTHORIZATION', '')
        
        if not auth_header:
            return None
        
        # Handle both formats
        if auth_header.startswith('Token '):
            # Standard format: "Token abc123..."
            token = auth_header[6:]  # Remove 'Token ' prefix
        else:
            # Swagger format: "abc123..." (just the token)
            token = auth_header
        
        if not token:
            return None
            
        # Use the parent class to authenticate
        return self.authenticate_credentials(token)
