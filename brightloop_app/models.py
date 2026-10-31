
import uuid
from decimal import Decimal
from django.db import models
from django.contrib.auth.models import AbstractUser, BaseUserManager
from django.utils import timezone
from dateutil.relativedelta import relativedelta


# -------------------------------------------------------------------------
# Custom User & Authentication
# -------------------------------------------------------------------------

class CustomUserManager(BaseUserManager):
    def create_user(self, email, password=None, **extra_fields):
        if not email:
            raise ValueError('Email address is required')
        email = self.normalize_email(email)
        extra_fields.setdefault('is_staff', False)
        extra_fields.setdefault('is_superuser', False)
        user = self.model(email=email, username=email, **extra_fields)
        if password:
            user.set_password(password)
        else:
            user.set_unusable_password()
        user.save(using=self._db)
        return user

    def create_superuser(self, email, password=None, **extra_fields):
        extra_fields.setdefault('is_staff', True)
        extra_fields.setdefault('is_superuser', True)
        extra_fields.setdefault('role', User.Role.ADMIN)

        if extra_fields.get('is_staff') is not True:
            raise ValueError('Superuser must have is_staff=True.')
        if extra_fields.get('is_superuser') is not True:
            raise ValueError('Superuser must have is_superuser=True.')

        return self.create_user(email, password, **extra_fields)


class User(AbstractUser):
    class Role(models.TextChoices):
        ADMIN = 'admin', 'Administrator'
        STAFF = 'staff', 'Internal Staff'
        CUSTOMER = 'customer', 'Customer'

    username = models.CharField(max_length=150, unique=True, blank=True)
    email = models.EmailField(unique=True)
    role = models.CharField(max_length=20, choices=Role.choices, default=Role.CUSTOMER)
    company_name = models.CharField(max_length=255, blank=True)
    phone = models.CharField(max_length=50, blank=True)
    address = models.TextField(blank=True)

    objects = CustomUserManager()

    USERNAME_FIELD = 'email'
    REQUIRED_FIELDS = ['first_name', 'last_name']

    def save(self, *args, **kwargs):
        if not self.username:
            self.username = self.email
        # Sync Django is_staff flag for internal roles
        if self.role in [self.Role.ADMIN, self.Role.STAFF]:
            self.is_staff = True
        else:
            self.is_staff = False
        super().save(*args, **kwargs)

    @property
    def is_admin_user(self):
        return self.role == self.Role.ADMIN or self.is_superuser

    @property
    def is_internal_staff(self):
        return self.role in [self.Role.ADMIN, self.Role.STAFF] or self.is_superuser

    @property
    def is_customer_user(self):
        return self.role == self.Role.CUSTOMER

    @property
    def display_name(self):
        if self.first_name or self.last_name:
            full = f"{self.first_name} {self.last_name}".strip()
            if self.company_name:
                return f"{full} ({self.company_name})"
            return full
        if self.company_name:
            return self.company_name
        return self.email

    def __str__(self):
        return f"{self.display_name} [{self.get_role_display()}]"


class PasswordResetToken(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='reset_tokens')
    token = models.CharField(max_length=64, unique=True, default=uuid.uuid4)
    created_at = models.DateTimeField(auto_now_add=True)
    is_used = models.BooleanField(default=False)

    def is_valid(self):
        # Valid for 24 hours
        if self.is_used:
            return False
        expiry = self.created_at + timezone.timedelta(hours=24)
        return timezone.now() <= expiry

    def __str__(self):
        return f"Token for {self.user.email} (used: {self.is_used})"


# -------------------------------------------------------------------------
# Products, Variants & Tax Rules
# -------------------------------------------------------------------------

class TaxRule(models.Model):
    name = models.CharField(max_length=100)
    rate = models.DecimalField(max_digits=5, decimal_places=2, help_text="Tax percentage e.g. 10.00 for 10%")
    description = models.CharField(max_length=255, blank=True)
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)

    def calculate_tax(self, amount):
        if not self.is_active or amount <= 0:
            return Decimal('0.00')
        return (amount * (self.rate / Decimal('100.00'))).quantize(Decimal('0.01'))

    def __str__(self):
        return f"{self.name} ({self.rate}%)"


class Product(models.Model):
    class ProductType(models.TextChoices):
        SOFTWARE = 'software', 'Business Software'
        ADDON = 'addon', 'Add-on'
        SERVICE = 'service', 'Recurring Service'
        PHYSICAL = 'physical', 'Hardware / Equipment'

    name = models.CharField(max_length=200)
    product_type = models.CharField(max_length=20, choices=ProductType.choices, default=ProductType.SOFTWARE)
    sales_price = models.DecimalField(max_digits=10, decimal_places=2)
    cost_price = models.DecimalField(max_digits=10, decimal_places=2, default=Decimal('0.00'))
    default_tax_rule = models.ForeignKey(TaxRule, on_delete=models.SET_NULL, null=True, blank=True)
    notes = models.TextField(blank=True)
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.name} (${self.sales_price})"


class ProductVariant(models.Model):
    product = models.ForeignKey(Product, on_delete=models.CASCADE, related_name='variants')
    attribute_name = models.CharField(max_length=100, default='Brand', help_text="e.g. Brand, Edition, Capacity")
    variant_value = models.CharField(max_length=100, help_text="e.g. Odoo, Standard, Premium")
    price_extra = models.DecimalField(
        max_digits=10, decimal_places=2, default=Decimal('0.00'),
        help_text="Extra charge added to product sales price (e.g. 560.00 for Odoo brand)"
    )

    @property
    def total_price(self):
        return self.product.sales_price + self.price_extra

    def __str__(self):
        if self.price_extra > 0:
            return f"{self.product.name} [{self.attribute_name}: {self.variant_value}] (+${self.price_extra})"
        return f"{self.product.name} [{self.attribute_name}: {self.variant_value}]"


# -------------------------------------------------------------------------
# Plans & Policy Lifecycle Rules
# -------------------------------------------------------------------------

class Plan(models.Model):
    class BillingInterval(models.TextChoices):
        DAILY = 'daily', 'Daily'
        WEEKLY = 'weekly', 'Weekly'
        MONTHLY = 'monthly', 'Monthly'
        YEARLY = 'yearly', 'Yearly'

    name = models.CharField(max_length=150)
    code = models.SlugField(max_length=100, unique=True)
    description = models.TextField(blank=True)
    cost = models.DecimalField(max_digits=10, decimal_places=2, help_text="Base recurring price per interval")
    billing_interval = models.CharField(max_length=20, choices=BillingInterval.choices, default=BillingInterval.MONTHLY)
    min_quantity = models.PositiveIntegerField(default=1, help_text="Minimum seats / quantity")
    available_from = models.DateField(default=timezone.now)
    available_to = models.DateField(null=True, blank=True, help_text="Optional end date for plan availability")
    is_active = models.BooleanField(default=True)

    # Admin configured lifecycle behavior rules (from Scene 2)
    auto_close_on_end = models.BooleanField(
        default=False,
        help_text="Some plans close on their own when they end"
    )
    allow_close_early = models.BooleanField(
        default=True,
        help_text="Allow subscription to be closed early by customer or staff"
    )
    allow_pause = models.BooleanField(
        default=True,
        help_text="Allow subscription to be paused and resumed"
    )
    allow_renewal = models.BooleanField(
        default=True,
        help_text="Allow subscription to be renewed before or upon expiration"
    )

    created_at = models.DateTimeField(auto_now_add=True)

    def is_currently_available(self, target_date=None):
        if not self.is_active:
            return False
        d = target_date or timezone.now().date()
        if self.available_from and d < self.available_from:
            return False
        if self.available_to and d > self.available_to:
            return False
        return True

    def calculate_next_date(self, from_date):
        if self.billing_interval == self.BillingInterval.DAILY:
            return from_date + relativedelta(days=1)
        elif self.billing_interval == self.BillingInterval.WEEKLY:
            return from_date + relativedelta(weeks=1)
        elif self.billing_interval == self.BillingInterval.MONTHLY:
            return from_date + relativedelta(months=1)
        elif self.billing_interval == self.BillingInterval.YEARLY:
            return from_date + relativedelta(years=1)
        return from_date + relativedelta(months=1)

    def __str__(self):
        return f"{self.name} (${self.cost} / {self.get_billing_interval_display()})"


# -------------------------------------------------------------------------
# Quotation Templates & Subscriptions
# -------------------------------------------------------------------------

class QuotationTemplate(models.Model):
    name = models.CharField(max_length=150)
    plan = models.ForeignKey(Plan, on_delete=models.CASCADE, related_name='templates')
    valid_days = models.PositiveIntegerField(default=15, help_text="Template offer stays valid for this many days")
    notes = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.name} (Valid {self.valid_days} days)"


class QuotationTemplateLine(models.Model):
    template = models.ForeignKey(QuotationTemplate, on_delete=models.CASCADE, related_name='lines')
    product = models.ForeignKey(Product, on_delete=models.CASCADE)
    variant = models.ForeignKey(ProductVariant, on_delete=models.SET_NULL, null=True, blank=True)
    quantity = models.PositiveIntegerField(default=1)
    unit_price = models.DecimalField(max_digits=10, decimal_places=2)
    tax_rule = models.ForeignKey(TaxRule, on_delete=models.SET_NULL, null=True, blank=True)

    def save(self, *args, **kwargs):
        if not self.unit_price:
            if self.variant:
                self.unit_price = self.variant.total_price
            else:
                self.unit_price = self.product.sales_price
        super().save(*args, **kwargs)


class Subscription(models.Model):
    class Status(models.TextChoices):
        DRAFT = 'draft', 'Draft'
        QUOTATION = 'quotation', 'Quotation'
        CONFIRMED = 'confirmed', 'Confirmed'
        ACTIVE = 'active', 'Active'
        PAUSED = 'paused', 'Paused'
        CLOSED = 'closed', 'Closed'

    PAYMENT_TERMS_CHOICES = [
        ('immediate', 'Immediate Payment'),
        ('net_15', '15 Days (Net 15)'),
        ('net_30', '30 Days (Net 30)'),
        ('net_60', '60 Days (Net 60)'),
    ]

    subscription_number = models.CharField(max_length=50, unique=True, db_index=True)
    customer = models.ForeignKey(User, on_delete=models.CASCADE, related_name='subscriptions')
    plan = models.ForeignKey(Plan, on_delete=models.PROTECT, related_name='subscriptions')
    status = models.CharField(max_length=20, choices=Status.choices, default=Status.DRAFT, db_index=True)
    start_date = models.DateField(default=timezone.now)
    expiry_date = models.DateField(null=True, blank=True)
    quotation_valid_until = models.DateField(null=True, blank=True)
    payment_terms = models.CharField(max_length=30, choices=PAYMENT_TERMS_CHOICES, default='net_30')
    last_billed_date = models.DateField(null=True, blank=True)
    next_billing_date = models.DateField(null=True, blank=True, db_index=True)
    notes = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['-created_at']

    def calculate_subtotal(self):
        return sum(line.subtotal for line in self.lines.all()) or Decimal('0.00')

    def calculate_taxes(self):
        return sum(line.tax_amount for line in self.lines.all()) or Decimal('0.00')

    def calculate_grand_total(self):
        return sum(line.total_amount for line in self.lines.all()) or Decimal('0.00')

    def advance_next_billing_date(self):
        base_date = self.next_billing_date or self.start_date
        self.last_billed_date = base_date
        self.next_billing_date = self.plan.calculate_next_date(base_date)
        self.save(update_fields=['last_billed_date', 'next_billing_date'])

    def can_pause(self):
        return self.status == self.Status.ACTIVE and self.plan.allow_pause

    def can_resume(self):
        return self.status == self.Status.PAUSED

    def can_close_early(self):
        return self.status in [self.Status.ACTIVE, self.Status.PAUSED] and self.plan.allow_close_early

    def can_renew(self):
        return self.status in [self.Status.ACTIVE, self.Status.CLOSED] and self.plan.allow_renewal

    def __str__(self):
        return f"{self.subscription_number} - {self.customer.display_name} ({self.get_status_display()})"


class SubscriptionLine(models.Model):
    subscription = models.ForeignKey(Subscription, on_delete=models.CASCADE, related_name='lines')
    product = models.ForeignKey(Product, on_delete=models.PROTECT)
    variant = models.ForeignKey(ProductVariant, on_delete=models.SET_NULL, null=True, blank=True)
    quantity = models.PositiveIntegerField(default=1)
    unit_price = models.DecimalField(max_digits=10, decimal_places=2)
    tax_rule = models.ForeignKey(TaxRule, on_delete=models.SET_NULL, null=True, blank=True)
    subtotal = models.DecimalField(max_digits=10, decimal_places=2, default=Decimal('0.00'))
    tax_amount = models.DecimalField(max_digits=10, decimal_places=2, default=Decimal('0.00'))
    total_amount = models.DecimalField(max_digits=10, decimal_places=2, default=Decimal('0.00'))

    def save(self, *args, **kwargs):
        if not self.unit_price or self.unit_price == 0:
            if self.variant:
                self.unit_price = self.variant.total_price
            else:
                self.unit_price = self.product.sales_price

        self.subtotal = (Decimal(self.quantity) * self.unit_price).quantize(Decimal('0.01'))
        if self.tax_rule:
            self.tax_amount = self.tax_rule.calculate_tax(self.subtotal)
        else:
            self.tax_amount = Decimal('0.00')
        self.total_amount = self.subtotal + self.tax_amount
        super().save(*args, **kwargs)

    def __str__(self):
        label = self.variant.variant_value if self.variant else self.product.name
        return f"{self.quantity}x {label} @ ${self.unit_price}"


# -------------------------------------------------------------------------
# Discount Rules (Scene 5)
# -------------------------------------------------------------------------

class DiscountRule(models.Model):
    class DiscountType(models.TextChoices):
        PERCENTAGE = 'percentage', 'Percentage (%)'
        FIXED = 'fixed', 'Fixed Amount ($)'

    class Scope(models.TextChoices):
        SUBSCRIPTION = 'subscription', 'Whole Subscription'
        PRODUCT = 'product', 'Specific Product'

    name = models.CharField(max_length=150)
    code = models.CharField(max_length=50, unique=True, help_text="Coupon / Promo code e.g. SUMMER20")
    discount_type = models.CharField(max_length=20, choices=DiscountType.choices, default=DiscountType.PERCENTAGE)
    discount_value = models.DecimalField(max_digits=10, decimal_places=2, help_text="e.g. 15.00 for 15% or 50.00 for $50")
    min_purchase_amount = models.DecimalField(max_digits=10, decimal_places=2, default=Decimal('0.00'), help_text="Minimum invoice amount")
    min_quantity = models.PositiveIntegerField(default=0, help_text="Minimum seats / quantity")
    start_date = models.DateField(default=timezone.now)
    end_date = models.DateField(help_text="End date for the discount rule")
    max_uses = models.PositiveIntegerField(null=True, blank=True, help_text="Max redemptions (leave blank for unlimited)")
    current_uses = models.PositiveIntegerField(default=0)
    scope = models.CharField(max_length=20, choices=Scope.choices, default=Scope.SUBSCRIPTION)
    product = models.ForeignKey(
        Product, on_delete=models.SET_NULL, null=True, blank=True,
        help_text="Product to which this discount applies (if scope is Specific Product)"
    )
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)

    def is_valid_for(self, amount, total_qty=1, product=None, target_date=None):
        if not self.is_active:
            return False, "Discount is inactive."
        d = target_date or timezone.now().date()
        if d < self.start_date:
            return False, "Discount period has not started yet."
        if d > self.end_date:
            return False, "Discount has expired."
        if self.max_uses and self.current_uses >= self.max_uses:
            return False, "Discount usage limit reached."
        if self.min_purchase_amount and amount < self.min_purchase_amount:
            return False, f"Minimum purchase of ${self.min_purchase_amount} required."
        if self.min_quantity and total_qty < self.min_quantity:
            return False, f"Minimum quantity of {self.min_quantity} items required."
        if self.scope == self.Scope.PRODUCT and self.product and product != self.product:
            return False, f"Discount only applies to product {self.product.name}."
        return True, "Valid"

    def compute_discount_amount(self, eligible_amount):
        if self.discount_type == self.DiscountType.PERCENTAGE:
            disc = (eligible_amount * (self.discount_value / Decimal('100.00'))).quantize(Decimal('0.01'))
            return min(disc, eligible_amount)
        elif self.discount_type == self.DiscountType.FIXED:
            return min(self.discount_value, eligible_amount)
        return Decimal('0.00')

    def record_usage(self):
        self.current_uses += 1
        if self.max_uses and self.current_uses >= self.max_uses:
            self.is_active = False
        self.save(update_fields=['current_uses', 'is_active'])

    def __str__(self):
        val_str = f"{self.discount_value}%" if self.discount_type == self.DiscountType.PERCENTAGE else f"${self.discount_value}"
        return f"{self.name} [{self.code}] ({val_str} off)"


# -------------------------------------------------------------------------
# Invoices, Invoice Lines & Payments (Scene 4 & 6)
# -------------------------------------------------------------------------

class Invoice(models.Model):
    class Status(models.TextChoices):
        DRAFT = 'draft', 'Draft'
        CONFIRMED = 'confirmed', 'Confirmed'
        PAID = 'paid', 'Paid'
        CANCELLED = 'cancelled', 'Cancelled'

    invoice_number = models.CharField(max_length=50, unique=True, db_index=True)
    subscription = models.ForeignKey(Subscription, on_delete=models.SET_NULL, null=True, blank=True, related_name='invoices')
    customer = models.ForeignKey(User, on_delete=models.PROTECT, related_name='invoices')
    invoice_date = models.DateField(default=timezone.now, db_index=True)
    due_date = models.DateField(db_index=True)
    status = models.CharField(max_length=20, choices=Status.choices, default=Status.DRAFT, db_index=True)
    billing_period_start = models.DateField(null=True, blank=True)
    billing_period_end = models.DateField(null=True, blank=True)

    subtotal = models.DecimalField(max_digits=12, decimal_places=2, default=Decimal('0.00'))
    discount_rule = models.ForeignKey(DiscountRule, on_delete=models.SET_NULL, null=True, blank=True)
    discount_amount = models.DecimalField(max_digits=12, decimal_places=2, default=Decimal('0.00'))
    tax_amount = models.DecimalField(max_digits=12, decimal_places=2, default=Decimal('0.00'))
    total_amount = models.DecimalField(max_digits=12, decimal_places=2, default=Decimal('0.00'))
    amount_paid = models.DecimalField(max_digits=12, decimal_places=2, default=Decimal('0.00'))
    balance_due = models.DecimalField(max_digits=12, decimal_places=2, default=Decimal('0.00'))

    sent_at = models.DateTimeField(null=True, blank=True)
    notes = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['-invoice_date', '-id']

    def is_overdue(self):
        if self.status in [self.Status.PAID, self.Status.CANCELLED]:
            return False
        return self.due_date < timezone.now().date() and self.balance_due > 0

    @property
    def overdue_days(self):
        if not self.is_overdue():
            return 0
        diff = timezone.now().date() - self.due_date
        return diff.days

    def update_totals(self):
        lines = self.lines.all()
        if lines.exists():
            computed_subtotal = sum(line.quantity * line.unit_price for line in lines)
            self.subtotal = computed_subtotal.quantize(Decimal('0.01'))
        elif not self.subtotal:
            self.subtotal = Decimal('0.00')

        # Recalculate discount if rule is present
        if self.discount_rule:
            self.discount_amount = self.discount_rule.compute_discount_amount(self.subtotal)
        else:
            self.discount_amount = Decimal('0.00')

        # Recalculate tax
        tax_sum = Decimal('0.00')
        if lines.exists():
            for line in lines:
                line_sub = (line.quantity * line.unit_price)
                if self.subtotal > 0 and self.discount_amount > 0:
                    # Pro-rate discount on line before tax
                    ratio = line_sub / self.subtotal
                    line_discount = (self.discount_amount * ratio).quantize(Decimal('0.01'))
                else:
                    line_discount = Decimal('0.00')
                line_taxable = max(Decimal('0.00'), line_sub - line_discount)
                if line.tax_rule:
                    line_tax = line.tax_rule.calculate_tax(line_taxable)
                else:
                    line_tax = Decimal('0.00')
                line.discount_amount = line_discount
                line.tax_amount = line_tax
                line.line_total = line_taxable + line_tax
                line.save(update_fields=['discount_amount', 'tax_amount', 'line_total'])
                tax_sum += line_tax
            self.tax_amount = tax_sum.quantize(Decimal('0.01'))
            self.total_amount = (self.subtotal - self.discount_amount + self.tax_amount).quantize(Decimal('0.01'))
        else:
            self.total_amount = (self.subtotal - self.discount_amount + self.tax_amount).quantize(Decimal('0.01'))
        
        # Calculate paid amount from payments
        paid_sum = sum(p.amount for p in self.payments.all()) or Decimal('0.00')
        self.amount_paid = paid_sum.quantize(Decimal('0.01'))
        self.balance_due = max(Decimal('0.00'), (self.total_amount - self.amount_paid).quantize(Decimal('0.01')))

        if self.balance_due <= 0 and self.total_amount > 0 and self.status == self.Status.CONFIRMED:
            self.status = self.Status.PAID

        self.save()

    def __str__(self):
        return f"{self.invoice_number} - {self.customer.display_name} (${self.total_amount}) [{self.get_status_display()}]"


class InvoiceLine(models.Model):
    invoice = models.ForeignKey(Invoice, on_delete=models.CASCADE, related_name='lines')
    product = models.ForeignKey(Product, on_delete=models.PROTECT)
    variant = models.ForeignKey(ProductVariant, on_delete=models.SET_NULL, null=True, blank=True)
    description = models.CharField(max_length=255)
    quantity = models.PositiveIntegerField(default=1)
    unit_price = models.DecimalField(max_digits=10, decimal_places=2)
    tax_rule = models.ForeignKey(TaxRule, on_delete=models.SET_NULL, null=True, blank=True)
    discount_amount = models.DecimalField(max_digits=10, decimal_places=2, default=Decimal('0.00'))
    tax_amount = models.DecimalField(max_digits=10, decimal_places=2, default=Decimal('0.00'))
    line_total = models.DecimalField(max_digits=12, decimal_places=2, default=Decimal('0.00'))

    def __str__(self):
        return f"{self.invoice.invoice_number} Line: {self.description} (${self.line_total})"


class Payment(models.Model):
    class PaymentMethod(models.TextChoices):
        CREDIT_CARD = 'credit_card', 'Credit Card'
        BANK_TRANSFER = 'bank_transfer', 'Bank Transfer'
        PAYPAL = 'paypal', 'PayPal'
        CASH = 'cash', 'Cash'
        CHECK = 'check', 'Check'

    invoice = models.ForeignKey(Invoice, on_delete=models.CASCADE, related_name='payments')
    payment_date = models.DateField(default=timezone.now, db_index=True)
    amount = models.DecimalField(max_digits=12, decimal_places=2)
    payment_method = models.CharField(max_length=30, choices=PaymentMethod.choices, default=PaymentMethod.BANK_TRANSFER)
    transaction_reference = models.CharField(max_length=100, blank=True, help_text="Reference/Transaction/Check ID")
    note = models.TextField(blank=True)
    recorded_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    def save(self, *args, **kwargs):
        super().save(*args, **kwargs)
        # Update the parent invoice amounts and status
        self.invoice.update_totals()

    def __str__(self):
        return f"Payment ${self.amount} for {self.invoice.invoice_number} via {self.get_payment_method_display()}"


# -------------------------------------------------------------------------
# Enhancement H: Admin Audit Log
# -------------------------------------------------------------------------

class AuditLog(models.Model):
    """Timestamped log of all significant system events."""
    class EventType(models.TextChoices):
        LOGIN = 'login', 'User Login'
        LOGOUT = 'logout', 'User Logout'
        STATUS_CHANGE = 'status_change', 'Status Change'
        PAYMENT = 'payment', 'Payment Recorded'
        INVOICE_SENT = 'invoice_sent', 'Invoice Sent'
        SUBSCRIPTION_CREATED = 'sub_created', 'Subscription Created'
        SUBSCRIPTION_CLOSED = 'sub_closed', 'Subscription Closed'
        BILLING_DAY = 'billing_day', 'Billing Day Run'
        DUNNING = 'dunning', 'Dunning Email Sent'
        EXPORT = 'export', 'Data Export'
        OTHER = 'other', 'Other'

    event_type = models.CharField(max_length=30, choices=EventType.choices, default=EventType.OTHER, db_index=True)
    actor = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True, related_name='audit_logs')
    target_model = models.CharField(max_length=50, blank=True, help_text="Model name e.g. Invoice, Subscription")
    target_id = models.PositiveIntegerField(null=True, blank=True, help_text="PK of the affected object")
    description = models.TextField()
    ip_address = models.GenericIPAddressField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True, db_index=True)

    class Meta:
        ordering = ['-created_at']

    def __str__(self):
        actor_str = self.actor.email if self.actor else 'System'
        return f"[{self.get_event_type_display()}] {actor_str}: {self.description[:60]}"


# -------------------------------------------------------------------------
# Enhancement I: Dunning Campaign Log
# -------------------------------------------------------------------------

class DunningLog(models.Model):
    """Tracks automated overdue follow-up emails per invoice."""
    class Level(models.TextChoices):
        DAY1 = 'day1', 'Day 1 Reminder'
        DAY7 = 'day7', 'Day 7 Follow-up'
        DAY14 = 'day14', 'Day 14 Final Notice'

    invoice = models.ForeignKey(Invoice, on_delete=models.CASCADE, related_name='dunning_logs')
    level = models.CharField(max_length=10, choices=Level.choices)
    sent_at = models.DateTimeField(auto_now_add=True)
    sent_to = models.EmailField()
    success = models.BooleanField(default=True)
    notes = models.TextField(blank=True)

    class Meta:
        ordering = ['-sent_at']

    def __str__(self):
        return f"Dunning {self.level} for {self.invoice.invoice_number} -> {self.sent_to}"
