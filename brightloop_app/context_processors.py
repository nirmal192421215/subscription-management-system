from brightloop_app.models import User, Invoice

def brightloop_context(request):
    overdue_count = 0
    if request.user.is_authenticated and request.user.is_internal_staff:
        # Fast query for overdue badge
        from django.utils import timezone
        today = timezone.now().date()
        overdue_count = Invoice.objects.filter(
            due_date__lt=today,
            balance_due__gt=0
        ).exclude(status__in=[Invoice.Status.PAID, Invoice.Status.CANCELLED]).count()

    demo_users = []
    if request.user.is_authenticated:
        # Provide sample demo accounts for quick role switching in the navbar
        demo_users = User.objects.all().order_by('role', 'id')[:10]

    return {
        'brightloop_role': getattr(request.user, 'role', 'guest'),
        'is_admin': getattr(request.user, 'is_admin_user', False),
        'is_staff': getattr(request.user, 'is_internal_staff', False),
        'is_customer': getattr(request.user, 'is_customer_user', False),
        'overdue_count': overdue_count,
        'demo_users': demo_users,
    }
