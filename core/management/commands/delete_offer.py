import time
from django.core.management.base import BaseCommand

from core.models import Offer


class Command(BaseCommand):
    help = 'Delete old logs'

    def handle(self, *args, **options):
        start_time = time.time()
        offers = Offer.objects.raw("SELECT t1.id from core_offer t1 left join core_statistic t2 on t1.id = t2.offer_id where t1.created_at <  CURRENT_DATE - INTERVAL '3 days' and t2.id is null")
        for offer in offers:
            offer.delete()
        self.stdout.write(self.style.SUCCESS('Completed!'))
        end_time = time.time()
        self.stdout.write(self.style.SUCCESS('Successfully deleted old logs in "%s"' % (end_time - start_time)))
