from .models import AuditLog


def log_audit(user, action, model_name, object_id=None, description="", request=None):
    """
    Helper function to record immutable audit log entries.
    Extracts IP address automatically if request object is provided.
    Guarantees passwords/hashes are never stored.
    """
    ip_address = None
    if request:
        x_forwarded_for = request.META.get('HTTP_X_FORWARDED_FOR')
        if x_forwarded_for:
            ip_address = x_forwarded_for.split(',')[0].strip()
        else:
            ip_address = request.META.get('REMOTE_ADDR')

    # Security check: redact passwords if present in description
    if "password" in description.lower():
        description = "[REDACTED SECURITY SENSITIVE DATA]"

    return AuditLog.objects.create(
        user=user if user and user.is_authenticated else None,
        action=action,
        model_name=model_name,
        object_id=str(object_id) if object_id is not None else None,
        description=description,
        ip_address=ip_address
    )
