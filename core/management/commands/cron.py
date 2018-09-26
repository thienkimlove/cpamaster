import time
from django.core.management.base import BaseCommand

from core.helpers import *


class Command(BaseCommand):
    help = 'Run cron network every days'

    def add_arguments(self, parser):

        parser.add_argument(
            '--network_id', dest='network_id', required=True,
            help='the network id inside site',
        )

        parser.add_argument(
            '--routing', dest='routing', required=True,
            help='dynamic routing for each call',
        )

    def handle(self, *args, **options):
        start_time = time.time()
        routing = options['routing']
        rabbit_send('Start getting data from URL. Please wait...', routing)
        cron_network(options['network_id'], routing)
        rabbit_send('Completed!', routing)
        end_time = time.time()
        rabbit_send("Successfully in %s" % (end_time - start_time), routing)
