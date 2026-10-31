import datetime
from decimal import Decimal
from django.core.management.base import BaseCommand
from django.utils import timezone
from brightloop_app.models import (
    User, Product, ProductVariant, TaxRule, Plan,
    QuotationTemplate, QuotationTemplateLine,
    Subscription, SubscriptionLine,
    DiscountRule, Invoice, InvoiceLine, Payment
)

class Command(BaseCommand):
    help = "Seed database with realistic Brightloop Software business data"

    def handle(self, *args, **options):
        self.stdout.write(self.style.NOTICE("Seeding Brightloop Software data..."))

        # 1. Tax Rules
        tax_standard, _ = TaxRule.objects.get_or_create(
            name="Standard Sales Tax",
            defaults={'rate': Decimal('8.25'), 'description': 'State & City standard tax'}
        )
        tax_vat, _ = TaxRule.objects.get_or_create(
            name="EU VAT (10%)",
            defaults={'rate': Decimal('10.00'), 'description': 'Value Added Tax'}
        )
        tax_exempt, _ = TaxRule.objects.get_or_create(
            name="Tax Exempt",
            defaults={'rate': Decimal('0.00'), 'description': 'Zero rated / Non-profit'}
        )

        # 2. Users (Admin, Staff, Customers)
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
        admin_user.set_password('Admin@12345')
        admin_user.save()

        sarah_staff, _ = User.objects.get_or_create(
            email='sarah@brightloop.com',
            defaults={
                'first_name': 'Sarah',
                'last_name': 'Jenkins',
                'role': User.Role.STAFF,
                'company_name': 'Brightloop Software Sales',
                'phone': '+1 (555) 019-4412',
                'is_staff': True
            }
        )
        sarah_staff.set_password('Staff@12345')
        sarah_staff.save()

        david_staff, _ = User.objects.get_or_create(
            email='david@brightloop.com',
            defaults={
                'first_name': 'David',
                'last_name': 'Kim',
                'role': User.Role.STAFF,
                'company_name': 'Brightloop Software Finance',
                'phone': '+1 (555) 019-7788',
                'is_staff': True
            }
        )
        david_staff.set_password('Staff@12345')
        david_staff.save()

        cust_acme, _ = User.objects.get_or_create(
            email='acme@acmecorp.com',
            defaults={
                'first_name': 'Arthur',
                'last_name': 'Pendleton',
                'company_name': 'Acme Corporation',
                'phone': '+1 (555) 302-8800',
                'address': '500 Enterprise Way, Suite 400, Chicago, IL 60601',
                'role': User.Role.CUSTOMER
            }
        )
        cust_acme.set_password('Acme@12345')
        cust_acme.save()

        cust_bistro, _ = User.objects.get_or_create(
            email='bistro@cornercafe.com',
            defaults={
                'first_name': 'Marie',
                'last_name': 'Laurent',
                'company_name': 'Corner Cafe & Bakery',
                'phone': '+1 (555) 234-9090',
                'address': '12 Elm Street, Portland, OR 97201',
                'role': User.Role.CUSTOMER
            }
        )
        cust_bistro.set_password('Corner@12345')
        cust_bistro.save()

        cust_techflow, _ = User.objects.get_or_create(
            email='techflow@techflow.io',
            defaults={
                'first_name': 'Devon',
                'last_name': 'Miles',
                'company_name': 'TechFlow Dynamics',
                'phone': '+1 (555) 890-1122',
                'address': '808 Tech Boulevard, Austin, TX 78701',
                'role': User.Role.CUSTOMER
            }
        )
        cust_techflow.set_password('TechFlow@12345')
        cust_techflow.save()

        cust_spark, _ = User.objects.get_or_create(
            email='spark@sparklabs.com',
            defaults={
                'first_name': 'Chloe',
                'last_name': 'Bennett',
                'company_name': 'Spark Labs Inc.',
                'phone': '+1 (555) 441-2990',
                'address': '42 Innovation Road, Boston, MA 02110',
                'role': User.Role.CUSTOMER
            }
        )
        cust_spark.set_password('Spark@12345')
        cust_spark.save()

        # 3. Products & Variants (Scene 2)
        prod_erp, _ = Product.objects.get_or_create(
            name="Brightloop Core ERP",
            defaults={
                'product_type': Product.ProductType.SOFTWARE,
                'sales_price': Decimal('120.00'),
                'cost_price': Decimal('30.00'),
                'default_tax_rule': tax_standard,
                'notes': 'Core enterprise resource planning module billed per seat'
            }
        )

        prod_odoo_suite, _ = Product.objects.get_or_create(
            name="Odoo Integration Suite",
            defaults={
                'product_type': Product.ProductType.ADDON,
                'sales_price': Decimal('85.00'),
                'cost_price': Decimal('15.00'),
                'default_tax_rule': tax_standard,
                'notes': 'Bi-directional sync with Odoo apps, CRM, inventory and accounting'
            }
        )

        prod_analytics, _ = Product.objects.get_or_create(
            name="Advanced Analytics Module",
            defaults={
                'product_type': Product.ProductType.SOFTWARE,
                'sales_price': Decimal('150.00'),
                'cost_price': Decimal('25.00'),
                'default_tax_rule': tax_standard,
                'notes': 'Real-time cohort, churn, and financial reporting dashboards'
            }
        )

        prod_hosting, _ = Product.objects.get_or_create(
            name="Dedicated Cloud Hosting",
            defaults={
                'product_type': Product.ProductType.SERVICE,
                'sales_price': Decimal('200.00'),
                'cost_price': Decimal('60.00'),
                'default_tax_rule': tax_standard,
                'notes': 'Isolated managed cloud cluster with SLA and automated daily backups'
            }
        )

        # Variant: Choosing Odoo brand adds 560 to price (Scene 2)
        var_odoo_brand, _ = ProductVariant.objects.get_or_create(
            product=prod_hosting,
            attribute_name="Brand",
            variant_value="Odoo",
            defaults={'price_extra': Decimal('560.00')}
        )

        var_std_brand, _ = ProductVariant.objects.get_or_create(
            product=prod_hosting,
            attribute_name="Brand",
            variant_value="Standard Cloud",
            defaults={'price_extra': Decimal('0.00')}
        )

        prod_sla, _ = Product.objects.get_or_create(
            name="24/7 Priority SLA Support",
            defaults={
                'product_type': Product.ProductType.ADDON,
                'sales_price': Decimal('99.00'),
                'cost_price': Decimal('20.00'),
                'default_tax_rule': tax_standard,
                'notes': 'Guaranteed 15-minute response time and dedicated account engineer'
            }
        )

        # 4. Plans & Policies (Scene 2)
        plan_monthly, _ = Plan.objects.get_or_create(
            code="monthly-starter",
            defaults={
                'name': "Monthly Starter",
                'cost': Decimal('120.00'),
                'billing_interval': Plan.BillingInterval.MONTHLY,
                'min_quantity': 1,
                'available_from': timezone.now().date() - datetime.timedelta(days=180),
                'description': 'Ideal for small shops and startups billed monthly.',
                'auto_close_on_end': False,
                'allow_close_early': True,
                'allow_pause': True,
                'allow_renewal': True
            }
        )

        plan_yearly, _ = Plan.objects.get_or_create(
            code="professional-yearly",
            defaults={
                'name': "Professional Yearly",
                'cost': Decimal('1200.00'),
                'billing_interval': Plan.BillingInterval.YEARLY,
                'min_quantity': 5,
                'available_from': timezone.now().date() - datetime.timedelta(days=365),
                'description': 'Annual agreement for growing businesses with annual discounting.',
                'auto_close_on_end': False,
                'allow_close_early': True,
                'allow_pause': True,
                'allow_renewal': True
            }
        )

        plan_enterprise, _ = Plan.objects.get_or_create(
            code="high-volume-enterprise",
            defaults={
                'name': "High-Volume Enterprise",
                'cost': Decimal('2500.00'),
                'billing_interval': Plan.BillingInterval.MONTHLY,
                'min_quantity': 10,
                'available_from': timezone.now().date() - datetime.timedelta(days=120),
                'description': 'Enterprise tier with dedicated account rep and strict commitments.',
                'auto_close_on_end': False,
                'allow_close_early': False,
                'allow_pause': False,
                'allow_renewal': True
            }
        )

        plan_trial, _ = Plan.objects.get_or_create(
            code="trial-special",
            defaults={
                'name': "Trial Special (Weekly)",
                'cost': Decimal('49.00'),
                'billing_interval': Plan.BillingInterval.WEEKLY,
                'min_quantity': 1,
                'available_from': timezone.now().date() - datetime.timedelta(days=30),
                'description': 'Short-term trial plan that automatically closes on its own when finished.',
                'auto_close_on_end': True,
                'allow_close_early': False,
                'allow_pause': False,
                'allow_renewal': False
            }
        )

        # 5. Quotation Templates (Scene 3)
        tmpl_smb, _ = QuotationTemplate.objects.get_or_create(
            name="Standard SMB Onboarding Template",
            defaults={
                'plan': plan_monthly,
                'valid_days': 15,
                'notes': 'Pre-configured starter bundle for small business clients with Core ERP + Odoo Suite.'
            }
        )
        if not tmpl_smb.lines.exists():
            QuotationTemplateLine.objects.create(template=tmpl_smb, product=prod_erp, quantity=2, unit_price=Decimal('120.00'), tax_rule=tax_standard)
            QuotationTemplateLine.objects.create(template=tmpl_smb, product=prod_odoo_suite, quantity=1, unit_price=Decimal('85.00'), tax_rule=tax_standard)

        tmpl_enterprise, _ = QuotationTemplate.objects.get_or_create(
            name="Enterprise Multi-Seat Package",
            defaults={
                'plan': plan_yearly,
                'valid_days': 30,
                'notes': 'Complete yearly offer with 20 seats, dedicated Odoo-branded cloud hosting, and priority support.'
            }
        )
        if not tmpl_enterprise.lines.exists():
            QuotationTemplateLine.objects.create(template=tmpl_enterprise, product=prod_erp, quantity=20, unit_price=Decimal('120.00'), tax_rule=tax_standard)
            QuotationTemplateLine.objects.create(template=tmpl_enterprise, product=prod_hosting, variant=var_odoo_brand, quantity=1, unit_price=var_odoo_brand.total_price, tax_rule=tax_standard)
            QuotationTemplateLine.objects.create(template=tmpl_enterprise, product=prod_sla, quantity=1, unit_price=Decimal('99.00'), tax_rule=tax_standard)

        # 6. Discount Rules (Scene 5)
        disc_summer, _ = DiscountRule.objects.get_or_create(
            code="SUMMER20",
            defaults={
                'name': "Summer Growth Promo (20% Off)",
                'discount_type': DiscountRule.DiscountType.PERCENTAGE,
                'discount_value': Decimal('20.00'),
                'min_purchase_amount': Decimal('500.00'),
                'min_quantity': 0,
                'start_date': timezone.now().date() - datetime.timedelta(days=30),
                'end_date': timezone.now().date() + datetime.timedelta(days=60),
                'max_uses': 50,
                'current_uses': 4,
                'scope': DiscountRule.Scope.SUBSCRIPTION,
                'is_active': True
            }
        )

        disc_seat, _ = DiscountRule.objects.get_or_create(
            code="SEAT100",
            defaults={
                'name': "10+ Seats Volume Bonus ($100 Off)",
                'discount_type': DiscountRule.DiscountType.FIXED,
                'discount_value': Decimal('100.00'),
                'min_purchase_amount': Decimal('0.00'),
                'min_quantity': 10,
                'start_date': timezone.now().date() - datetime.timedelta(days=15),
                'end_date': timezone.now().date() + datetime.timedelta(days=45),
                'max_uses': 20,
                'current_uses': 1,
                'scope': DiscountRule.Scope.SUBSCRIPTION,
                'is_active': True
            }
        )

        # 7. Subscriptions across various lifecycle states (Scene 3)
        today = timezone.now().date()

        # SUB-1: Acme Corporation (Active, Enterprise Yearly)
        sub_acme, _ = Subscription.objects.get_or_create(
            subscription_number="SUB-2026-00001",
            defaults={
                'customer': cust_acme,
                'plan': plan_yearly,
                'status': Subscription.Status.ACTIVE,
                'start_date': today - datetime.timedelta(days=120),
                'expiry_date': today + datetime.timedelta(days=245),
                'payment_terms': 'net_30',
                'last_billed_date': today - datetime.timedelta(days=120),
                'next_billing_date': today + datetime.timedelta(days=245),
                'notes': 'Long term annual contract with 15 seats and Odoo Cloud infrastructure.'
            }
        )
        if not sub_acme.lines.exists():
            SubscriptionLine.objects.create(subscription=sub_acme, product=prod_erp, quantity=15, unit_price=Decimal('120.00'), tax_rule=tax_standard)
            SubscriptionLine.objects.create(subscription=sub_acme, product=prod_hosting, variant=var_odoo_brand, quantity=1, unit_price=var_odoo_brand.total_price, tax_rule=tax_standard)
            SubscriptionLine.objects.create(subscription=sub_acme, product=prod_sla, quantity=1, unit_price=Decimal('99.00'), tax_rule=tax_standard)

        # SUB-2: Corner Cafe (Active, Monthly Starter)
        sub_cafe, _ = Subscription.objects.get_or_create(
            subscription_number="SUB-2026-00002",
            defaults={
                'customer': cust_bistro,
                'plan': plan_monthly,
                'status': Subscription.Status.ACTIVE,
                'start_date': today - datetime.timedelta(days=45),
                'expiry_date': today + datetime.timedelta(days=320),
                'payment_terms': 'net_15',
                'last_billed_date': today - datetime.timedelta(days=15),
                'next_billing_date': today + datetime.timedelta(days=15),
                'notes': 'Corner Cafe 2-seat monthly subscription.'
            }
        )
        if not sub_cafe.lines.exists():
            SubscriptionLine.objects.create(subscription=sub_cafe, product=prod_erp, quantity=2, unit_price=Decimal('120.00'), tax_rule=tax_standard)
            SubscriptionLine.objects.create(subscription=sub_cafe, product=prod_odoo_suite, quantity=1, unit_price=Decimal('85.00'), tax_rule=tax_standard)

        # SUB-3: TechFlow Dynamics (Confirmed, awaiting activation)
        sub_techflow, _ = Subscription.objects.get_or_create(
            subscription_number="SUB-2026-00003",
            defaults={
                'customer': cust_techflow,
                'plan': plan_enterprise,
                'status': Subscription.Status.CONFIRMED,
                'start_date': today,
                'expiry_date': today + datetime.timedelta(days=365),
                'payment_terms': 'net_30',
                'next_billing_date': today,
                'notes': 'Confirmed quotation offer, ready for activation on Billing Day.'
            }
        )
        if not sub_techflow.lines.exists():
            SubscriptionLine.objects.create(subscription=sub_techflow, product=prod_erp, quantity=10, unit_price=Decimal('120.00'), tax_rule=tax_standard)
            SubscriptionLine.objects.create(subscription=sub_techflow, product=prod_analytics, quantity=2, unit_price=Decimal('150.00'), tax_rule=tax_standard)

        # SUB-4: Spark Labs (Active, Due for Billing Day batch run!)
        sub_spark, _ = Subscription.objects.get_or_create(
            subscription_number="SUB-2026-00004",
            defaults={
                'customer': cust_spark,
                'plan': plan_monthly,
                'status': Subscription.Status.ACTIVE,
                'start_date': today - datetime.timedelta(days=35),
                'expiry_date': today + datetime.timedelta(days=330),
                'payment_terms': 'net_30',
                'last_billed_date': today - datetime.timedelta(days=35),
                'next_billing_date': today, # DUE TODAY!
                'notes': 'Due for billing today to showcase automated batch billing engine.'
            }
        )
        if not sub_spark.lines.exists():
            SubscriptionLine.objects.create(subscription=sub_spark, product=prod_erp, quantity=3, unit_price=Decimal('120.00'), tax_rule=tax_standard)

        # 8. Invoices & Payments (Scenes 4, 6, 7)
        # Invoice 1: Acme Corp - Paid in full
        inv_acme, _ = Invoice.objects.get_or_create(
            invoice_number="INV-2026-00001",
            defaults={
                'subscription': sub_acme,
                'customer': cust_acme,
                'invoice_date': today - datetime.timedelta(days=120),
                'due_date': today - datetime.timedelta(days=90),
                'status': Invoice.Status.PAID,
                'billing_period_start': today - datetime.timedelta(days=120),
                'billing_period_end': today + datetime.timedelta(days=245),
                'discount_rule': disc_summer,
                'notes': 'Annual subscription renewal invoice with Summer Promo applied.'
            }
        )
        if not inv_acme.lines.exists():
            InvoiceLine.objects.create(invoice=inv_acme, product=prod_erp, description="Brightloop Core ERP (15 Seats)", quantity=15, unit_price=Decimal('120.00'), tax_rule=tax_standard)
            InvoiceLine.objects.create(invoice=inv_acme, product=prod_hosting, variant=var_odoo_brand, description="Dedicated Cloud Hosting (Brand: Odoo)", quantity=1, unit_price=var_odoo_brand.total_price, tax_rule=tax_standard)
            inv_acme.update_totals()

            Payment.objects.create(
                invoice=inv_acme,
                payment_date=today - datetime.timedelta(days=115),
                amount=inv_acme.total_amount,
                payment_method=Payment.PaymentMethod.BANK_TRANSFER,
                transaction_reference="WIRE-ACME-9912",
                note="Wire transfer settled in full",
                recorded_by=david_staff
            )

        # Invoice 2: Corner Cafe - Confirmed, Unpaid (Outstanding balance)
        inv_cafe, _ = Invoice.objects.get_or_create(
            invoice_number="INV-2026-00002",
            defaults={
                'subscription': sub_cafe,
                'customer': cust_bistro,
                'invoice_date': today - datetime.timedelta(days=10),
                'due_date': today + datetime.timedelta(days=5),
                'status': Invoice.Status.CONFIRMED,
                'billing_period_start': today - datetime.timedelta(days=10),
                'billing_period_end': today + datetime.timedelta(days=20),
                'notes': 'Monthly billing cycle. Due in 5 days.'
            }
        )
        if not inv_cafe.lines.exists():
            InvoiceLine.objects.create(invoice=inv_cafe, product=prod_erp, description="Brightloop Core ERP (2 Seats)", quantity=2, unit_price=Decimal('120.00'), tax_rule=tax_standard)
            InvoiceLine.objects.create(invoice=inv_cafe, product=prod_odoo_suite, description="Odoo Integration Suite", quantity=1, unit_price=Decimal('85.00'), tax_rule=tax_standard)
            inv_cafe.update_totals()

        # Invoice 3: Spark Labs - OVERDUE (Scene 6 & 7 chase scenario!)
        inv_spark_overdue, _ = Invoice.objects.get_or_create(
            invoice_number="INV-2026-00003",
            defaults={
                'subscription': sub_spark,
                'customer': cust_spark,
                'invoice_date': today - datetime.timedelta(days=45),
                'due_date': today - datetime.timedelta(days=15), # Overdue by 15 days!
                'status': Invoice.Status.CONFIRMED,
                'billing_period_start': today - datetime.timedelta(days=45),
                'billing_period_end': today - datetime.timedelta(days=15),
                'notes': 'Previous monthly cycle. OVERDUE - chase payment.'
            }
        )
        if not inv_spark_overdue.lines.exists():
            InvoiceLine.objects.create(invoice=inv_spark_overdue, product=prod_erp, description="Brightloop Core ERP (3 Seats)", quantity=3, unit_price=Decimal('120.00'), tax_rule=tax_standard)
            inv_spark_overdue.update_totals()

        self.stdout.write(self.style.SUCCESS("Brightloop Software database successfully seeded!"))
        self.stdout.write(self.style.SUCCESS("Sample Accounts Available:"))
        self.stdout.write("  - Admin:    admin@brightloop.com     (Password: Admin@12345)")
        self.stdout.write("  - Staff:    sarah@brightloop.com     (Password: Staff@12345)")
        self.stdout.write("  - Customer: acme@acmecorp.com        (Password: Acme@12345)")
        self.stdout.write("  - Customer: bistro@cornercafe.com    (Password: Corner@12345)")
        self.stdout.write("  - Customer: spark@sparklabs.com      (Password: Spark@12345)")
