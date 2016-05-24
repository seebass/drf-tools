from decimal import Decimal

from django.db import models


class TestResource(models.Model):
    name = models.CharField(max_length=255)


class RelatedResource1(models.Model):
    name = models.CharField(max_length=255)
    active = models.BooleanField(default=True)
    number = models.DecimalField(max_digits=10, decimal_places=2, default=Decimal('2.00'))
    resource = models.OneToOneField(TestResource)


class RelatedResource2(models.Model):
    name = models.CharField(max_length=255)
    active = models.BooleanField(default=True)
    related_resources_1 = models.ManyToManyField(RelatedResource1)
    resource = models.ForeignKey(TestResource)
