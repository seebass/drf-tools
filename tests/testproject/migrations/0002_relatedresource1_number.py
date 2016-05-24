# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import models, migrations
from decimal import Decimal


class Migration(migrations.Migration):

    dependencies = [
        ('testproject', '0001_initial'),
    ]

    operations = [
        migrations.AddField(
            model_name='relatedresource1',
            name='number',
            field=models.DecimalField(decimal_places=2, max_digits=10, default=Decimal('2.00')),
        ),
    ]
