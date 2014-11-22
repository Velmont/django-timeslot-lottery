import datetime

from django.contrib.auth import get_user_model
from django.test import TestCase
from django.utils import timezone

from timeslot_lottery import views
from timeslot_lottery.models import Slot
from timeslot_lottery.models import Template
from timeslot_lottery.models import Week


User = get_user_model()


class TestBasics(TestCase):
    def test_template_create_new_week(self):
        tmpl = Template.objects.create(
            slug='test',
            slots={1:['10:00'], 2:['12:00', '12:15'], 7:['00:00'],
                   6: ['23:59', '10:00']})
        self.assertEqual(0, Week.objects.all().count())
        self.assertEqual(0, Slot.objects.all().count())
        week = tmpl.create_new_week((2010, 1))
        self.assertEqual(1, Week.objects.all().count())
        self.assertEqual(6, Slot.objects.all().count())

        self.assertEqual([unicode(s) for s in week.slots.all()],
                         ['Slot 2010-01-04 10:00:00',
                          'Slot 2010-01-05 12:00:00',
                          'Slot 2010-01-05 12:15:00',
                          'Slot 2010-01-09 10:00:00',
                          'Slot 2010-01-09 23:59:00',
                          'Slot 2010-01-10 00:00:00'])


class TestTemplate(TestCase):
    def test_dates(self):
        dt = datetime.datetime
        open_dt = dt(2014, 1, 7, 10, 0)
        self.assertEqual(open_dt.isoweekday(), 2)  # Tuesday
        close_dt = dt(2014, 1, 9, 11, 30)
        t = Template(title='', slug='',
                     auto_opening=open_dt, auto_closing=close_dt)

        # concrete_opening_time
        self.assertEqual(t.concrete_opening_time(2014, 3),
                         dt(2014, 1, 14, 10))
        self.assertEqual(t.concrete_opening_time(2014, 3).isoweekday(), 2)

        # concrete_closing_time
        self.assertEqual(t.concrete_closing_time(2014, 3),
                         dt(2014, 1, 16, 11, 30))
        self.assertEqual(t.concrete_closing_time(2014, 3).isoweekday(), 4)

    def test_far_ahead_dates(self):
        dt = datetime.datetime
        open_dt = dt(2010, 1, 7, 10, 0)
        self.assertEqual(open_dt.isoweekday(), 4) # Thursday
        close_dt = dt(2010, 1, 14, 8, 0)
        t = Template(title='', slug='',
                     auto_opening=open_dt, auto_closing=close_dt)

        # concrete_closing_time
        self.assertEqual(t.concrete_opening_time(2014, 3),
                         dt(2014, 1, 16, 10))
        self.assertEqual(t.concrete_opening_time(2014, 3).isoweekday(), 4)

        # concrete_closing_time
        self.assertEqual(t.concrete_closing_time(2014, 3),
                         dt(2014, 1, 23, 8))
        self.assertEqual(t.concrete_closing_time(2014, 3).isoweekday(), 4)


class TestCloseAndFillSlots(TestCase):
    def setUp(self):
        tmpl = Template.objects.create(
            slug='test',
            slots={1:['10:00'], 7:['00:00', '12:00']})
        self.week = tmpl.create_new_week((2010, 1))
        self.slots = self.week.slots.all()
        self.users = [
            User.objects.create(username='user_1'),
            User.objects.create(username='user_2'),
            User.objects.create(username='user_3'),
        ]

    def test_basic(self):
        s1, s2, s3 = self.slots
        u1, u2, u3 = self.users

        s1.bidders.add(u1, u2, u3)
        s2.bidders.add(u1, u2, u3)
        s3.bidders.add(u1, u2, u3)

        self.week.fill_slots()

        self.assertEqual(set([u1, u2, u3]),
                         set(s.winner for s in Slot.objects.all()))

    def test_with_restrictions(self):
        s1, s2, s3 = self.slots
        u1, u2, u3 = self.users

        s1.bidders.add(u2)
        s2.bidders.add(u1, u2, u3)
        s3.bidders.add(u1, u2)

        self.week.fill_slots()

        s1, s2, s3 = Slot.objects.all()
        self.assertEqual(u2, s1.winner)
        self.assertEqual(u3, s2.winner)
        self.assertEqual(u1, s3.winner)

    def test_one_too_many_bidders(self):
        s1, s2, s3 = self.slots
        u1, u2, u3 = self.users
        u4 = User.objects.create(username='test_4')

        s1.bidders.add(u1, u2, u3, u4)
        s2.bidders.add(u1, u2, u3, u4)
        s3.bidders.add(u1, u2, u3, u4)

        self.week.fill_slots()

        # One that didn't win
        self.assertEqual(
            1, len(set(self.users + [u4]) -
                   set(s.winner for s in Slot.objects.all())))

    def test_one_too_few_bidders(self):
        s1, s2, s3 = self.slots
        u1, u2, u3 = self.users

        s1.bidders.add(u1)
        s2.bidders.add(u1, u2)
        s3.bidders.add(u2)

        self.week.fill_slots()

        # The least-wanted slots gets filled first,
        # hence no one is taking Slot 2.
        s1, s2, s3 = Slot.objects.all()
        self.assertEqual(u1, s1.winner)
        self.assertEqual(None, s2.winner)
        self.assertEqual(u2, s3.winner)

    def test_slot_prioritization(self):
        s1, s2, s3 = self.slots
        u1, u2, u3 = self.users
        u4 = User.objects.create(username='test_4')
        u5 = User.objects.create(username='test_5')

        # Old week to let u1 and u3 have some earlier wins
        week2 = Week.objects.create(year=2000, week_no=1,
                                    template=self.week.template)
        Slot.objects.create(
            week=week2, time=timezone.now(), winner=u1)
        Slot.objects.create(
            week=week2, time=timezone.now(), winner=u1)
        Slot.objects.create(
            week=week2, time=timezone.now(), winner=u2)
        Slot.objects.create(
            week=week2, time=timezone.now(), winner=u2)
        Slot.objects.create(
            week=week2, time=timezone.now(), winner=u3)

        s1.bidders.add(u1, u2, u3, u4, u5) # u3 "wins"
        s2.bidders.add(u4, u2, u1, u3) # u4 wins
        s3.bidders.add(u1, u5, u2) # u5 wins

        self.week.fill_slots()

        s1, s2, s3 = self.week.slots.all()
        self.assertEqual(u3, s1.winner)
        self.assertEqual(u4, s2.winner)
        self.assertEqual(u5, s3.winner)

    def test_lower_pri_nonpicky_may_win(self):
        s1, s2, s3 = self.slots
        u1, u2, u3 = self.users
        u4_lowpri = User.objects.create(username='test_4')

        week2 = Week.objects.create(year=2000, week_no=1,
                                    template=self.week.template)
        Slot.objects.create(
            week=week2, time=timezone.now(), winner=u4_lowpri)
        Slot.objects.create(
            week=week2, time=timezone.now(), winner=u4_lowpri)
        Slot.objects.create(
            week=week2, time=timezone.now(), winner=u3)

        s1.bidders.add(u1, u3)
        s2.bidders.add(u1, u2, u4_lowpri)
        s3.bidders.add(u2, u3)

        self.week.fill_slots()

        # Even though u3 is higher pri, it didn't bid on the
        # free s2 spot, so u4 can have it.
        s1, s2, s3 = self.week.slots.all()
        self.assertEqual(u1, s1.winner)
        self.assertEqual(u4_lowpri, s2.winner)
        self.assertEqual(u2, s3.winner)


class TestEmail(TestCase):
    def setUp(self):
        tmpl = Template.objects.create(
            slug='test',
            slots={1:['10:00'], 7:['00:00', '12:00']})
        self.week = tmpl.create_new_week((2010, 1))
        self.slots = self.week.slots.all()
        self.users = [
            User.objects.create(username='user_1'),
        ]

    def test_winner_email_body(self):
        txt, html = views._create_winner_email_body(self.users[0],
                                                    self.slots[0])
        self.assertIn('You got slot ', txt)
