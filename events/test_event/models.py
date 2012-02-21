from django.db import models

# Create your models here.
from event.models import Event

class CustomEvent(Event):
    title = models.CharField(max_length=20)

    shared_attributes = ["title"]