import uuid
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth import login, logout, authenticate
from django.contrib import messages
from django.core.exceptions import ValidationError
from django.contrib.auth.password_validation import validate_password
from brightloop_app.models import User, PasswordResetToken

def login_view(request):
    if request.user.is_authenticated:
        if request.user.is_customer_user:
            return redirect('portal_dashboard')
        return redirect('finance_dashboard')

    if request.method == 'POST':
        email = request.POST.get('email', '').strip().lower()
        password = request.POST.get('password', '')
        user = authenticate(request, username=email, password=password)
        if user is not None:
            login(request, user)
            messages.success(request, f"Welcome back, {user.display_name}!")
            next_url = request.GET.get('next')
            if next_url:
                return redirect(next_url)
            if user.is_customer_user:
                return redirect('portal_dashboard')
            return redirect('finance_dashboard')
        else:
            messages.error(request, "Invalid email or password.")

    demo_accounts = [
        {'role': 'Administrator', 'email': 'admin@brightloop.com', 'pass': 'Brightloop#Admin2026!', 'desc': 'Full system control, staff management, discount rules'},
        {'role': 'Finance / Staff', 'email': 'staff@brightloop.com', 'pass': 'Brightloop#Staff2026!', 'desc': 'Daily ops, quotes, invoicing, payments'},
        {'role': 'Customer', 'email': 'acme@example.com', 'pass': 'Brightloop#Cust2026!', 'desc': 'Acme Corp portal (Active enterprise subscription)'},
        {'role': 'Customer (Alt)', 'email': 'customer@brightloop.com', 'pass': 'Brightloop#Cust2026!', 'desc': 'Customer portal (Monthly starter plan)'},
    ]

    return render(request, 'brightloop/auth/login.html', {'demo_accounts': demo_accounts})


def logout_view(request):
    logout(request)
    messages.info(request, "You have been logged out.")
    return redirect('login')


def register_view(request):
    """
    Scene 1: A small business finds Brightloop online and creates an account
    with their email and a password.
    Each email can belong to only one account.
    Password must be > 8 characters, with uppercase, lowercase, and special character.
    """
    if request.user.is_authenticated:
        return redirect('portal_dashboard' if request.user.is_customer_user else 'finance_dashboard')

    errors = []
    if request.method == 'POST':
        email = request.POST.get('email', '').strip().lower()
        password = request.POST.get('password', '')
        confirm_password = request.POST.get('confirm_password', '')
        company_name = request.POST.get('company_name', '').strip()
        first_name = request.POST.get('first_name', '').strip()
        last_name = request.POST.get('last_name', '').strip()
        phone = request.POST.get('phone', '').strip()
        address = request.POST.get('address', '').strip()

        if not email:
            errors.append("Email address is required.")
        elif User.objects.filter(email=email).exists():
            errors.append("An account with this email address already exists.")

        if password != confirm_password:
            errors.append("Passwords do not match.")

        # Validate password complexity via custom Brightloop validator
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
                company_name=company_name,
                phone=phone,
                address=address,
                role=User.Role.CUSTOMER
            )
            login(request, user)
            messages.success(request, "Your Brightloop account has been created successfully! Welcome to your customer portal.")
            return redirect('portal_dashboard')

    return render(request, 'brightloop/auth/register.html', {'errors': errors})


def forgot_password_view(request):
    """
    Scene 1: If they forget it later, a reset link should arrive at their registered email.
    Uses canonical BASE_URL if configured, or dynamically falls back to request origin.
    """
    reset_link_generated = None
    if request.method == 'POST':
        email = request.POST.get('email', '').strip().lower()
        try:
            user = User.objects.get(email=email)
            token = PasswordResetToken.objects.create(user=user)
            from django.conf import settings
            base_url = getattr(settings, 'BASE_URL', '') or request.build_absolute_uri('/').rstrip('/')
            reset_url = f"{base_url}/reset-password/{token.token}/"
            reset_link_generated = reset_url
            messages.success(request, f"A password reset link has been dispatched to {email}.")
        except User.DoesNotExist:
            # For security, we can still show a generic notice or helpful hint in demo mode
            messages.info(request, f"If an account exists for {email}, a reset link has been dispatched.")

    return render(request, 'brightloop/auth/forgot_password.html', {'reset_link': reset_link_generated})


def reset_password_view(request, token):
    reset_token = get_object_or_404(PasswordResetToken, token=token)
    if not reset_token.is_valid():
        messages.error(request, "This password reset link is invalid or has expired.")
        return redirect('forgot_password')

    errors = []
    if request.method == 'POST':
        password = request.POST.get('password', '')
        confirm_password = request.POST.get('confirm_password', '')

        if password != confirm_password:
            errors.append("Passwords do not match.")

        try:
            validate_password(password)
        except ValidationError as e:
            errors.extend(e.messages)

        if not errors:
            user = reset_token.user
            user.set_password(password)
            user.save()
            reset_token.is_used = True
            reset_token.save()
            messages.success(request, "Password updated successfully. You can now log in.")
            return redirect('login')

    return render(request, 'brightloop/auth/reset_password.html', {'token': token, 'errors': errors})


def demo_switch_user_view(request, user_id):
    """
    Fast role switcher for demo and hackathon presentation.
    Allows instant switching between Admin, Staff, and Customer users.
    """
    target_user = get_object_or_404(User, id=user_id)
    login(request, target_user)
    messages.info(request, f"Switched view to {target_user.display_name} ({target_user.get_role_display()})")
    if target_user.is_customer_user:
        return redirect('portal_dashboard')
    return redirect('finance_dashboard')

