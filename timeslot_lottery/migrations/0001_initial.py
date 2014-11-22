# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import models, migrations
import model_utils.fields
import jsonfield.fields
import django.utils.timezone
from django.conf import settings


class Migration(migrations.Migration):

    dependencies = [
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
    ]

    operations = [
        migrations.CreateModel(
            name='Slot',
            fields=[
                ('id', models.AutoField(verbose_name='ID', serialize=False, auto_created=True, primary_key=True)),
                ('created', model_utils.fields.AutoCreatedField(default=django.utils.timezone.now, verbose_name='created', editable=False)),
                ('modified', model_utils.fields.AutoLastModifiedField(default=django.utils.timezone.now, verbose_name='modified', editable=False)),
                ('time', models.DateTimeField()),
                ('bidders', models.ManyToManyField(related_name='slots_bid_for', to=settings.AUTH_USER_MODEL)),
            ],
            options={
                'ordering': ('time',),
            },
            bases=(models.Model,),
        ),
        migrations.CreateModel(
            name='Template',
            fields=[
                ('id', models.AutoField(verbose_name='ID', serialize=False, auto_created=True, primary_key=True)),
                ('created', model_utils.fields.AutoCreatedField(default=django.utils.timezone.now, verbose_name='created', editable=False)),
                ('modified', model_utils.fields.AutoLastModifiedField(default=django.utils.timezone.now, verbose_name='modified', editable=False)),
                ('title', models.CharField(max_length=32)),
                ('slug', models.SlugField()),
                ('slots', jsonfield.fields.JSONField(default={1: [], 2: [], 3: [], 4: [], 5: [], 6: [], 7: []}, help_text=b'1=Monday, 7=Sunday. For two slots thursday, you could write: {4: ["09:00", "17:30"]}')),
                ('auto_opening', models.DateTimeField(help_text=b"Not used as a fixed date.  Only the day and time are considered.  It's always put in the corresponding week.", null=True, blank=True)),
                ('auto_closing', models.DateTimeField(help_text=b'Not used as a fixed date.  Only the relative time back to the auto opening time is considered.', null=True, blank=True)),
            ],
            options={
                'abstract': False,
            },
            bases=(models.Model,),
        ),
        migrations.CreateModel(
            name='Week',
            fields=[
                ('id', models.AutoField(verbose_name='ID', serialize=False, auto_created=True, primary_key=True)),
                ('created', model_utils.fields.AutoCreatedField(default=django.utils.timezone.now, verbose_name='created', editable=False)),
                ('modified', model_utils.fields.AutoLastModifiedField(default=django.utils.timezone.now, verbose_name='modified', editable=False)),
                ('year', models.PositiveSmallIntegerField()),
                ('week_no', models.PositiveSmallIntegerField()),
                ('status', models.CharField(default=b'new', max_length=32, choices=[(b'new', b'new'), (b'active', b'active'), (b'closed', b'closed')])),
                ('auto_close_from', models.DateTimeField(null=True, blank=True)),
                ('template', models.ForeignKey(related_name='weeks', to='timeslot_lottery.Template')),
            ],
            options={
            },
            bases=(models.Model,),
        ),
        migrations.AlterUniqueTogether(
            name='week',
            unique_together=set([('year', 'week_no', 'template')]),
        ),
        migrations.AddField(
            model_name='slot',
            name='week',
            field=models.ForeignKey(related_name='slots', to='timeslot_lottery.Week'),
            preserve_default=True,
        ),
        migrations.AddField(
            model_name='slot',
            name='winner',
            field=models.ForeignKey(related_name='slots_won', blank=True, to=settings.AUTH_USER_MODEL, null=True),
            preserve_default=True,
        ),
    ]
