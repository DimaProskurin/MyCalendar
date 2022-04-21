from django.urls import path

from core.views import create_views, info_views, update_views, timetable_views

urlpatterns = [
    # create views
    path("create/user", create_views.create_user),
    path("create/event", create_views.create_event),
    # info views
    path("info/event/<int:event_id>", info_views.info_event),
    path("info/user/<int:user_id>", info_views.info_user),
    path("info/invites", info_views.info_user_invites),
    path("info/user/<int:user_id>/events", info_views.info_user_events),
    # update views
    path("update/invite/<int:invite_id>", update_views.update_invite),
    # timetable views
    path("timetable/free_time_slot", timetable_views.get_first_free_time_slot),
]
