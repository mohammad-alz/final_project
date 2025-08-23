# api/authentication.py
from rest_framework_simplejwt.authentication import JWTAuthentication

class CustomJWTAuthentication(JWTAuthentication):
    """
    A custom authentication class that reads the JWT from a custom header
    instead of the 'Authorization' header.
    """
    def get_header(self, request):
        """
        Overrides the default method to look for our custom header.
        """
        # The header name you want to use, e.g., 'X-Access-Token'
        header_name = 'X-Access-Token'
        token = request.headers.get(header_name)
        
        if token:
            # SimpleJWT expects the header to be returned as bytes
            return token.encode('utf-8')
        
        return None

    def get_raw_token(self, header):
        """
        Overrides the default method to simply return the token, as we are no
        longer using a prefix like 'Bearer' or 'Gold'.
        """
        return header