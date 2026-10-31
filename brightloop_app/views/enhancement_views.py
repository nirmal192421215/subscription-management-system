"""
Enhancement views:
A. Interactive Charts (data API endpoint for Chart.js)
F. Customer Onboarding Wizard
H. Admin Audit Log
I. Dunning Campaign
J. CSV Export
K. Customer Statement PDF
L. Renewal Reminder Badges (data computed in subscription list)
"""

import csv
import datetime
from decimal import Decimal

from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.http import HttpResponse, JsonResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.utils import timezone
from django.db.models import Sum, Count, Q

from brightloop_app.models import (
    AuditLog, DunningLog, Invoice, Payment, Plan, Subscription,
    SubscriptionLine, User, Product, TaxRule
)
from brightloop_app.services.pdf_service import PDFService
from brightloop_app.views.catalog_views import internal_required
from brightloop_app.views.staff_views import admin_required


# ─── Helpers ──────────────────────────────────────────────────────────────────

def _get_client_ip(request):
    """Extract real client IP, honouring X-Forwarded-For."""
    xff = request.META.get('HTTP_X_FORWARDED_FOR')
    if xff:
        return xff.split(',')[0].strip()
    return request.META.get('REMOTE_ADDR')


def log_event(event_type, description, actor=None, target_model='', target_id=None, request=None):
    """Convenience helper to create an AuditLog entry."""
    ip = _get_client_ip(request) if request else None
    AuditLog.objects.create(
        event_type=event_type,
        actor=actor,
        target_model=target_model,
        target_id=target_id,
        description=description,
        ip_address=ip,
    )


# ─── Enhancement H: Admin Audit Log ──────────────────────────────────────────

@login_required
@admin_required
def audit_log_view(request):
    """Full paginated audit log for administrators."""
    event_type_filter = request.GET.get('event_type', '')
    actor_filter = request.GET.get('actor', '')
    search_q = request.GET.get('q', '').strip()

    logs = AuditLog.objects.select_related('actor').all()

    if event_type_filter:
        logs = logs.filter(event_type=event_type_filter)
    if actor_filter:
        logs = logs.filter(actor_id=actor_filter)
    if search_q:
        logs = logs.filter(
            Q(description__icontains=search_q) |
            Q(target_model__icontains=search_q) |
            Q(actor__email__icontains=search_q)
        )

    # Simple pagination: last 200 entries
    logs = logs[:200]

    event_types = AuditLog.EventType.choices
    actors = User.objects.filter(is_active=True).order_by('email')

    return render(request, 'brightloop/admin/audit_log.html', {
        'logs': logs,
        'event_types': event_types,
        'actors': actors,
        'current_event_type': event_type_filter,
        'current_actor': actor_filter,
        'search_q': search_q,
    })


# ─── Enhancement I: Dunning Campaign ─────────────────────────────────────────

@login_required
@internal_required
def dunning_dashboard_view(request):
    """View overdue invoices and trigger dunning emails (simulated)."""
    today = timezone.now().date()

    overdue_invoices = Invoice.objects.filter(
        due_date__lt=today,
        balance_due__gt=0
    ).exclude(
        status__in=[Invoice.Status.PAID, Invoice.Status.CANCELLED]
    ).select_related('customer', 'subscription').prefetch_related('dunning_logs').order_by('due_date')

    # Annotate with which dunning levels have been sent
    dunning_data = []
    for inv in overdue_invoices:
        sent_levels = set(inv.dunning_logs.values_list('level', flat=True))
        overdue_days = (today - inv.due_date).days
        # Which levels are now due?
        suggested = []
        if overdue_days >= 1 and DunningLog.Level.DAY1 not in sent_levels:
            suggested.append(DunningLog.Level.DAY1)
        if overdue_days >= 7 and DunningLog.Level.DAY7 not in sent_levels:
            suggested.append(DunningLog.Level.DAY7)
        if overdue_days >= 14 and DunningLog.Level.DAY14 not in sent_levels:
            suggested.append(DunningLog.Level.DAY14)
        dunning_data.append({
            'invoice': inv,
            'overdue_days': overdue_days,
            'sent_levels': sent_levels,
            'suggested': suggested,
        })

    return render(request, 'brightloop/admin/dunning_dashboard.html', {
        'dunning_data': dunning_data,
        'today': today,
    })


@login_required
@internal_required
def dunning_send_view(request, invoice_id, level):
    """Send (or simulate) a dunning email for the given invoice and level."""
    invoice = get_object_or_404(Invoice, id=invoice_id)
    valid_levels = [l.value for l in DunningLog.Level]

    if level not in valid_levels:
        messages.error(request, "Invalid dunning level.")
        return redirect('dunning_dashboard')

    # Check if already sent
    if invoice.dunning_logs.filter(level=level).exists():
        messages.warning(request, f"Dunning {level} already sent for {invoice.invoice_number}.")
        return redirect('dunning_dashboard')

    # Simulate sending (Django prints to console in development)
    level_labels = {
        'day1': 'Day 1 Payment Reminder',
        'day7': 'Day 7 Follow-up Notice',
        'day14': 'Day 14 Final Notice — Action Required',
    }
    subject = f"[Brightloop] {level_labels.get(level, 'Payment Reminder')} — {invoice.invoice_number}"
    body = (
        f"Dear {invoice.customer.display_name},\n\n"
        f"This is a {level_labels.get(level, 'payment reminder')} for invoice "
        f"{invoice.invoice_number} with a balance of ${invoice.balance_due:.2f} "
        f"that was due on {invoice.due_date}.\n\n"
        f"Please settle your account at your earliest convenience.\n\n"
        f"Regards,\nBrightloop Billing Team"
    )
    # In production: send_mail(subject, body, settings.DEFAULT_FROM_EMAIL, [invoice.customer.email])
    print(f"\n{'='*60}\nDUNNING EMAIL ({level.upper()})\nTo: {invoice.customer.email}\nSubject: {subject}\n\n{body}\n{'='*60}\n")

    DunningLog.objects.create(
        invoice=invoice,
        level=level,
        sent_to=invoice.customer.email,
        success=True,
        notes=f"Simulated send by {request.user.email}",
    )

    log_event(
        AuditLog.EventType.DUNNING,
        f"Dunning {level} sent for {invoice.invoice_number} to {invoice.customer.email}",
        actor=request.user,
        target_model='Invoice',
        target_id=invoice.id,
        request=request,
    )

    messages.success(request, f"✅ Dunning {level_labels.get(level)} sent to {invoice.customer.email}.")
    return redirect('dunning_dashboard')


# ─── Enhancement J: CSV Export ────────────────────────────────────────────────

@login_required
@internal_required
def export_invoices_csv(request):
    """Download all invoices as a CSV file."""
    response = HttpResponse(content_type='text/csv')
    response['Content-Disposition'] = 'attachment; filename="brightloop_invoices.csv"'

    writer = csv.writer(response)
    writer.writerow([
        'Invoice #', 'Customer', 'Company', 'Email',
        'Invoice Date', 'Due Date', 'Status',
        'Subtotal', 'Discount', 'Tax', 'Total', 'Amount Paid', 'Balance Due',
        'Subscription #', 'Plan',
    ])

    invoices = Invoice.objects.select_related('customer', 'subscription__plan').order_by('-invoice_date')
    for inv in invoices:
        writer.writerow([
            inv.invoice_number,
            f"{inv.customer.first_name} {inv.customer.last_name}".strip(),
            inv.customer.company_name,
            inv.customer.email,
            inv.invoice_date,
            inv.due_date,
            inv.get_status_display(),
            inv.subtotal,
            inv.discount_amount,
            inv.tax_amount,
            inv.total_amount,
            inv.amount_paid,
            inv.balance_due,
            inv.subscription.subscription_number if inv.subscription else '',
            inv.subscription.plan.name if inv.subscription else '',
        ])

    log_event(AuditLog.EventType.EXPORT, "Invoices CSV exported", actor=request.user, request=request)
    return response


@login_required
@internal_required
def export_subscriptions_csv(request):
    """Download all subscriptions as a CSV file."""
    response = HttpResponse(content_type='text/csv')
    response['Content-Disposition'] = 'attachment; filename="brightloop_subscriptions.csv"'

    writer = csv.writer(response)
    writer.writerow([
        'Subscription #', 'Customer', 'Company', 'Email',
        'Plan', 'Billing Interval', 'Status',
        'Start Date', 'Expiry Date', 'Next Billing Date',
        'Payment Terms', 'Recurring Total',
    ])

    subs = Subscription.objects.select_related('customer', 'plan').prefetch_related('lines').order_by('-created_at')
    for sub in subs:
        writer.writerow([
            sub.subscription_number,
            f"{sub.customer.first_name} {sub.customer.last_name}".strip(),
            sub.customer.company_name,
            sub.customer.email,
            sub.plan.name,
            sub.plan.get_billing_interval_display(),
            sub.get_status_display(),
            sub.start_date,
            sub.expiry_date or '',
            sub.next_billing_date or '',
            sub.get_payment_terms_display(),
            sub.calculate_grand_total(),
        ])

    log_event(AuditLog.EventType.EXPORT, "Subscriptions CSV exported", actor=request.user, request=request)
    return response


@login_required
@internal_required
def export_payments_csv(request):
    """Download all payments as a CSV file."""
    response = HttpResponse(content_type='text/csv')
    response['Content-Disposition'] = 'attachment; filename="brightloop_payments.csv"'

    writer = csv.writer(response)
    writer.writerow([
        'Invoice #', 'Customer', 'Company', 'Email',
        'Payment Date', 'Amount', 'Method', 'Reference', 'Recorded By',
    ])

    payments = Payment.objects.select_related('invoice__customer', 'recorded_by').order_by('-payment_date')
    for p in payments:
        writer.writerow([
            p.invoice.invoice_number,
            p.invoice.customer.display_name,
            p.invoice.customer.company_name,
            p.invoice.customer.email,
            p.payment_date,
            p.amount,
            p.get_payment_method_display(),
            p.transaction_reference,
            p.recorded_by.email if p.recorded_by else 'System',
        ])

    log_event(AuditLog.EventType.EXPORT, "Payments CSV exported", actor=request.user, request=request)
    return response


# ─── Enhancement K: Customer Statement PDF ───────────────────────────────────

@login_required
@internal_required
def customer_statement_pdf(request, customer_id):
    """Generate a full account statement PDF for a customer."""
    customer = get_object_or_404(User, id=customer_id, role=User.Role.CUSTOMER)
    invoices = Invoice.objects.filter(customer=customer).order_by('invoice_date').prefetch_related('payments')
    payments = Payment.objects.filter(invoice__customer=customer).order_by('payment_date')

    total_invoiced = invoices.aggregate(t=Sum('total_amount'))['t'] or Decimal('0.00')
    total_paid = payments.aggregate(t=Sum('amount'))['t'] or Decimal('0.00')
    total_outstanding = invoices.exclude(status=Invoice.Status.PAID).aggregate(b=Sum('balance_due'))['b'] or Decimal('0.00')

    pdf_bytes = PDFService.generate_customer_statement(
        customer=customer,
        invoices=list(invoices),
        payments=list(payments),
        total_invoiced=total_invoiced,
        total_paid=total_paid,
        total_outstanding=total_outstanding,
        generated_on=timezone.now().date(),
    )

    log_event(
        AuditLog.EventType.EXPORT,
        f"Customer statement PDF generated for {customer.display_name}",
        actor=request.user,
        target_model='User',
        target_id=customer.id,
        request=request,
    )

    response = HttpResponse(pdf_bytes, content_type='application/pdf')
    response['Content-Disposition'] = f'inline; filename="statement_{customer.email}.pdf"'
    return response


# ─── Enhancement F: Customer Onboarding Wizard ───────────────────────────────

@login_required
def onboarding_step1_view(request):
    """Step 1 of 3: Customer chooses a plan."""
    # Only for customers who have no active subscriptions yet
    if request.user.is_internal_staff:
        return redirect('finance_dashboard')

    plans = Plan.objects.filter(is_active=True).prefetch_related('templates')
    selected_plan_id = request.session.get('onboarding_plan_id')

    if request.method == 'POST':
        plan_id = request.POST.get('plan_id')
        if plan_id:
            request.session['onboarding_plan_id'] = plan_id
            return redirect('onboarding_step2')
        messages.error(request, "Please select a plan to continue.")

    return render(request, 'brightloop/onboarding/step1_choose_plan.html', {
        'plans': plans,
        'selected_plan_id': selected_plan_id,
    })


@login_required
def onboarding_step2_view(request):
    """Step 2 of 3: Configure subscription details (quantity, start date)."""
    if request.user.is_internal_staff:
        return redirect('finance_dashboard')

    plan_id = request.session.get('onboarding_plan_id')
    if not plan_id:
        return redirect('onboarding_step1')

    plan = get_object_or_404(Plan, id=plan_id, is_active=True)
    products = Product.objects.filter(is_active=True).prefetch_related('variants', 'default_tax_rule')

    if request.method == 'POST':
        request.session['onboarding_qty'] = request.POST.get('quantity', '1')
        request.session['onboarding_start'] = request.POST.get('start_date', str(timezone.now().date()))
        request.session['onboarding_notes'] = request.POST.get('notes', '')
        return redirect('onboarding_step3')

    return render(request, 'brightloop/onboarding/step2_configure.html', {
        'plan': plan,
        'products': products,
        'today': timezone.now().date().isoformat(),
    })


@login_required
def onboarding_step3_view(request):
    """Step 3 of 3: Confirm and create the subscription."""
    if request.user.is_internal_staff:
        return redirect('finance_dashboard')

    plan_id = request.session.get('onboarding_plan_id')
    if not plan_id:
        return redirect('onboarding_step1')

    plan = get_object_or_404(Plan, id=plan_id, is_active=True)
    qty = int(request.session.get('onboarding_qty', '1'))
    start_str = request.session.get('onboarding_start', str(timezone.now().date()))
    notes = request.session.get('onboarding_notes', '')

    try:
        start_date = datetime.date.fromisoformat(start_str)
    except ValueError:
        start_date = timezone.now().date()

    if request.method == 'POST' and request.POST.get('confirm') == '1':
        # Create the subscription
        year = timezone.now().year
        count = Subscription.objects.count() + 1
        sub_number = f"SUB-{year}-{count:05d}"

        sub = Subscription.objects.create(
            subscription_number=sub_number,
            customer=request.user,
            plan=plan,
            status=Subscription.Status.ACTIVE,
            start_date=start_date,
            next_billing_date=plan.calculate_next_date(start_date),
            payment_terms='net_30',
            notes=notes,
        )

        # Add a default line with plan cost
        if plan.cost and plan.cost > 0:
            # Find a default product for the plan or use a placeholder
            default_products = Product.objects.filter(is_active=True)
            if default_products.exists():
                product = default_products.first()
                SubscriptionLine.objects.create(
                    subscription=sub,
                    product=product,
                    quantity=qty,
                    unit_price=plan.cost,
                    tax_rule=product.default_tax_rule,
                )

        # Clear session
        for key in ['onboarding_plan_id', 'onboarding_qty', 'onboarding_start', 'onboarding_notes']:
            request.session.pop(key, None)

        log_event(
            AuditLog.EventType.SUBSCRIPTION_CREATED,
            f"Customer onboarding: {sub.subscription_number} created for {request.user.email}",
            actor=request.user,
            target_model='Subscription',
            target_id=sub.id,
            request=request,
        )

        messages.success(request, f"🎉 Welcome aboard! Your subscription {sub.subscription_number} is now active.")
        return redirect('portal_subscription_detail', subscription_id=sub.id)

    # Summary preview
    estimated_total = plan.cost * Decimal(str(qty))
    next_billing_date = plan.calculate_next_date(start_date)

    return render(request, 'brightloop/onboarding/step3_confirm.html', {
        'plan': plan,
        'qty': qty,
        'start_date': start_date,
        'next_billing_date': next_billing_date,
        'notes': notes,
        'estimated_total': estimated_total,
    })


# ─── Enhancement A: Chart Data API ───────────────────────────────────────────

@login_required
@internal_required
def chart_data_api(request):
    """
    JSON endpoint for Chart.js: returns last 6 months of revenue data,
    MRR per month, and overdue aging buckets.
    """
    today = timezone.now().date()
    months = []
    revenue_data = []
    invoice_data = []

    for i in range(5, -1, -1):
        # Go back i months from current month
        first_of_month = (today.replace(day=1) - datetime.timedelta(days=1)).replace(day=1) if i == 0 else today
        # Simpler: compute month start directly
        month_start = datetime.date(today.year, today.month, 1)
        # Shift back i months
        month_date = month_start
        for _ in range(i):
            month_date = (month_date - datetime.timedelta(days=1)).replace(day=1)

        month_end = (month_date.replace(day=28) + datetime.timedelta(days=4)).replace(day=1) - datetime.timedelta(days=1)
        label = month_date.strftime('%b %Y')
        months.append(label)

        # Revenue collected in this month
        rev = Payment.objects.filter(
            payment_date__gte=month_date,
            payment_date__lte=month_end
        ).aggregate(total=Sum('amount'))['total'] or Decimal('0.00')
        revenue_data.append(float(rev))

        # Invoices generated this month
        inv_total = Invoice.objects.filter(
            invoice_date__gte=month_date,
            invoice_date__lte=month_end
        ).aggregate(total=Sum('total_amount'))['total'] or Decimal('0.00')
        invoice_data.append(float(inv_total))

    # Overdue aging buckets
    overdue_base = Invoice.objects.filter(
        due_date__lt=today,
        balance_due__gt=0
    ).exclude(status__in=[Invoice.Status.PAID, Invoice.Status.CANCELLED])

    aging_1_30 = overdue_base.filter(due_date__gte=today - datetime.timedelta(days=30)).aggregate(t=Sum('balance_due'))['t'] or Decimal('0.00')
    aging_31_60 = overdue_base.filter(
        due_date__gte=today - datetime.timedelta(days=60),
        due_date__lt=today - datetime.timedelta(days=30)
    ).aggregate(t=Sum('balance_due'))['t'] or Decimal('0.00')
    aging_60_plus = overdue_base.filter(due_date__lt=today - datetime.timedelta(days=60)).aggregate(t=Sum('balance_due'))['t'] or Decimal('0.00')

    # Subscription status donut
    status_counts = {}
    for s in Subscription.objects.values('status').annotate(c=Count('id')):
        status_counts[s['status']] = s['c']

    return JsonResponse({
        'months': months,
        'revenue_collected': revenue_data,
        'invoices_generated': invoice_data,
        'aging': {
            'labels': ['1-30 days', '31-60 days', '60+ days'],
            'values': [float(aging_1_30), float(aging_31_60), float(aging_60_plus)],
        },
        'subscription_status': status_counts,
    })

