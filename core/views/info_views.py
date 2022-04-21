from django.http import HttpResponseBadRequest, JsonResponse
from django.utils.dateparse import parse_datetime
from django.utils.timezone import make_aware

from core.models import Event, Invite, User

JSON_DUMPS_PARAMS = {"indent": 3}


def exist_user(user_id):
    user_query = User.objects.filter(id=user_id)
    if len(user_query) == 0:
        return None, HttpResponseBadRequest(f"No user with such id = {user_id}")
    return user_query[0], None


def exist_event(event_id):
    event_query = Event.objects.filter(id=event_id)
    if len(event_query) == 0:
        return None, HttpResponseBadRequest(f"No event with such id = {event_id}")
    return event_query[0], None


def info_event(request, event_id):
    event, err = exist_event(event_id)
    if err:
        return err

    related_user_ids = event.get_related_user_ids()
    if not event.is_private or request.user.id in related_user_ids:
        return JsonResponse(
            event.deep_description(), json_dumps_params=JSON_DUMPS_PARAMS
        )
    else:
        return JsonResponse(
            event.hidden_description(), json_dumps_params=JSON_DUMPS_PARAMS
        )


def info_user(request, user_id):
    user, err = exist_user(user_id)
    if err:
        return err
    return JsonResponse({"user": str(user)}, json_dumps_params=JSON_DUMPS_PARAMS)


def info_user_invites(request):
    if not request.user.is_authenticated:
        return HttpResponseBadRequest("You are not logged in to lookup your invites")

    invite_status = request.GET.get("status")
    if invite_status is not None:
        if invite_status not in Invite.Status.names:
            return HttpResponseBadRequest(f"Status {invite_status} is not valid")
        user = User.objects.get(id=request.user.id)
        invites = user.get_invites_by_status(status=Invite.Status[invite_status])
    else:
        user = User.objects.get(id=request.user.id)
        invites = user.get_all_invites()
    return JsonResponse(
        {"invites": [str(invite) for invite in invites]},
        json_dumps_params=JSON_DUMPS_PARAMS,
    )


def info_user_events(request, user_id):
    from_time = request.GET.get("from")
    till_time = request.GET.get("till")
    if from_time is None or till_time is None:
        return HttpResponseBadRequest("from and till params should be provided")

    try:
        from_time = parse_datetime(from_time)
        till_time = parse_datetime(till_time)
        if from_time is None or till_time is None:
            return HttpResponseBadRequest("from and till params are not valid")
        from_time = make_aware(from_time)
        till_time = make_aware(till_time)
    except ValueError as e:
        return HttpResponseBadRequest(f"Input params is not valid because {e}")

    user, err = exist_user(user_id)
    if err:
        return err

    events_instances = user.get_events_instances_by_time_period(from_time, till_time)
    event2related_user_ids = {}
    for _, event in events_instances:
        if event not in event2related_user_ids:
            event2related_user_ids[event] = event.get_related_user_ids()

    # sort events by start
    events_instances = sorted(events_instances, key=lambda it: it[0][0])
    pretty_events = []
    for (start, end), event in events_instances:
        if event.is_private and request.user.id not in event2related_user_ids[event]:
            pretty_events.append(
                f"Start={start}, End={end}, Title=(PRIVATE)"
            )  # like hidden format
        else:
            pretty_events.append(f"Start={start}, End={end}, Title={str(event)}")

    return JsonResponse({"events": pretty_events}, json_dumps_params=JSON_DUMPS_PARAMS)
