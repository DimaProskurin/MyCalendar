from django.contrib import admin
from core.models import User, Calendar, Event, CalendarPermission, RRule, Invite

# Register your models here.
admin.site.register(User)
admin.site.register(Calendar)
admin.site.register(Event)
admin.site.register(CalendarPermission)
admin.site.register(RRule)
admin.site.register(Invite)
