import datetime
from decimal import Decimal
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.utils import timezone
from django.http import HttpResponse
from brightloop_app.models import Invoice, InvoiceLine, Payment, DiscountRule, Subscription, Product, User
from brightloop_app.services.billing_engine import BillingEngine
from brightloop_app.services.pdf_service import PDFService
from brightloop_app.views.catalog_views import internal_required
from brightloop_app.views.staff_views import admin_required

# ----------------- Invoices & Billing Day (Scene 4) -----------------

@login_required
@internal_required
def run_billing_day_view(request):
    """
    Scene 4: Billing day batch execution.
    Auto-bills due subscriptions, applies taxes and discounts, handles auto-close,
    and prevents duplicate billing (idempotency).
    """
    results = None
    target_date = timezone.now().date()

    if request.method == 'POST':
        date_str = request.POST.get('target_date')
        if date_str:
            target_date = datetime.date.fromisoformat(date_str)
        results = BillingEngine.run_billing_day(target_date=target_date)
        messages.success(request, f"Billing Day Run Complete for {target_date}: {results['generated_count']} invoices generated, {results['auto_closed_count']} subscriptions auto-closed.")

    due_subs = Subscription.objects.filter(
        status=Subscription.Status.ACTIVE,
        next_billing_date__lte=target_date
    ).select_related('customer', 'plan')

    return render(request, 'brightloop/billing/billing_day.html', {
        'target_date': target_date.isoformat(),
        'due_subs': due_subs,
        'results': results,
    })

@login_required
@internal_required
def invoice_list_view(request):
    status_filter = request.GET.get('status')
    overdue_filter = request.GET.get('overdue')
    customer_filter = request.GET.get('customer')
    search_q = request.GET.get('q', '').strip()

    invoices = Invoice.objects.all().select_related('customer', 'subscription').prefetch_related('payments')

    today = timezone.now().date()
    if overdue_filter == '1':
        invoices = invoices.filter(
            due_date__lt=today,
            balance_due__gt=0
        ).exclude(status__in=[Invoice.Status.PAID, Invoice.Status.CANCELLED])
    elif status_filter:
        invoices = invoices.filter(status=status_filter)

    if customer_filter:
        invoices = invoices.filter(customer_id=customer_filter)

    if search_q:
        from django.db.models import Q
        invoices = invoices.filter(
            Q(customer__company_name__icontains=search_q) |
            Q(customer__first_name__icontains=search_q) |
            Q(customer__last_name__icontains=search_q) |
            Q(invoice_number__icontains=search_q)
        )

    customers = User.objects.filter(role=User.Role.CUSTOMER).order_by('company_name')

    return render(request, 'brightloop/billing/invoice_list.html', {
        'invoices': invoices,
        'customers': customers,
        'current_status': status_filter,
        'overdue_filter': overdue_filter,
        'search_q': search_q,
        'today': today,
    })

@login_required
@internal_required
def invoice_detail_view(request, invoice_id):
    invoice = get_object_or_404(
        Invoice.objects.select_related('customer', 'subscription', 'discount_rule').prefetch_related('lines__product', 'lines__variant', 'lines__tax_rule', 'payments'),
        id=invoice_id
    )
    return render(request, 'brightloop/billing/invoice_detail.html', {'invoice': invoice})

@login_required
@internal_required
def invoice_confirm_view(request, invoice_id):
    invoice = get_object_or_404(Invoice, id=invoice_id)
    if invoice.status == Invoice.Status.DRAFT:
        invoice.status = Invoice.Status.CONFIRMED
        invoice.save(update_fields=['status'])
        messages.success(request, f"Invoice {invoice.invoice_number} has been confirmed.")
    return redirect('invoice_detail', invoice_id=invoice.id)

@login_required
@internal_required
def invoice_cancel_view(request, invoice_id):
    invoice = get_object_or_404(Invoice, id=invoice_id)
    invoice.status = Invoice.Status.CANCELLED
    invoice.save(update_fields=['status'])
    messages.warning(request, f"Invoice {invoice.invoice_number} was cancelled.")
    return redirect('invoice_detail', invoice_id=invoice.id)

@login_required
@internal_required
def invoice_send_view(request, invoice_id):
    """
    Scene 4: The team can confirm, cancel, send or print any invoice.
    """
    invoice = get_object_or_404(Invoice, id=invoice_id)
    invoice.sent_at = timezone.now()
    invoice.save(update_fields=['sent_at'])
    messages.success(request, f"Invoice {invoice.invoice_number} has been emailed to {invoice.customer.email}.")
    return redirect('invoice_detail', invoice_id=invoice.id)

@login_required
@internal_required
def invoice_print_view(request, invoice_id):
    invoice = get_object_or_404(Invoice, id=invoice_id)
    return render(request, 'brightloop/billing/invoice_print.html', {'invoice': invoice})

@login_required
@internal_required
def invoice_pdf_view(request, invoice_id):
    invoice = get_object_or_404(Invoice, id=invoice_id)
    pdf_bytes = PDFService.generate_invoice_pdf(invoice)
    response = HttpResponse(pdf_bytes, content_type='application/pdf')
    response['Content-Disposition'] = f'attachment; filename="{invoice.invoice_number}.pdf"'
    return response

# ----------------- Payments (Scene 6) -----------------

@login_required
@internal_required
def payment_record_view(request, invoice_id):
    """
    Scene 6: Payments arrive by different methods and on different days.
    Each one needs to be recorded with its method, amount, date and a note, against the right invoice.
    """
    invoice = get_object_or_404(Invoice, id=invoice_id)

    if request.method == 'POST':
        amount_str = request.POST.get('amount')
        method = request.POST.get('payment_method', Payment.PaymentMethod.BANK_TRANSFER)
        date_str = request.POST.get('payment_date') or timezone.now().date().isoformat()
        reference = request.POST.get('transaction_reference', '').strip()
        note = request.POST.get('note', '').strip()

        try:
            amount = Decimal(amount_str)
            if amount <= 0:
                raise ValueError()
        except (ValueError, TypeError):
            messages.error(request, "Please enter a valid positive payment amount.")
            return render(request, 'brightloop/billing/payment_form.html', {'invoice': invoice})

        p_date = datetime.date.fromisoformat(date_str)
        payment = Payment.objects.create(
            invoice=invoice,
            payment_date=p_date,
            amount=amount,
            payment_method=method,
            transaction_reference=reference,
            note=note,
            recorded_by=request.user
        )

        messages.success(request, f"Payment of ${amount:,.2f} recorded for {invoice.invoice_number} via {payment.get_payment_method_display()}! Status: {invoice.get_status_display()}.")
        return redirect('invoice_detail', invoice_id=invoice.id)

    return render(request, 'brightloop/billing/payment_form.html', {
        'invoice': invoice,
        'methods': Payment.PaymentMethod.choices,
        'today': timezone.now().date().isoformat()
    })

# ----------------- Discounts (Scene 5) -----------------

@login_required
@admin_required
def discount_list_view(request):
    """
    Scene 5: Only the admin can create discount rules.
    """
    discounts = DiscountRule.objects.all().order_by('-created_at')
    return render(request, 'brightloop/billing/discount_list.html', {'discounts': discounts})

@login_required
@admin_required
def discount_create_view(request):
    products = Product.objects.filter(is_active=True)

    if request.method == 'POST':
        name = request.POST.get('name', '').strip()
        code = request.POST.get('code', '').strip().upper()
        discount_type = request.POST.get('discount_type', DiscountRule.DiscountType.PERCENTAGE)
        val = Decimal(request.POST.get('discount_value', '0.00'))
        min_amount = Decimal(request.POST.get('min_purchase_amount', '0.00') or '0.00')
        min_qty = int(request.POST.get('min_quantity', '0') or '0')
        start_date = datetime.date.fromisoformat(request.POST.get('start_date') or timezone.now().date().isoformat())
        end_date = datetime.date.fromisoformat(request.POST.get('end_date'))
        max_uses_str = request.POST.get('max_uses')
        max_uses = int(max_uses_str) if max_uses_str else None
        scope = request.POST.get('scope', DiscountRule.Scope.SUBSCRIPTION)
        product_id = request.POST.get('product_id')
        target_product = Product.objects.filter(id=product_id).first() if product_id else None

        rule = DiscountRule.objects.create(
            name=name,
            code=code,
            discount_type=discount_type,
            discount_value=val,
            min_purchase_amount=min_amount,
            min_quantity=min_qty,
            start_date=start_date,
            end_date=end_date,
            max_uses=max_uses,
            scope=scope,
            product=target_product
        )
        messages.success(request, f"Discount rule '{rule.name}' [{rule.code}] created! Ready to be auto-applied on future billing runs.")
        return redirect('discount_list')

    return render(request, 'brightloop/billing/discount_form.html', {
        'products': products,
        'types': DiscountRule.DiscountType.choices,
        'scopes': DiscountRule.Scope.choices,
        'today': timezone.now().date().isoformat(),
        'default_end': (timezone.now().date() + datetime.timedelta(days=90)).isoformat(),
    })

@login_required
@admin_required
def discount_toggle_view(request, discount_id):
    discount = get_object_or_404(DiscountRule, id=discount_id)
    discount.is_active = not discount.is_active
    discount.save(update_fields=['is_active'])
    status = "activated" if discount.is_active else "deactivated"
    messages.info(request, f"Discount rule '{discount.name}' has been {status}.")
    return redirect('discount_list')
