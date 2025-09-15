# api/authentication.py
from rest_framework_simplejwt.authentication import JWTAuthentication

class CustomJWTAuthentication(JWTAuthentication):
    """
    A custom authentication class that reads the JWT from a custom header
    instead of the 'Authorization' header.
    """
    def get_header(self, request):
        header_name = 'X-Access-Token'
        token = request.headers.get(header_name)
        
        if token:
            return token.encode('utf-8')
        
        return None

    def get_raw_token(self, header):
        return header