from rest_framework import permissions

class IsAdmin(permissions.BasePermission):
    def has_permission(self, request, view):
        return request.user.is_authenticated and request.user.role == 'Admin'

class IsPolice(permissions.BasePermission):
    def has_permission(self, request, view):
        return request.user.is_authenticated and request.user.role == 'Police'

class IsInvestigator(permissions.BasePermission):
    def has_permission(self, request, view):
        return request.user.is_authenticated and request.user.role == 'Investigator'

class IsAdminOrInvestigator(permissions.BasePermission):
    def has_permission(self, request, view):
        is_admin = IsAdmin().has_permission(request, view)
        is_investigator = IsInvestigator().has_permission(request, view)
        return is_admin or is_investigator

class IsAdminOrInvestigatorOrPolice(permissions.BasePermission):
    def has_permission(self, request, view):
        is_admin = IsAdmin().has_permission(request, view)
        is_investigator = IsInvestigator().has_permission(request, view)
        is_police = IsPolice().has_permission(request, view)
        return is_admin or is_investigator or is_police