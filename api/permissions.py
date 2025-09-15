from rest_framework import permissions
from .models import UserVerification

class IsVerifiedUser(permissions.BasePermission):
    """
    Allows access only to users whose LATEST verification attempt is 'VERIFIED'.
    """
    message = 'Your account is not verified. Please upload your verification document.'

    def has_permission(self, request, view):
        if not request.user.is_authenticated:
            return False
        
        latest_verification = request.user.verifications.last()
        
        if not latest_verification:
            return False
            
        return latest_verification.status == UserVerification.Status.VERIFIED