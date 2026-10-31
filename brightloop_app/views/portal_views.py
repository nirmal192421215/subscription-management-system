from decimal import Decimal
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.utils import timezone
from brightloop_app.models import Subscription, Invoice, Payment, Plan
from brightloop_app.services.pdf_service import PDFService
from django.http import HttpResponse

def customer_required(view_func):
    def wrapper(request, *args, **kwargs):
        if not request.user.is_authenticated:
            return redirect('login')
        # If admin/staff visit portal, allow viewing or previewing
        return view_func(request, *args, **kwargs)
    return wrapper

@login_required
@customer_required
def portal_dashboard_view(request):
    user = request.user
    if user.is_customer_user:
        subscriptions = Subscription.objects.filter(customer=user).select_related('plan').order_by('-created_at')
        invoices = Invoice.objects.filter(customer=user).order_by('-invoice_date')
    else:
        # If staff views portal, show all or recent as preview
        subscriptions = Subscription.objects.all().select_related('plan', 'customer')[:10]
        invoices = Invoice.objects.all().select_related('customer')[:10]

    active_subs = [s for s in subscriptions if s.status == Subscription.Status.ACTIVE]
    unpaid_invoices = [i for i in invoices if i.status == Invoice.Status.CONFIRMED and i.balance_due > 0]
    total_due = sum(i.balance_due for i in unpaid_invoices)

    return render(request, 'brightloop/portal/dashboard.html', {
        'subscriptions': subscriptions[:5],
        'invoices': invoices[:5],
        'active_subs_count': len(active_subs),
        'unpaid_invoices_count': len(unpaid_invoices),
        'total_due': total_due,
    })

@login_required
@customer_required
def portal_subscriptions_view(request):
    user = request.user
    if user.is_customer_user:
        subscriptions = Subscription.objects.filter(customer=user).select_related('plan').order_by('-created_at')
    else:
        subscriptions = Subscription.objects.all().select_related('plan', 'customer').order_by('-created_at')
    return render(request, 'brightloop/portal/subscriptions.html', {'subscriptions': subscriptions})

@login_required
@customer_required
def portal_subscription_detail_view(request, subscription_id):
    user = request.user
    if user.is_customer_user:
        subscription = get_object_or_404(Subscription, id=subscription_id, customer=user)
    else:
        subscription = get_object_or_404(Subscription, id=subscription_id)

    invoices = subscription.invoices.all().order_by('-invoice_date')
    return render(request, 'brightloop/portal/subscription_detail.html', {
        'subscription': subscription,
        'invoices': invoices
    })

@login_required
@customer_required
def portal_subscription_action_view(request, subscription_id, action):
    """
    Customer self-service management governed by Plan policy rules:
    - pause (if plan.allow_pause)
    - resume
    - close_early (if plan.allow_close_early)
    - renew (if plan.allow_renewal)
    """
    user = request.user
    if user.is_customer_user:
        subscription = get_object_or_404(Subscription, id=subscription_id, customer=user)
    else:
        subscription = get_object_or_404(Subscription, id=subscription_id)

    plan = subscription.plan

    if action == 'pause':
        if not plan.allow_pause:
            messages.error(request, f"Pausing is not permitted for the '{plan.name}' plan.")
        elif subscription.status != Subscription.Status.ACTIVE:
            messages.error(request, "Only active subscriptions can be paused.")
        else:
            subscription.status = Subscription.Status.PAUSED
            subscription.save(update_fields=['status'])
            messages.success(request, f"Subscription {subscription.subscription_number} has been paused.")

    elif action == 'resume':
        if subscription.status != Subscription.Status.PAUSED:
            messages.error(request, "Only paused subscriptions can be resumed.")
        else:
            subscription.status = Subscription.Status.ACTIVE
            subscription.save(update_fields=['status'])
            messages.success(request, f"Subscription {subscription.subscription_number} has been resumed and is now active.")

    elif action == 'close_early':
        if not plan.allow_close_early:
            messages.error(request, f"Closing early is not permitted for the '{plan.name}' plan policy.")
        elif subscription.status in [Subscription.Status.CLOSED]:
            messages.warning(request, "Subscription is already closed.")
        else:
            subscription.status = Subscription.Status.CLOSED
            subscription.save(update_fields=['status'])
            messages.info(request, f"Subscription {subscription.subscription_number} has been closed.")

    elif action == 'renew':
        if not plan.allow_renewal:
            messages.error(request, f"Renewals are not permitted for the '{plan.name}' plan.")
        else:
            # Extend expiry date by 1 interval
            base_date = subscription.expiry_date or timezone.now().date()
            subscription.expiry_date = plan.calculate_next_date(base_date)
            if subscription.status in [Subscription.Status.CLOSED, Subscription.Status.CONFIRMED]:
                subscription.status = Subscription.Status.ACTIVE
            subscription.save(update_fields=['expiry_date', 'status'])
            messages.success(request, f"Subscription {subscription.subscription_number} successfully renewed until {subscription.expiry_date}!")

    return redirect('portal_subscription_detail', subscription_id=subscription.id)

@login_required
@customer_required
def portal_invoices_view(request):
    user = request.user
    if user.is_customer_user:
        invoices = Invoice.objects.filter(customer=user).order_by('-invoice_date')
    else:
        invoices = Invoice.objects.all().select_related('customer').order_by('-invoice_date')
    return render(request, 'brightloop/portal/invoices.html', {'invoices': invoices})

@login_required
@customer_required
def portal_invoice_detail_view(request, invoice_id):
    user = request.user
    if user.is_customer_user:
        invoice = get_object_or_404(Invoice, id=invoice_id, customer=user)
    else:
        invoice = get_object_or_404(Invoice, id=invoice_id)
    return render(request, 'brightloop/portal/invoice_detail.html', {'invoice': invoice})

@login_required
@customer_required
def portal_invoice_pdf_view(request, invoice_id):
    user = request.user
    if user.is_customer_user:
        invoice = get_object_or_404(Invoice, id=invoice_id, customer=user)
    else:
        invoice = get_object_or_404(Invoice, id=invoice_id)
    pdf_bytes = PDFService.generate_invoice_pdf(invoice)
    response = HttpResponse(pdf_bytes, content_type='application/pdf')
    response['Content-Disposition'] = f'attachment; filename="{invoice.invoice_number}.pdf"'
    return response

@login_required
@customer_required
def portal_pay_invoice_view(request, invoice_id):
    user = request.user
    if user.is_customer_user:
        invoice = get_object_or_404(Invoice, id=invoice_id, customer=user)
    else:
        invoice = get_object_or_404(Invoice, id=invoice_id)

    if invoice.balance_due <= 0:
        messages.info(request, "This invoice is already fully paid.")
        return redirect('portal_invoice_detail', invoice_id=invoice.id)

    if request.method == 'POST':
        method = request.POST.get('payment_method', Payment.PaymentMethod.CREDIT_CARD)
        note = request.POST.get('note', 'Payment via Customer Portal')
        ref = request.POST.get('reference', f"PORTAL-TXN-{timezone.now().strftime('%Y%m%d%H%M%S')}")
        
        try:
            amount_str = request.POST.get('amount', str(invoice.balance_due))
            amount = Decimal(amount_str)
            if amount <= 0:
                raise ValueError()
        except (ValueError, TypeError):
            messages.error(request, "Please enter a valid positive payment amount.")
            return render(request, 'brightloop/portal/pay_invoice.html', {'invoice': invoice})

        if amount > invoice.balance_due:
            amount = invoice.balance_due

        Payment.objects.create(
            invoice=invoice,
            payment_date=timezone.now().date(),
            amount=amount,
            payment_method=method,
            transaction_reference=ref,
            note=note,
            recorded_by=request.user
        )

        messages.success(request, f"Payment of ${amount:,.2f} processed successfully! Invoice updated.")
        return redirect('portal_invoice_detail', invoice_id=invoice.id)

    return render(request, 'brightloop/portal/pay_invoice.html', {'invoice': invoice})

