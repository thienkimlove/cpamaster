import time

from django.db.models import Q
from gevent.pool import Pool
from django.core.management.base import BaseCommand
from django.core import management

from core.models import Virtual


def call_existed():
    management.call_command('basic', verbosity=0)


class Command(BaseCommand):
    help = 'Running virtual clicks'

    def handle(self, *args, **options):
        start_time = time.time()
        Virtual.objects.filter(Q(sent=None) & Q(process=None)).update(sent=False)
        count = Virtual.objects.filter(Q(sent=False) & Q(process=None)).count()
        i = count
        pool = Pool()
        while i > 100:
            pool.spawn(call_existed())
            i = i - 100
        pool.spawn(call_existed())
        pool.join()
        self.stdout.write(self.style.SUCCESS('Completed!'))

        end_time = time.time()
        self.stdout.write(self.style.SUCCESS('Successfully end clicks in "%s"' % (end_time - start_time)))
