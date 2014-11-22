# -*- coding: utf-8 -*-
import sys

from django.core.management.base import BaseCommand

from timeslot_lottery.models import Week


class Command(BaseCommand):
    help = "Close and calculate winners for pending weeks"

    def handle(self, *args, **options):
        results = Week.objects.close_pending()

        if results:
            sys.stdout.write("{:10s} {:6s} {:6s}"
                             .format("week", "wins", "left_bids"))
        for week, close_result in results.items():
            msg = u"{:10s}: {:6d} {:6d}".format(
                week,
                len(close_result['updated_slots']),
                len(close_result['remaining_bidders']))
            sys.stdout.write(msg.encode('utf-8'))
