import collections
import datetime
import logging
import random

from django.conf import settings
from django.contrib.auth import get_user_model
from django.db import models
from django.db import transaction
from django.utils import timezone

from jsonfield import JSONField
from model_utils import Choices
from model_utils.models import TimeStampedModel

from timeslot_lottery.utils import iso_to_gregorian


logger = logging.getLogger(__name__)


class Template(TimeStampedModel):
    """
    Template for creating the weekly slots

    Fields:
      slug   The name of the template.
      slots  A dict with days 1 (monday) to 7 (sunday) as keys.
             Every day has a list of times as a string with hour
             and minute separated by a colon.
             E.g. {1: ['10:30', '16:00']}
    """
    title = models.CharField(max_length=32)
    slug = models.SlugField()

    slots = JSONField(
        default={1: [], 2: [], 3: [], 4: [], 5: [], 6: [], 7: []},
        help_text="""1=Monday, 7=Sunday. For two slots thursday, """
                  """you could write: {4: ["09:00", "17:30"]}""")
    auto_opening = models.DateTimeField(
        blank=True, null=True,
        help_text="""Not used as a fixed date.  Only the day and time """
                  """are considered.  It's always put in the """
                  """corresponding week.""")
    auto_closing = models.DateTimeField(
        blank=True, null=True,
        help_text="""Not used as a fixed date.  Only the relative """
                  """time back to the auto opening time is considered.""")

    def __unicode__(self):
        return "{}".format(self.title)

    def concrete_opening_time(self, year, week):
        isoday = self.auto_opening.isoweekday()
        date = iso_to_gregorian(year, week, isoday)
        return datetime.datetime.combine(date, self.auto_opening.time())

    def concrete_closing_time(self, year, week):
        close_delta = self.auto_closing - self.auto_opening
        return self.concrete_opening_time(year, week) + close_delta

    def current_week(self, year_week_tuple=None):
        if not year_week_tuple:
            year_week_tuple = timezone.now().isocalendar()[:2]
        year, week_no = year_week_tuple
        try:
            return self.weeks.get(year=year, week_no=week_no)
        except Week.DoesNotExist:
            return None

    def create_current_week(self):
        """
        Create 'week' for today if it doesn't already exist
        """
        now = timezone.now()
        year, week = now.isocalendar()[:2]
        if self.concrete_opening_time(year, week) > now:
            # Opening time is in the future, let's wait with creation
            return False
        if self.weeks.filter(year=year, week_no=week).exists():
            # Week already exists
            return False

        self.create_new_week((year, week))
        return True

    def create_new_week(self, year_week_tuple=None):
        if not year_week_tuple:
            year_week_tuple = timezone.now().isocalendar()[:2]
        year, week_no = year_week_tuple
        week_start = iso_to_gregorian(year, week_no, 1)
        week = Week.objects.create(year=year, week_no=week_no, template=self)
        if self.auto_opening and self.auto_closing:
            week.auto_close_from = self.concrete_closing_time(year, week)
        for day, times in self.slots.items():
            for time in times:
                hour, minute = map(int, time.split(':'))
                slot_date = week_start.replace(day=week_start.day + (day-1))
                slot_time = datetime.time(hour, minute)
                slot_datetime = datetime.datetime.combine(slot_date, slot_time)
                Slot.objects.create(week=week, time=slot_datetime)
        return week


class WeekManager(models.Manager):
    def close_pending(self):
        """
        Close and calculate winners for pending weeks

        Returns:
          A dict mapping between the week-object and a
          dict with the results of the week close.
        """
        now = timezone.now()
        to_close = (self.filter(auto_close_from__lte=now)
                    .exclude(status=Week.STATUS.closed))
        week_to_close_result = {}
        for week in to_close:
            updated_slots, remaining_bidders = week.close()
            week_to_close_result[week] = {
                'updated_slots': updated_slots,
                'remaining_bidders': remaining_bidders,
            }
        return week_to_close_result


class Week(TimeStampedModel):
    STATUS = Choices('new', 'active', 'closed')

    year = models.PositiveSmallIntegerField()
    week_no = models.PositiveSmallIntegerField()
    template = models.ForeignKey(Template, related_name='weeks')
    status = models.CharField(max_length=32, choices=STATUS,
                              default=STATUS.new)

    auto_close_from = models.DateTimeField(blank=True, null=True)

    objects = WeekManager()

    class Meta:
        unique_together = ('year', 'week_no', 'template')

    def __unicode__(self):
        return "{}-{}".format(self.year, self.week_no)

    def fill_slots(self):
        open_slots = (self.slots
                      .annotate(num_bids=models.Count('bidders'))
                      .filter(winner__isnull=True)
                      .order_by('num_bids'))
        bidders = (get_user_model().objects
                   .annotate(num_wins=models.Count('slots_won'))
                   .filter(slots_bid_for__week=self))
        ordered_bidders = self._bidders_in_pick_order(bidders)
        remaining_slots = list(open_slots)
        newly_won_slots = []
        # Fill first-come first-served
        for bidder in ordered_bidders:
            for slot in remaining_slots:
                if bidder in slot.bidders.all():
                    slot.winner = bidder
                    newly_won_slots.append(slot)
                    remaining_slots.remove(slot)
                    break
            if not remaining_slots:
                break
        remaining_bidders = ordered_bidders[ordered_bidders.index(bidder):]
        with transaction.atomic():
            for slot in newly_won_slots:
                slot.save()
        return newly_won_slots, remaining_bidders

    def close(self):
        now = timezone.now()
        if self.auto_close_from and now < self.auto_close_from:
            logger.warning(
                "Closing week {s} before closing time {s.close_from}."
                .format(s=self))
            self.auto_close_from = now
        if self.status == self.STATUS.closed:
            logger.info(
                "Closing week {s} which has already been closed."
                .format(s=self))
        self.status = self.STATUS.closed
        return self.fill_slots()

    def _bidders_in_pick_order(self, bidders):
        ordered_bidders = []
        bidders_by_wins = collections.defaultdict(list)
        # Group by number of wins
        for bidder in bidders:
            bidders_by_wins[bidder.num_wins].append(bidder)
        for key in sorted(bidders_by_wins.keys()):
            # Shuffle persons internally in each group
            random.shuffle(bidders_by_wins[key])
            # Build a full list of all bidders
            ordered_bidders.extend(bidders_by_wins[key])
        return ordered_bidders


class Slot(TimeStampedModel):
    week = models.ForeignKey(Week, related_name='slots')
    time = models.DateTimeField()

    winner = models.ForeignKey(settings.AUTH_USER_MODEL, blank=True, null=True,
                               related_name='slots_won')
    bidders = models.ManyToManyField(settings.AUTH_USER_MODEL,
                                     related_name='slots_bid_for')

    class Meta:
        ordering = ('time',)

    def __unicode__(self):
        return "Slot {}".format(self.time)
