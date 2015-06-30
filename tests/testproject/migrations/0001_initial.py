# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import models, migrations


class Migration(migrations.Migration):

    dependencies = [
    ]

    operations = [
        migrations.CreateModel(
            name='RelatedResource1',
            fields=[
                ('id', models.AutoField(primary_key=True, verbose_name='ID', serialize=False, auto_created=True)),
                ('name', models.CharField(max_length=255)),
                ('active', models.BooleanField(default=True)),
            ],
        ),
        migrations.CreateModel(
            name='RelatedResource2',
            fields=[
                ('id', models.AutoField(primary_key=True, verbose_name='ID', serialize=False, auto_created=True)),
                ('name', models.CharField(max_length=255)),
                ('active', models.BooleanField(default=True)),
                ('related_resources_1', models.ManyToManyField(to='testproject.RelatedResource1')),
            ],
        ),
        migrations.CreateModel(
            name='TestResource',
            fields=[
                ('id', models.AutoField(primary_key=True, verbose_name='ID', serialize=False, auto_created=True)),
                ('name', models.CharField(max_length=255)),
            ],
        ),
        migrations.AddField(
            model_name='relatedresource2',
            name='resource',
            field=models.ForeignKey(to='testproject.TestResource'),
        ),
        migrations.AddField(
            model_name='relatedresource1',
            name='resource',
            field=models.OneToOneField(to='testproject.TestResource'),
        ),
    ]
