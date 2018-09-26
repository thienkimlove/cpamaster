import time
from django.core.management.base import BaseCommand

from core.helpers import create_statistic_on_lead
from core.models import Lead


class Command(BaseCommand):
    help = 'Delete old logs'

    def handle(self, *args, **options):
        start_time = time.time()

        leads = Lead.objects.all()

        for lead in leads:
            # Store in statistic table.
            create_statistic_on_lead(lead)

        self.stdout.write(self.style.SUCCESS('Completed!'))
        end_time = time.time()
        self.stdout.write(self.style.SUCCESS('Successfully deleted old logs in "%s"' % (end_time - start_time)))
