from django.conf.urls import patterns
from django.conf.urls import url


urlpatterns = patterns('timeslot_lottery.views',
    url(r'^$', 'home', name='home'),
    url(r'^(?P<template_slug>[\w-]+)/$',
        'template_detail', name='template_detail'),
    url(r'^(?P<template_slug>[\w-]+)/(?P<year>\d{4})-(?P<week_no>\d{2})/$',
        'week_detail', name='week_detail'),
)
