import datetime
from decimal import Decimal
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.utils import timezone
from django.http import HttpResponse
from brightloop_app.models import (
    Subscription, SubscriptionLine, QuotationTemplate, QuotationTemplateLine,
    Plan, Product, ProductVariant, TaxRule, User, Invoice
)
from brightloop_app.services.pdf_service import PDFService
from brightloop_app.views.catalog_views import internal_required

def generate_sub_number():
    year = timezone.now().year
    count = Subscription.objects.count() + 1
    return f"SUB-{year}-{count:05d}"

# ----------------- Quotation Templates -----------------

@login_required
@internal_required
def template_list_view(request):
    templates = QuotationTemplate.objects.all().prefetch_related('lines', 'plan')
    return render(request, 'brightloop/subscriptions/template_list.html', {'templates': templates})

@login_required
@internal_required
def template_create_view(request):
    plans = Plan.objects.filter(is_active=True)
    products = Product.objects.filter(is_active=True).prefetch_related('variants')
    taxes = TaxRule.objects.filter(is_active=True)

    if request.method == 'POST':
        name = request.POST.get('name', '').strip()
        plan_id = request.POST.get('plan_id')
        valid_days = int(request.POST.get('valid_days', '15') or '15')
        notes = request.POST.get('notes', '').strip()

        plan = get_object_or_404(Plan, id=plan_id)
        template = QuotationTemplate.objects.create(
            name=name,
            plan=plan,
            valid_days=valid_days,
            notes=notes
        )

        # Process initial lines
        product_ids = request.POST.getlist('line_product_id')
        quantities = request.POST.getlist('line_quantity')
        prices = request.POST.getlist('line_price')
        tax_ids = request.POST.getlist('line_tax_id')

        for i in range(len(product_ids)):
            p_id = product_ids[i]
            if p_id:
                p = Product.objects.filter(id=p_id).first()
                if p:
                    qty = int(quantities[i]) if i < len(quantities) and quantities[i] else 1
                    pr = Decimal(prices[i]) if i < len(prices) and prices[i] else p.sales_price
                    t_id = tax_ids[i] if i < len(tax_ids) else None
                    t_rule = TaxRule.objects.filter(id=t_id).first() if t_id else None
                    QuotationTemplateLine.objects.create(
                        template=template,
                        product=p,
                        quantity=qty,
                        unit_price=pr,
                        tax_rule=t_rule
                    )

        messages.success(request, f"Quotation template '{template.name}' created!")
        return redirect('template_list')

    return render(request, 'brightloop/subscriptions/template_form.html', {
        'plans': plans,
        'products': products,
        'taxes': taxes,
    })

@login_required
@internal_required
def template_create_quote_view(request, template_id):
    """
    Scene 3: A sales rep starts from a quotation template that already has the
    right plan and product lines, and stays valid for a set number of days.
    """
    template = get_object_or_404(QuotationTemplate, id=template_id)
    customers = User.objects.filter(role=User.Role.CUSTOMER).order_by('company_name', 'first_name')

    if request.method == 'POST':
        customer_id = request.POST.get('customer_id')
        customer = get_object_or_404(User, id=customer_id)
        start_date_str = request.POST.get('start_date') or timezone.now().date().isoformat()
        start_date = datetime.date.fromisoformat(start_date_str)
        payment_terms = request.POST.get('payment_terms', 'net_30')

        valid_until = start_date + datetime.timedelta(days=template.valid_days)
        expiry_date = template.plan.calculate_next_date(start_date)

        sub_num = generate_sub_number()
        subscription = Subscription.objects.create(
            subscription_number=sub_num,
            customer=customer,
            plan=template.plan,
            start_date=start_date,
            expiry_date=expiry_date,
            quotation_valid_until=valid_until,
            payment_terms=payment_terms,
            status=Subscription.Status.QUOTATION, # Created directly as Quotation offer
            next_billing_date=start_date,
            notes=f"Generated from Quotation Template: {template.name}. {template.notes}"
        )

        for line in template.lines.all():
            SubscriptionLine.objects.create(
                subscription=subscription,
                product=line.product,
                variant=line.variant,
                quantity=line.quantity,
                unit_price=line.unit_price,
                tax_rule=line.tax_rule
            )

        messages.success(request, f"Quotation {subscription.subscription_number} prepared for {customer.display_name} using template '{template.name}' (Valid until {valid_until})!")
        return redirect('subscription_detail', subscription_id=subscription.id)

    return render(request, 'brightloop/subscriptions/quote_from_template.html', {
        'template': template,
        'customers': customers,
        'today': timezone.now().date().isoformat()
    })

# ----------------- Subscriptions Lifecycle -----------------

@login_required
@internal_required
def subscription_list_view(request):
    status_filter = request.GET.get('status')
    plan_filter = request.GET.get('plan')
    search_q = request.GET.get('q', '').strip()

    subs = Subscription.objects.all().select_related('customer', 'plan').prefetch_related('lines')

    if status_filter:
        subs = subs.filter(status=status_filter)
    if plan_filter:
        subs = subs.filter(plan_id=plan_filter)
    if search_q:
        from django.db.models import Q
        subs = subs.filter(
            Q(customer__company_name__icontains=search_q) |
            Q(customer__first_name__icontains=search_q) |
            Q(customer__last_name__icontains=search_q) |
            Q(subscription_number__icontains=search_q)
        )

    plans = Plan.objects.all()
    statuses = Subscription.Status.choices

    return render(request, 'brightloop/subscriptions/subscription_list.html', {
        'subscriptions': subs,
        'plans': plans,
        'statuses': statuses,
        'current_status': status_filter,
        'current_plan': plan_filter,
        'search_q': search_q,
    })

@login_required
@internal_required
def subscription_create_view(request):
    customers = User.objects.filter(role=User.Role.CUSTOMER).order_by('company_name', 'first_name')
    plans = Plan.objects.filter(is_active=True)
    products = Product.objects.filter(is_active=True).prefetch_related('variants')
    taxes = TaxRule.objects.filter(is_active=True)

    if request.method == 'POST':
        customer_id = request.POST.get('customer_id')
        plan_id = request.POST.get('plan_id')
        start_date_str = request.POST.get('start_date') or timezone.now().date().isoformat()
        start_date = datetime.date.fromisoformat(start_date_str)
        expiry_date_str = request.POST.get('expiry_date')
        expiry_date = datetime.date.fromisoformat(expiry_date_str) if expiry_date_str else None
        payment_terms = request.POST.get('payment_terms', 'net_30')
        notes = request.POST.get('notes', '').strip()
        status = request.POST.get('initial_status', Subscription.Status.DRAFT)

        customer = get_object_or_404(User, id=customer_id)
        plan = get_object_or_404(Plan, id=plan_id)

        if not expiry_date:
            expiry_date = plan.calculate_next_date(start_date)

        sub_num = generate_sub_number()
        subscription = Subscription.objects.create(
            subscription_number=sub_num,
            customer=customer,
            plan=plan,
            start_date=start_date,
            expiry_date=expiry_date,
            payment_terms=payment_terms,
            status=status,
            next_billing_date=start_date,
            notes=notes
        )

        # Lines
        product_ids = request.POST.getlist('line_product_id')
        variant_ids = request.POST.getlist('line_variant_id')
        quantities = request.POST.getlist('line_quantity')
        prices = request.POST.getlist('line_price')
        tax_ids = request.POST.getlist('line_tax_id')

        for i in range(len(product_ids)):
            p_id = product_ids[i]
            if p_id:
                p = Product.objects.filter(id=p_id).first()
                if p:
                    v_id = variant_ids[i] if i < len(variant_ids) and variant_ids[i] else None
                    var = ProductVariant.objects.filter(id=v_id).first() if v_id else None
                    qty = int(quantities[i]) if i < len(quantities) and quantities[i] else 1
                    pr = Decimal(prices[i]) if i < len(prices) and prices[i] else (var.total_price if var else p.sales_price)
                    t_id = tax_ids[i] if i < len(tax_ids) else None
                    t_rule = TaxRule.objects.filter(id=t_id).first() if t_id else None

                    SubscriptionLine.objects.create(
                        subscription=subscription,
                        product=p,
                        variant=var,
                        quantity=qty,
                        unit_price=pr,
                        tax_rule=t_rule
                    )

        messages.success(request, f"Subscription {subscription.subscription_number} created!")
        return redirect('subscription_detail', subscription_id=subscription.id)

    return render(request, 'brightloop/subscriptions/subscription_form.html', {
        'customers': customers,
        'plans': plans,
        'products': products,
        'taxes': taxes,
        'today': timezone.now().date().isoformat()
    })

@login_required
@internal_required
def subscription_detail_view(request, subscription_id):
    subscription = get_object_or_404(
        Subscription.objects.select_related('customer', 'plan').prefetch_related('lines__product', 'lines__variant', 'lines__tax_rule', 'invoices'),
        id=subscription_id
    )
    products = Product.objects.filter(is_active=True).prefetch_related('variants')
    taxes = TaxRule.objects.filter(is_active=True)
    invoices = subscription.invoices.all().order_by('-invoice_date')

    subtotal = subscription.calculate_subtotal()
    tax_total = subscription.calculate_taxes()
    grand_total = subscription.calculate_grand_total()

    return render(request, 'brightloop/subscriptions/subscription_detail.html', {
        'subscription': subscription,
        'products': products,
        'taxes': taxes,
        'invoices': invoices,
        'subtotal': subtotal,
        'tax_total': tax_total,
        'grand_total': grand_total,
    })

@login_required
@internal_required
def subscription_add_line_view(request, subscription_id):
    subscription = get_object_or_404(Subscription, id=subscription_id)
    if request.method == 'POST':
        product_id = request.POST.get('product_id')
        variant_id = request.POST.get('variant_id')
        quantity = int(request.POST.get('quantity', '1') or '1')
        price_str = request.POST.get('unit_price')
        tax_id = request.POST.get('tax_rule_id')

        product = get_object_or_404(Product, id=product_id)
        variant = ProductVariant.objects.filter(id=variant_id).first() if variant_id else None
        tax_rule = TaxRule.objects.filter(id=tax_id).first() if tax_id else None

        if price_str:
            unit_price = Decimal(price_str)
        else:
            unit_price = variant.total_price if variant else product.sales_price

        SubscriptionLine.objects.create(
            subscription=subscription,
            product=product,
            variant=variant,
            quantity=quantity,
            unit_price=unit_price,
            tax_rule=tax_rule
        )
        messages.success(request, f"Added line item {product.name} to {subscription.subscription_number}.")

    return redirect('subscription_detail', subscription_id=subscription.id)

@login_required
@internal_required
def subscription_delete_line_view(request, line_id):
    line = get_object_or_404(SubscriptionLine, id=line_id)
    sub_id = line.subscription.id
    line.delete()
    messages.info(request, "Line item removed.")
    return redirect('subscription_detail', subscription_id=sub_id)

@login_required
@internal_required
def subscription_status_change_view(request, subscription_id, new_status):
    """
    Moves from Draft to Quotation to Confirmed to Active and finally to Closed (Scene 3).
    Also supports Paused and Renew.
    """
    subscription = get_object_or_404(Subscription, id=subscription_id)
    old_status = subscription.status
    plan = subscription.plan

    if new_status == 'quotation':
        subscription.status = Subscription.Status.QUOTATION
        if not subscription.quotation_valid_until:
            subscription.quotation_valid_until = timezone.now().date() + datetime.timedelta(days=15)
        messages.success(request, f"Quotation offer prepared for customer. Valid until {subscription.quotation_valid_until}.")

    elif new_status == 'confirmed':
        subscription.status = Subscription.Status.CONFIRMED
        messages.success(request, f"Subscription {subscription.subscription_number} confirmed by customer.")

    elif new_status == 'active':
        subscription.status = Subscription.Status.ACTIVE
        if not subscription.next_billing_date:
            subscription.next_billing_date = subscription.start_date
        messages.success(request, f"Subscription {subscription.subscription_number} is now ACTIVE! Recurring billing initialized.")

    elif new_status == 'paused':
        if not plan.allow_pause:
            messages.error(request, f"Plan policy for '{plan.name}' does not allow pausing.")
            return redirect('subscription_detail', subscription_id=subscription.id)
        subscription.status = Subscription.Status.PAUSED
        messages.info(request, f"Subscription {subscription.subscription_number} paused.")

    elif new_status == 'closed':
        if old_status in [Subscription.Status.ACTIVE, Subscription.Status.PAUSED] and not plan.allow_close_early and subscription.expiry_date and subscription.expiry_date > timezone.now().date():
            messages.warning(request, f"Note: Plan '{plan.name}' restricts early closure, but admin override was applied.")
        subscription.status = Subscription.Status.CLOSED
        messages.info(request, f"Subscription {subscription.subscription_number} closed.")

    elif new_status == 'renew':
        if not plan.allow_renewal:
            messages.error(request, f"Plan policy for '{plan.name}' does not permit renewals.")
            return redirect('subscription_detail', subscription_id=subscription.id)
        base = subscription.expiry_date or timezone.now().date()
        subscription.expiry_date = plan.calculate_next_date(base)
        subscription.status = Subscription.Status.ACTIVE
        messages.success(request, f"Subscription renewed until {subscription.expiry_date} and reactivated!")

    subscription.save()
    return redirect('subscription_detail', subscription_id=subscription.id)

@login_required
@internal_required
def subscription_pdf_view(request, subscription_id):
    subscription = get_object_or_404(Subscription, id=subscription_id)
    pdf_bytes = PDFService.generate_quote_pdf(subscription)
    response = HttpResponse(pdf_bytes, content_type='application/pdf')
    response['Content-Disposition'] = f'attachment; filename="Quote_{subscription.subscription_number}.pdf"'
    return response
