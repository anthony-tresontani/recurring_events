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

    def test_recurring_custom_event(self):
        event = get(CustomEvent, title= "my title", date=date(2012, 03, 02))
        event.set_recurring(Event.MONTH)

        child_event = CustomEvent.objects.filter(date=date(2012, 03, 02))[0]
        assert_that(child_event.title, is_(event.title))

