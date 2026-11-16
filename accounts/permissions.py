from rest_framework.permissions import BasePermission


class IsPharmacyStaff(BasePermission):
    """Owner or pharmacist who belongs to a pharmacy."""
    message = "You must belong to a pharmacy to do this."

    def has_permission(self, request, view):
        user = request.user
        return bool(user and user.is_authenticated and user.pharmacy_id)


class IsPharmacyOwner(BasePermission):
    """Only the owner of a pharmacy."""
    message = "Only the pharmacy owner can do this."

    def has_permission(self, request, view):
        user = request.user
        return bool(
            user and user.is_authenticated
            and user.pharmacy_id
            and user.role == 'owner'
        )