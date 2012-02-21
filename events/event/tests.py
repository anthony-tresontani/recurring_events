from datetime import datetime, date
from unittest.case import TestCase
from django_dynamic_fixture import get
from hamcrest import *
from event.models import EventManager
from models import Event

class TestEvent(TestCase):

    def setUp(self):
        self.event = get(Event, date=date(2012, 03, 02), _parent=None, persist_dependencies=False)
        assert_that(self.event._parent, is_(none()))

    def tearDown(self):
        Event.objects.all().delete()

    def test_event_are_searcheable(self):
        assert_that(Event.objects.filter_for_month(2012, 03).count(), is_(1))

    def test_non_recurrent_event_next(self):
        assert_that(self.event.next(), is_(none()))

    def test_month_recurrent_event(self):
        self.event.set_recurrent(Event.MONTH)

        event = Event.objects.get(id=self.event.id)
        assert_that(event.is_recurring)
        assert_that(event.periodicity, is_("months"))

        next_event = event.next()
        assert_that(next_event.date, is_(date(2012, 4, 2)))
        assert_that(next_event.is_recurring)

    def test_year_recurrent_event(self):
        self.event.set_recurrent(Event.YEAR)

        event = Event.objects.get(id=self.event.id)
        next_event = event.next()
        assert_that(next_event.date, is_(date(2013, 03, 2)))

    def test_get_root_event(self):
        self.event.set_recurrent(Event.YEAR)
        next = self.event.next()
        assert_that(Event.objects.count(), 2)
        assert_that(Event.objects.get_root_events().count(), is_(1))

    def test_is_occuring(self):
        self.event.set_recurrent(Event.WEEK)

        event = Event.objects.get(id=self.event.id)
        assert_that(event.is_occuring(date=date(2012, 03, 2)))

        assert_that(event.is_occuring(date_from=date(2012, 03, 8), date_to=date(2012, 03, 10)))
        assert_that(event.is_occuring(date_from=date(2012, 03, 8), date_to=date(2012, 03, 10)))

        #TODO add a test if two values in an interval an initial date is higher than the period upper limit

    def test_on_the_fly_event_generation_for_a_fixed_date(self):
        self.event.set_recurrent(Event.MONTH)

        # 12 months after, there should be an event
        assert_that(Event.objects.filter(date=date(2013, 3, 2)).count(), is_(1))

    def test_get_date_boundaries(self):
        assert_that(EventManager.get_date_boundaries(date=date(2013, 3, 2)), equal_to((date(2013, 3, 2), date(2013, 3, 2))))
        assert_that(EventManager.get_date_boundaries(date__lte=date(2013, 3, 2)), equal_to((None, date(2013, 3, 2))))
        assert_that(EventManager.get_date_boundaries(date__lt=date(2013, 3, 2)), equal_to((None, date(2013, 3, 1))))
        assert_that(EventManager.get_date_boundaries(date__gt=date(2013, 3, 2)), equal_to((date(2013, 3, 3), None)))
        assert_that(EventManager.get_date_boundaries(date__gte=date(2013, 3, 2)), equal_to((date(2013, 3, 2), None)))

    def test_get_date_args(self):
        assert_that(EventManager.get_date_kwargs(**{"date":1, "date_lte":2, "nodate":None}), is_({"date":1, "date_lte":2}))

    def test_on_the_fly_event_generation_for_a_upper_limit_in_time(self):
        self.event.set_recurrent(Event.MONTH)
        assert_that(Event.objects.filter(date__lte=date(2013, 03, 01)).count(), is_(12))
        assert_that(Event.objects.filter(date__lte=date(2013, 03, 01)).count(), is_(12))
        assert_that(Event.objects.filter(date__gt=date(2013, 03, 01)).count(), is_(12))

    def test_delete_event(self):
        self.event.set_recurrent(Event.MONTH)
        first_child = self.event.create_child_event(date(2013, 3, 2))
        second_child = self.event.create_child_event(date(2013, 3, 3))
        self.event.delete()

        first_child = Event.objects.get(id=first_child.id)
        assert_that(first_child._parent, is_(none()))

        second_child = Event.objects.get(id=second_child.id)
        assert_that(second_child._parent, is_(first_child))

