import copy
from dateutil.relativedelta import relativedelta
from django.utils.translation import ugettext_lazy as _
from django.db import models

MAX_NB_YEAR = 1

class EventManager(models.Manager):

    def filter_for_month(self, year, month):
        return self.filter(date__year=year, date__month=month)

    @classmethod
    def get_date_boundaries(cls, **kwargs):
        if "date" in kwargs:
            date = kwargs["date"]
            return (date, date)
        elif "date__lte" in kwargs:
            date = kwargs["date__lte"]
            return (None, date)
        elif "date__lt" in kwargs:
            date = kwargs["date__lt"]
            return (None, date - relativedelta(days=1))
        elif "date__gte" in kwargs:
            date = kwargs["date__gte"]
            return (date, None)
        elif "date__gt" in kwargs:
            date = kwargs["date__gt"]
            return (date + relativedelta(days=1), None)

    @classmethod
    def get_date_kwargs(cls, **kwargs):
        return dict((key, value) for (key, value) in kwargs.items() if key.startswith("date"))

    def filter(self, *args, **kwargs):
        date_range = self.get_date_boundaries(**kwargs)
        if date_range:
            for root_event in self.get_root_events():
                if root_event.is_occuring(date_from=date_range[0], date_to=date_range[1]):
                    # Event doesn't exist already
                    date = root_event.first_date_in_period(date_from=date_range[0], date_to=date_range[1])
                    if root_event.date == date:
                        # first event is the root one
                        event = root_event
                    else:
                        first_event = root_event._children._filter(date=date)
                        if not len(first_event):
                            event = root_event.create_child_event(date)
                        else:
                            event = first_event[0]
                    if not date_range[1]:
                        date_range = (date_range[0], date + relativedelta(years=MAX_NB_YEAR))
                    while event.get_next_date() < date_range[1]:
                        next_event_qs = root_event._children._filter(date=event.get_next_date())
                        if not next_event_qs.count():
                            event = event.next()
                        else:
                            event = next_event_qs[0]
        return self._filter(*args, **kwargs)

    def _filter(self, *args, **kwargs):
        return super(EventManager, self).filter(*args, **kwargs)

    def get_root_events(self):
        return self._filter(is_recurring=True, _parent=None)

class Event(models.Model):
    WEEK, MONTH, YEAR = "weeks","months", "years"

    date = models.DateField(_("Event date"))
    is_recurring = models.BooleanField(default=False)
    _periodicity = models.CharField(max_length=20)
    _parent = models.ForeignKey("self", null=True)
    _children = models.ManyToManyField("self")

    objects = EventManager()

    shared_attributes = []

    def set_recurring(self, periodicity):
        self.is_recurring = True
        self._periodicity = periodicity
        self.save()

    @property
    def periodicity(self):
        return self._periodicity

    def add_child(self, event):
        if not self._parent:
            self._children.add(event)
        else:
            self._parent.add_child(event)

    @classmethod
    def duplicate(cls, event, next_date):
        new_event = copy.copy(event)
        new_event.id = None
        new_event._parent = event
        new_event.date = next_date
        new_event.save()
        return new_event

    def create_child_event(self, next_date):
        event = self.duplicate(self, next_date)
        self.add_child(event)
        return event

    def get_next_date(self):
        return self.date + relativedelta(**{self._periodicity: 1})

    def _next(self):
        next_date = self.get_next_date()
        event = self.create_child_event(next_date)
        return event

    def next(self):
        if self.is_recurring:
            return self._next()
        return None

    def save(self, force_insert=False, force_update=False, using=None, update_series=False):
        if update_series:
            root = self._parent or self
            for child in root._children._filter(date__gte=self.date):
                for attribute in self.shared_attributes:
                    setattr(child, attribute, getattr(self, attribute))
                    child.save()
        super(Event, self).save(force_insert, force_update, using)


    def delete(self, using=None, all=False):
        """
        When deleting a recurring event, if the event is the root one,
        the first child become the root
        """
        children = self._children.all().order_by("date")
        if all:
            children.delete()
        if len(children):
            first_children = children[0]
            first_children._parent = None
            first_children.save()
            for child in children[1:]:
                child._parent = first_children
                child.save()
                first_children.add_child(child)
        super(Event, self).delete(using)

    @classmethod
    def is_include(cls, date, date_from, date_to):
        return date >= date_from and date <= date_to

    def is_occuring(self, date=None, date_from=None, date_to=None):
        return self.first_date_in_period(date, date_from, date_to) != None

    def first_date_in_period(self, date=None, date_from=None, date_to=None):
        if date:
            date_from, date_to = date, date
        else:
            if not date_from:
                date_from = self.date
            if not date_to:
                date_to = date_from + relativedelta(years=MAX_NB_YEAR)
            assert date_from <= date_to

        result = self.is_include(self.date, date_from, date_to)
        if result:
            return self.date
        elif not self.is_recurring:
            return None
        else:
            if self.date < date_from:
                date = self.date
                while date < date_from:
                    date = date + relativedelta(**{self._periodicity:1})
                if self.is_include(date, date_from, date_to):
                    return date
                else:
                    return None

            if self.date > date_to:
                date = self.date
                while date > date_from:
                    previous_date = date
                    date = date - relativedelta(**{self._periodicity:1})
                if self.is_include(previous_date, date_from, date_to):
                    return previous_date
                else:
                    return None

    class Meta:
        abstract = True

class BaseEvent(Event):pass


