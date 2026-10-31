import datetime
from decimal import Decimal
from django.core.management.base import BaseCommand
from django.utils import timezone
from brightloop_app.models import (
    User, Product, ProductVariant, TaxRule, Plan,
    QuotationTemplate, QuotationTemplateLine,
    Subscription, SubscriptionLine,
    DiscountRule, Invoice, InvoiceLine, Payment, AuditLog, DunningLog
)

class Command(BaseCommand):
    help = "Repeatable seed script: wipes existing demo records and populates clean, production-grade data"

    def handle(self, *args, **options):
        self.stdout.write(self.style.NOTICE("Resetting and seeding Brightloop Software database..."))

        # Clean existing business records to prevent duplicates and ensure repeatability
        Payment.objects.all().delete()
        InvoiceLine.objects.all().delete()
        Invoice.objects.all().delete()
        SubscriptionLine.objects.all().delete()
        Subscription.objects.all().delete()
        QuotationTemplateLine.objects.all().delete()
        QuotationTemplate.objects.all().delete()
        DiscountRule.objects.all().delete()
        ProductVariant.objects.all().delete()
        Product.objects.all().delete()
        Plan.objects.all().delete()
        TaxRule.objects.all().delete()
        AuditLog.objects.all().delete()
        DunningLog.objects.all().delete()

        # ---------------------------------------------------------------------
        # 1. Tax Rules
        # ---------------------------------------------------------------------
        tax_standard = TaxRule.objects.create(
            name="Standard Sales Tax",
            rate=Decimal('8.25'),
            description="State and city standard sales tax"
        )
        tax_vat = TaxRule.objects.create(
            name="EU VAT (10%)",
            rate=Decimal('10.00'),
            description="Value Added Tax"
        )

        # ---------------------------------------------------------------------
        # 2. Demo Logins (1 Clean User per Role with Strong Passwords)
        # ---------------------------------------------------------------------
        # Passwords adhere to BrightloopPasswordValidator (>8 chars, uppercase, lowercase, special char)
        ADMIN_PASSWORD = "Brightloop#Admin2026!"
        STAFF_PASSWORD = "Brightloop#Staff2026!"
        CUSTOMER_PASSWORD = "Brightloop#Cust2026!"

        # Admin
        admin_user, _ = User.objects.get_or_create(
            email='admin@brightloop.com',
            defaults={
                'first_name': 'Elena',
                'last_name': 'Vance',
                'role': User.Role.ADMIN,
                'company_name': 'Brightloop Software HQ',
                'phone': '+1 (555) 019-2831',
                'is_staff': True,
                'is_superuser': True
            }
        )
        admin_user.set_password(ADMIN_PASSWORD)
        admin_user.save()

        # Staff
        staff_user, _ = User.objects.get_or_create(
            email='staff@brightloop.com',
            defaults={
                'first_name': 'Sarah',
                'last_name': 'Jenkins',
                'role': User.Role.STAFF,
                'company_name': 'Brightloop Software Sales',
                'phone': '+1 (555) 019-4412',
                'is_staff': True
            }
        )
        staff_user.set_password(STAFF_PASSWORD)
        staff_user.save()

        # Customer
        customer_user, _ = User.objects.get_or_create(
            email='customer@brightloop.com',
            defaults={
                'first_name': 'Arthur',
                'last_name': 'Pendleton',
                'role': User.Role.CUSTOMER,
                'company_name': 'Acme Corporation',
                'phone': '+1 (555) 302-8800',
                'address': '500 Enterprise Way, Suite 400, Chicago, IL 60601',
            }
        )
        customer_user.set_password(CUSTOMER_PASSWORD)
        customer_user.save()

        # Remove any legacy uncleaned users
        User.objects.exclude(email__in=['admin@brightloop.com', 'staff@brightloop.com', 'customer@brightloop.com']).delete()

        # ---------------------------------------------------------------------
        # 3. Products & Configured Variants (Scene 2)
        # ---------------------------------------------------------------------
        prod_hosting = Product.objects.create(
            name="Dedicated Cloud Hosting",
            product_type=Product.ProductType.SERVICE,
            sales_price=Decimal('200.00'),
            cost_price=Decimal('60.00'),
            default_tax_rule=tax_standard,
            notes="Isolated managed cloud cluster with automated daily backups"
        )

        # Odoo brand variant adds $560 to price (Scene 2 specification)
        var_odoo_brand = ProductVariant.objects.create(
            product=prod_hosting,
            attribute_name="Brand",
            variant_value="Odoo",
            price_extra=Decimal('560.00')
        )
        var_std_brand = ProductVariant.objects.create(
            product=prod_hosting,
            attribute_name="Brand",
            variant_value="Standard Cloud",
            price_extra=Decimal('0.00')
        )

        prod_erp = Product.objects.create(
            name="Brightloop Core ERP",
            product_type=Product.ProductType.SOFTWARE,
            sales_price=Decimal('120.00'),
            cost_price=Decimal('30.00'),
            default_tax_rule=tax_standard,
            notes="Core enterprise resource planning module billed per seat"
        )

        prod_odoo_suite = Product.objects.create(
            name="Odoo Integration Suite",
            product_type=Product.ProductType.ADDON,
            sales_price=Decimal('85.00'),
            cost_price=Decimal('15.00'),
            default_tax_rule=tax_standard,
            notes="Bi-directional sync with Odoo apps, CRM, inventory and accounting"
        )

        prod_sla = Product.objects.create(
            name="24/7 Priority SLA Support",
            product_type=Product.ProductType.ADDON,
            sales_price=Decimal('99.00'),
            cost_price=Decimal('20.00'),
            default_tax_rule=tax_standard,
            notes="Guaranteed 15-minute response time with dedicated account engineer"
        )

        # ---------------------------------------------------------------------
        # 4. Plans & Policy Lifecycle Rules (Scene 2)
        # ---------------------------------------------------------------------
        today = timezone.now().date()

        plan_monthly = Plan.objects.create(
            code="monthly-starter",
            name="Monthly Starter",
            cost=Decimal('120.00'),
            billing_interval=Plan.BillingInterval.MONTHLY,
            min_quantity=1,
            available_from=today - datetime.timedelta(days=180),
            description="Ideal for small shops and startups billed monthly.",
            auto_close_on_end=False,
            allow_close_early=True,
            allow_pause=True,
            allow_renewal=True
        )

        plan_yearly = Plan.objects.create(
            code="professional-yearly",
            name="Professional Yearly",
            cost=Decimal('1200.00'),
            billing_interval=Plan.BillingInterval.YEARLY,
            min_quantity=5,
            available_from=today - datetime.timedelta(days=365),
            description="Annual agreement for growing businesses with annual discounting.",
            auto_close_on_end=False,
            allow_close_early=True,
            allow_pause=True,
            allow_renewal=True
        )

        plan_trial = Plan.objects.create(
            code="trial-special",
            name="Trial Special (Weekly)",
            cost=Decimal('49.00'),
            billing_interval=Plan.BillingInterval.WEEKLY,
            min_quantity=1,
            available_from=today - datetime.timedelta(days=30),
            description="Short-term trial plan that automatically closes on its own when finished.",
            auto_close_on_end=True,
            allow_close_early=False,
            allow_pause=False,
            allow_renewal=False
        )

        # ---------------------------------------------------------------------
        # 5. Quotation Templates (Scene 3)
        # ---------------------------------------------------------------------
        tmpl_smb = QuotationTemplate.objects.create(
            name="Standard SMB Onboarding Template",
            plan=plan_monthly,
            valid_days=15,
            notes="Pre-configured starter bundle for small business clients with Core ERP + Odoo Suite."
        )
        QuotationTemplateLine.objects.create(
            template=tmpl_smb,
            product=prod_erp,
            quantity=2,
            unit_price=Decimal('120.00'),
            tax_rule=tax_standard
        )
        QuotationTemplateLine.objects.create(
            template=tmpl_smb,
            product=prod_odoo_suite,
            quantity=1,
            unit_price=Decimal('85.00'),
            tax_rule=tax_standard
        )

        # ---------------------------------------------------------------------
        # 6. Discount Rules (Scene 5 - Active and Inactive)
        # ---------------------------------------------------------------------
        disc_summer = DiscountRule.objects.create(
            name="Summer Growth Promo (20% Off)",
            code="SUMMER20",
            discount_type=DiscountRule.DiscountType.PERCENTAGE,
            discount_value=Decimal('20.00'),
            min_purchase_amount=Decimal('500.00'),
            min_quantity=0,
            start_date=today - datetime.timedelta(days=30),
            end_date=today + datetime.timedelta(days=60),
            max_uses=50,
            current_uses=1,
            scope=DiscountRule.Scope.SUBSCRIPTION,
            is_active=True
        )

        # Inactive rule for testing toggle
        DiscountRule.objects.create(
            name="Early Bird Welcome (10% Off)",
            code="WELCOME10",
            discount_type=DiscountRule.DiscountType.PERCENTAGE,
            discount_value=Decimal('10.00'),
            min_purchase_amount=Decimal('100.00'),
            min_quantity=0,
            start_date=today - datetime.timedelta(days=60),
            end_date=today + datetime.timedelta(days=30),
            max_uses=10,
            current_uses=0,
            scope=DiscountRule.Scope.SUBSCRIPTION,
            is_active=False
        )

        # ---------------------------------------------------------------------
        # 7. Subscriptions Across All 5 Lifecycle States (Draft, Quotation, Confirmed, Active, Closed)
        # ---------------------------------------------------------------------
        # 1. Draft
        sub_draft = Subscription.objects.create(
            subscription_number="SUB-2026-00001",
            customer=customer_user,
            plan=plan_monthly,
            status=Subscription.Status.DRAFT,
            start_date=today,
            payment_terms='net_30',
            notes="Draft subscription proposal being drafted by sales team."
        )
        SubscriptionLine.objects.create(
            subscription=sub_draft,
            product=prod_erp,
            quantity=1,
            unit_price=Decimal('120.00'),
            tax_rule=tax_standard
        )

        # 2. Quotation
        sub_quote = Subscription.objects.create(
            subscription_number="SUB-2026-00002",
            customer=customer_user,
            plan=plan_yearly,
            status=Subscription.Status.QUOTATION,
            start_date=today,
            quotation_valid_until=today + datetime.timedelta(days=15),
            payment_terms='net_30',
            notes="Quotation awaiting customer signoff."
        )
        SubscriptionLine.objects.create(
            subscription=sub_quote,
            product=prod_erp,
            quantity=5,
            unit_price=Decimal('120.00'),
            tax_rule=tax_standard
        )
        SubscriptionLine.objects.create(
            subscription=sub_quote,
            product=prod_sla,
            quantity=1,
            unit_price=Decimal('99.00'),
            tax_rule=tax_standard
        )

        # 3. Confirmed
        sub_confirmed = Subscription.objects.create(
            subscription_number="SUB-2026-00003",
            customer=customer_user,
            plan=plan_monthly,
            status=Subscription.Status.CONFIRMED,
            start_date=today,
            payment_terms='net_15',
            next_billing_date=today,
            notes="Customer accepted quotation; ready for Billing Day activation."
        )
        SubscriptionLine.objects.create(
            subscription=sub_confirmed,
            product=prod_erp,
            quantity=2,
            unit_price=Decimal('120.00'),
            tax_rule=tax_standard
        )
        SubscriptionLine.objects.create(
            subscription=sub_confirmed,
            product=prod_odoo_suite,
            quantity=1,
            unit_price=Decimal('85.00'),
            tax_rule=tax_standard
        )

        # 4. Active (Includes Cloud Hosting with Odoo +560 brand variant)
        sub_active = Subscription.objects.create(
            subscription_number="SUB-2026-00004",
            customer=customer_user,
            plan=plan_yearly,
            status=Subscription.Status.ACTIVE,
            start_date=today - datetime.timedelta(days=120),
            expiry_date=today + datetime.timedelta(days=245),
            payment_terms='net_30',
            last_billed_date=today - datetime.timedelta(days=120),
            next_billing_date=today + datetime.timedelta(days=245),
            notes="Annual contract with 15 seats and Odoo-branded cloud infrastructure."
        )
        SubscriptionLine.objects.create(
            subscription=sub_active,
            product=prod_erp,
            quantity=15,
            unit_price=Decimal('120.00'),
            tax_rule=tax_standard
        )
        SubscriptionLine.objects.create(
            subscription=sub_active,
            product=prod_hosting,
            variant=var_odoo_brand,
            quantity=1,
            unit_price=var_odoo_brand.total_price, # $200 + $560 = $760
            tax_rule=tax_standard
        )
        SubscriptionLine.objects.create(
            subscription=sub_active,
            product=prod_sla,
            quantity=1,
            unit_price=Decimal('99.00'),
            tax_rule=tax_standard
        )

        # 5. Closed (Auto-closed trial contract)
        sub_closed = Subscription.objects.create(
            subscription_number="SUB-2026-00005",
            customer=customer_user,
            plan=plan_trial,
            status=Subscription.Status.CLOSED,
            start_date=today - datetime.timedelta(days=35),
            expiry_date=today - datetime.timedelta(days=7),
            payment_terms='immediate',
            notes="Weekly trial completed; automatically closed per plan lifecycle policy."
        )
        SubscriptionLine.objects.create(
            subscription=sub_closed,
            product=prod_erp,
            quantity=1,
            unit_price=Decimal('120.00'),
            tax_rule=tax_standard
        )

        # ---------------------------------------------------------------------
        # 8. Invoices (Paid, Outstanding, Overdue) & Payments (Scenes 4 & 6)
        # ---------------------------------------------------------------------
        # 1. Paid Invoice
        inv_paid = Invoice.objects.create(
            invoice_number="INV-2026-00001",
            subscription=sub_active,
            customer=customer_user,
            invoice_date=today - datetime.timedelta(days=120),
            due_date=today - datetime.timedelta(days=90),
            status=Invoice.Status.PAID,
            billing_period_start=today - datetime.timedelta(days=120),
            billing_period_end=today + datetime.timedelta(days=245),
            discount_rule=disc_summer,
            notes="Annual contract invoice with Summer Promo discount applied. Paid in full."
        )
        InvoiceLine.objects.create(
            invoice=inv_paid,
            product=prod_erp,
            description="Brightloop Core ERP (15 Seats)",
            quantity=15,
            unit_price=Decimal('120.00'),
            tax_rule=tax_standard
        )
        InvoiceLine.objects.create(
            invoice=inv_paid,
            product=prod_hosting,
            variant=var_odoo_brand,
            description="Dedicated Cloud Hosting [Brand: Odoo]",
            quantity=1,
            unit_price=var_odoo_brand.total_price,
            tax_rule=tax_standard
        )
        inv_paid.update_totals()

        Payment.objects.create(
            invoice=inv_paid,
            payment_date=today - datetime.timedelta(days=110),
            amount=inv_paid.total_amount,
            payment_method=Payment.PaymentMethod.BANK_TRANSFER,
            transaction_reference="WIRE-ACME-0091",
            note="Full wire settlement",
            recorded_by=staff_user
        )

        # 2. Outstanding Invoice (Confirmed, Unpaid, Due in future)
        inv_outstanding = Invoice.objects.create(
            invoice_number="INV-2026-00002",
            subscription=sub_confirmed,
            customer=customer_user,
            invoice_date=today - datetime.timedelta(days=5),
            due_date=today + datetime.timedelta(days=10), # Due in 10 days
            status=Invoice.Status.CONFIRMED,
            billing_period_start=today - datetime.timedelta(days=5),
            billing_period_end=today + datetime.timedelta(days=25),
            notes="Monthly cycle invoice. Due in 10 days."
        )
        InvoiceLine.objects.create(
            invoice=inv_outstanding,
            product=prod_erp,
            description="Brightloop Core ERP (2 Seats)",
            quantity=2,
            unit_price=Decimal('120.00'),
            tax_rule=tax_standard
        )
        InvoiceLine.objects.create(
            invoice=inv_outstanding,
            product=prod_odoo_suite,
            description="Odoo Integration Suite",
            quantity=1,
            unit_price=Decimal('85.00'),
            tax_rule=tax_standard
        )
        inv_outstanding.update_totals()

        # 3. Overdue Invoice (Confirmed, Unpaid, Due date was 15 days ago)
        inv_overdue = Invoice.objects.create(
            invoice_number="INV-2026-00003",
            subscription=sub_active,
            customer=customer_user,
            invoice_date=today - datetime.timedelta(days=45),
            due_date=today - datetime.timedelta(days=15), # Overdue by 15 days
            status=Invoice.Status.CONFIRMED,
            billing_period_start=today - datetime.timedelta(days=45),
            billing_period_end=today - datetime.timedelta(days=15),
            notes="Previous cycle support invoice. Overdue - eligible for dunning chase."
        )
        InvoiceLine.objects.create(
            invoice=inv_overdue,
            product=prod_sla,
            description="24/7 Priority SLA Support (Monthly)",
            quantity=3,
            unit_price=Decimal('99.00'),
            tax_rule=tax_standard
        )
        inv_overdue.update_totals()

        # Initial Audit Log entry
        AuditLog.objects.create(
            event_type=AuditLog.EventType.OTHER,
            actor=admin_user,
            target_model="System",
            description="Clean production seed data initialized",
        )

        self.stdout.write(self.style.SUCCESS("Brightloop Software clean dataset successfully seeded!"))
        self.stdout.write(self.style.SUCCESS("\nDemo Logins Available:"))
        self.stdout.write(f"  • Administrator: admin@brightloop.com    | Password: {ADMIN_PASSWORD}")
        self.stdout.write(f"  • Staff:         staff@brightloop.com    | Password: {STAFF_PASSWORD}")
        self.stdout.write(f"  • Customer:      customer@brightloop.com | Password: {CUSTOMER_PASSWORD}\n")
