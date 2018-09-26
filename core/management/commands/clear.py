import time
from django.core.management.base import BaseCommand
from core.models import Virtual


class Command(BaseCommand):
    help = 'Delete old logs'

    def handle(self, *args, **options):
        start_time = time.time()
        Virtual.objects.filter(sent=True).delete()
        self.stdout.write(self.style.SUCCESS('Completed!'))
        end_time = time.time()
        self.stdout.write(self.style.SUCCESS('Successfully deleted old logs in "%s"' % (end_time - start_time)))
