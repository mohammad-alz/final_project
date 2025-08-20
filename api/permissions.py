from rest_framework import permissions
from .models import UserVerification

class IsVerifiedUser(permissions.BasePermission):
    """
    Allows access only to users whose LATEST verification attempt is 'VERIFIED'.
    """
    message = 'Your account is not verified. Please upload your verification document.'

    def has_permission(self, request, view):
        # Must be authenticated first
        if not request.user.is_authenticated:
            return False
        
        # --- THIS IS THE FIX ---
        # Get the most recent verification submission for the user.
        latest_verification = request.user.verifications.last()
        
        # If the user has no submissions, they are not verified.
        if not latest_verification:
            return False
            
        # Check if the status of the latest submission is 'VERIFIED'.
        return latest_verification.status == UserVerification.Status.VERIFIED