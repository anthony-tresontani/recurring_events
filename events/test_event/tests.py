"""
This file demonstrates writing tests using the unittest module. These will pass
when you run "manage.py test".

Replace this with more appropriate tests for your application.
"""
from datetime import date
from hamcrest import *

from django.test import TestCase
from django_dynamic_fixture import get
from event.models import Event
from test_event.models import CustomEvent

class CustomEventTest(TestCase):

    def setUp(self):
        self.event = get(CustomEvent, title= "my title", date=date(2012, 3, 2), _parent=None)
        self.event.set_recurring(Event.MONTH)

    def test_recurring_custom_event(self):
        child_event = CustomEvent.objects.filter(date=date(2012, 4, 2))[0]
        assert_that(child_event.title, is_(self.event.title))

    def test_title_update(self):
        # Create the child event
        child_event_id = CustomEvent.objects.filter(date=date(2012, 4, 2))[0].id

        title = "A new title"
        self.event.title = title
        self.event.save(update_series=True)

        child_event = CustomEvent.objects.get(id=child_event_id)
        assert_that(child_event.title, is_(title))