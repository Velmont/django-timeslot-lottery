from django.contrib import admin

from timeslot_lottery import models


admin.site.register(models.Slot)
admin.site.register(models.Template)
admin.site.register(models.Week)
