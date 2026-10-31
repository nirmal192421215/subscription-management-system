from decimal import Decimal
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.utils.text import slugify
from brightloop_app.models import Product, ProductVariant, Plan, TaxRule

def internal_required(view_func):
    def wrapper(request, *args, **kwargs):
        if not request.user.is_authenticated:
            return redirect('login')
        if not request.user.is_internal_staff:
            messages.error(request, "Access restricted to internal staff.")
            return redirect('portal_dashboard')
        return view_func(request, *args, **kwargs)
    return wrapper

# ----------------- Products & Variants (Scene 2) -----------------

@login_required
@internal_required
def product_list_view(request):
    products = Product.objects.all().prefetch_related('variants', 'default_tax_rule').order_by('name')
    return render(request, 'brightloop/catalog/product_list.html', {'products': products})

@login_required
@internal_required
def product_create_view(request):
    taxes = TaxRule.objects.filter(is_active=True)
    if request.method == 'POST':
        name = request.POST.get('name', '').strip()
        product_type = request.POST.get('product_type', Product.ProductType.SOFTWARE)
        sales_price = Decimal(request.POST.get('sales_price', '0.00'))
        cost_price = Decimal(request.POST.get('cost_price', '0.00') or '0.00')
        tax_id = request.POST.get('default_tax_rule')
        notes = request.POST.get('notes', '').strip()

        tax_rule = TaxRule.objects.filter(id=tax_id).first() if tax_id else None

        product = Product.objects.create(
            name=name,
            product_type=product_type,
            sales_price=sales_price,
            cost_price=cost_price,
            default_tax_rule=tax_rule,
            notes=notes
        )

        # Handle optional initial variant (e.g. Brand: Odoo +560)
        v_attr = request.POST.get('variant_attr', '').strip()
        v_val = request.POST.get('variant_val', '').strip()
        v_extra = request.POST.get('variant_extra', '0.00')
        if v_attr and v_val:
            ProductVariant.objects.create(
                product=product,
                attribute_name=v_attr,
                variant_value=v_val,
                price_extra=Decimal(v_extra or '0.00')
            )

        messages.success(request, f"Product '{product.name}' created successfully!")
        return redirect('product_list')

    return render(request, 'brightloop/catalog/product_form.html', {'taxes': taxes})

@login_required
@internal_required
def product_edit_view(request, product_id):
    product = get_object_or_404(Product, id=product_id)
    taxes = TaxRule.objects.filter(is_active=True)

    if request.method == 'POST':
        product.name = request.POST.get('name', '').strip()
        product.product_type = request.POST.get('product_type', product.product_type)
        product.sales_price = Decimal(request.POST.get('sales_price', '0.00'))
        product.cost_price = Decimal(request.POST.get('cost_price', '0.00') or '0.00')
        tax_id = request.POST.get('default_tax_rule')
        product.default_tax_rule = TaxRule.objects.filter(id=tax_id).first() if tax_id else None
        product.notes = request.POST.get('notes', '').strip()
        product.is_active = 'is_active' in request.POST
        product.save()

        messages.success(request, f"Product '{product.name}' updated successfully.")
        return redirect('product_list')

    return render(request, 'brightloop/catalog/product_form.html', {'product': product, 'taxes': taxes})

@login_required
@internal_required
def variant_create_view(request, product_id):
    product = get_object_or_404(Product, id=product_id)
    if request.method == 'POST':
        attribute_name = request.POST.get('attribute_name', 'Brand').strip()
        variant_value = request.POST.get('variant_value', '').strip()
        price_extra = Decimal(request.POST.get('price_extra', '0.00') or '0.00')

        if variant_value:
            ProductVariant.objects.create(
                product=product,
                attribute_name=attribute_name,
                variant_value=variant_value,
                price_extra=price_extra
            )
            messages.success(request, f"Variant '{attribute_name}: {variant_value}' (+${price_extra}) added to {product.name}!")
    return redirect('product_edit', product_id=product.id)

@login_required
@internal_required
def variant_delete_view(request, variant_id):
    variant = get_object_or_404(ProductVariant, id=variant_id)
    product_id = variant.product.id
    variant.delete()
    messages.info(request, "Variant removed.")
    return redirect('product_edit', product_id=product_id)

# ----------------- Plans (Scene 2) -----------------

@login_required
@internal_required
def plan_list_view(request):
    plans = Plan.objects.all().order_by('billing_interval', 'cost')
    return render(request, 'brightloop/catalog/plan_list.html', {'plans': plans})

@login_required
@internal_required
def plan_create_view(request):
    if request.method == 'POST':
        name = request.POST.get('name', '').strip()
        code = request.POST.get('code', '').strip() or slugify(name)
        cost = Decimal(request.POST.get('cost', '0.00'))
        billing_interval = request.POST.get('billing_interval', Plan.BillingInterval.MONTHLY)
        min_quantity = int(request.POST.get('min_quantity', '1') or '1')
        available_from = request.POST.get('available_from') or None
        available_to = request.POST.get('available_to') or None
        description = request.POST.get('description', '').strip()

        # Lifecycle toggles
        auto_close = 'auto_close_on_end' in request.POST
        allow_early = 'allow_close_early' in request.POST
        allow_pause = 'allow_pause' in request.POST
        allow_renew = 'allow_renewal' in request.POST

        plan = Plan.objects.create(
            name=name,
            code=code,
            cost=cost,
            billing_interval=billing_interval,
            min_quantity=min_quantity,
            available_from=available_from or timezone.now().date(),
            available_to=available_to or None,
            description=description,
            auto_close_on_end=auto_close,
            allow_close_early=allow_early,
            allow_pause=allow_pause,
            allow_renewal=allow_renew,
        )
        messages.success(request, f"Plan '{plan.name}' created successfully!")
        return redirect('plan_list')

    return render(request, 'brightloop/catalog/plan_form.html', {'intervals': Plan.BillingInterval.choices})

@login_required
@internal_required
def plan_edit_view(request, plan_id):
    plan = get_object_or_404(Plan, id=plan_id)
    if request.method == 'POST':
        plan.name = request.POST.get('name', '').strip()
        plan.cost = Decimal(request.POST.get('cost', '0.00'))
        plan.billing_interval = request.POST.get('billing_interval', plan.billing_interval)
        plan.min_quantity = int(request.POST.get('min_quantity', '1') or '1')
        plan.available_from = request.POST.get('available_from') or plan.available_from
        plan.available_to = request.POST.get('available_to') or None
        plan.description = request.POST.get('description', '').strip()

        plan.auto_close_on_end = 'auto_close_on_end' in request.POST
        plan.allow_close_early = 'allow_close_early' in request.POST
        plan.allow_pause = 'allow_pause' in request.POST
        plan.allow_renewal = 'allow_renewal' in request.POST
        plan.is_active = 'is_active' in request.POST
        plan.save()

        messages.success(request, f"Plan '{plan.name}' updated successfully.")
        return redirect('plan_list')

    return render(request, 'brightloop/catalog/plan_form.html', {'plan': plan, 'intervals': Plan.BillingInterval.choices})

# ----------------- Taxes -----------------

@login_required
@internal_required
def tax_rule_list_view(request):
    taxes = TaxRule.objects.all().order_by('name')
    return render(request, 'brightloop/catalog/tax_list.html', {'taxes': taxes})

@login_required
@internal_required
def tax_rule_create_view(request):
    if request.method == 'POST':
        name = request.POST.get('name', '').strip()
        rate = Decimal(request.POST.get('rate', '0.00'))
        description = request.POST.get('description', '').strip()
        tax = TaxRule.objects.create(name=name, rate=rate, description=description)
        messages.success(request, f"Tax rule '{tax.name}' ({tax.rate}%) created!")
        return redirect('tax_rule_list')
    return render(request, 'brightloop/catalog/tax_form.html')

