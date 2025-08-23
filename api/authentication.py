# api/authentication.py
from rest_framework_simplejwt.authentication import JWTAuthentication

# ... (your DevelopmentAuthentication class might be here)

class CustomJWTAuthentication(JWTAuthentication):
    # Change this to whatever keyword you want to use
    auth_header_prefix = 'Gold'