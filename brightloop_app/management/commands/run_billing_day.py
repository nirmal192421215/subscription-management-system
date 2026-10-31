import datetime
from django.core.management.base import BaseCommand
from django.utils import timezone
from brightloop_app.services.billing_engine import BillingEngine

class Command(BaseCommand):
    help = "Run automated billing day cycle for all active subscriptions"

    def add_arguments(self, parser):
        parser.add_argument(
            '--date',
            type=str,
            help='Target billing date in YYYY-MM-DD format (defaults to today)',
            default=None
        )

    def handle(self, *args, **options):
        date_str = options.get('date')
        target_date = datetime.date.fromisoformat(date_str) if date_str else timezone.now().date()

        self.stdout.write(self.style.NOTICE(f"Running Brightloop Billing Day for {target_date}..."))
        results = BillingEngine.run_billing_day(target_date=target_date)

        self.stdout.write(self.style.SUCCESS(f"Generated {results['generated_count']} invoices."))
        self.stdout.write(self.style.WARNING(f"Auto-closed {results['auto_closed_count']} expired subscriptions."))
        self.stdout.write(f"Skipped / already billed: {results['skipped_count']} subscriptions.")

        for msg in results['messages']:
            self.stdout.write(f" - {msg}")

