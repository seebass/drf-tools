from django.db import models


class TestResource(models.Model):
    name = models.CharField(max_length=255)


class RelatedResource1(models.Model):
    name = models.CharField(max_length=255)
    active = models.BooleanField(default=True)
    resource = models.OneToOneField(TestResource)


class RelatedResource2(models.Model):
    name = models.CharField(max_length=255)
    active = models.BooleanField(default=True)
    related_resources_1 = models.ManyToManyField(RelatedResource1)
    resource = models.ForeignKey(TestResource)
