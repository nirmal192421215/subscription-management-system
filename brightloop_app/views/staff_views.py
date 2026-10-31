from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.core.exceptions import ValidationError
from django.contrib.auth.password_validation import validate_password
from brightloop_app.models import User

def admin_required(view_func):
    def wrapper(request, *args, **kwargs):
        if not request.user.is_authenticated:
            return redirect('login')
        if not request.user.is_admin_user:
            messages.error(request, "Permission Denied: Only Brightloop Administrators can access staff management.")
            return redirect('dashboard')
        return view_func(request, *args, **kwargs)
    return wrapper

@login_required
@admin_required
def staff_list_view(request):
    staff_members = User.objects.filter(role__in=[User.Role.ADMIN, User.Role.STAFF]).order_by('role', 'first_name')
    return render(request, 'brightloop/staff/staff_list.html', {'staff_members': staff_members})

@login_required
@admin_required
def staff_create_view(request):
    errors = []
    if request.method == 'POST':
        email = request.POST.get('email', '').strip().lower()
        first_name = request.POST.get('first_name', '').strip()
        last_name = request.POST.get('last_name', '').strip()
        phone = request.POST.get('phone', '').strip()
        role = request.POST.get('role', User.Role.STAFF)
        password = request.POST.get('password', '')
        confirm_password = request.POST.get('confirm_password', '')

        if not email:
            errors.append("Staff email is required.")
        elif User.objects.filter(email=email).exists():
            errors.append("An account with this email address already exists.")

        if password != confirm_password:
            errors.append("Passwords do not match.")

        try:
            validate_password(password)
        except ValidationError as e:
            errors.extend(e.messages)

        if not errors:
            user = User.objects.create_user(
                email=email,
                password=password,
                first_name=first_name,
                last_name=last_name,
                phone=phone,
                role=role
            )
            messages.success(request, f"New team member {user.display_name} ({user.get_role_display()}) added successfully!")
            return redirect('staff_list')

    return render(request, 'brightloop/staff/staff_form.html', {'errors': errors})
