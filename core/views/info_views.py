from django.http import HttpResponseBadRequest, JsonResponse
from django.utils.dateparse import parse_datetime
from django.utils.timezone import make_aware

from core.models import Event, Invite, User


def info_event(request, id):
    event_query = Event.objects.filter(id=id)
    if len(event_query) == 0:
        return HttpResponseBadRequest(f"No event with such id {id}")
    event = event_query[0]
    return JsonResponse(event.deep_description(), json_dumps_params={"indent": 3})


def info_user(request, id):
    user_query = User.objects.filter(id=id)
    if len(user_query) == 0:
        return HttpResponseBadRequest(f"No user with such id = {id}")
    user = user_query[0]
    return JsonResponse({"user": str(user)}, json_dumps_params={"indent": 3})


def info_user_invites(request, userid):
    user_query = User.objects.filter(id=userid)
    if len(user_query) == 0:
        return HttpResponseBadRequest(f"No user with such id = {userid}")
    user = user_query[0]

    invite_status = request.GET.get("status")
    if invite_status is not None:
        if invite_status not in Invite.Status.names:
            return HttpResponseBadRequest(f"Status {invite_status} is not valid")
        invites = user.get_invites_by_status(status=Invite.Status[invite_status])
    else:
        invites = user.get_all_invites()
    return JsonResponse(
        {"invites": [str(invite) for invite in invites]},
        json_dumps_params={"indent": 3}
    )


def info_user_events(request, userid):
    user_query = User.objects.filter(id=userid)
    if len(user_query) == 0:
        return HttpResponseBadRequest(f"No user with such id = {userid}")
    user = user_query[0]

    from_time = request.GET.get("from")
    till_time = request.GET.get("till")
    if from_time is None or till_time is None:
        return HttpResponseBadRequest("from and till params should be provided")

    from_time = parse_datetime(from_time)
    till_time = parse_datetime(till_time)
    if from_time is None or till_time is None:
        return HttpResponseBadRequest("from and till params are not valid")
    from_time = make_aware(from_time)
    till_time = make_aware(till_time)

    events = user.get_events_instances_by_time_period(from_time, till_time)
    # sort events by start
    events = sorted(events, key=lambda it: it[0][0])
    pretty_events = []
    for (start, end), event in events:
        pretty_events.append(
            f"Start={start}, End={end}, Title={str(event)}"
        )

    return JsonResponse({"events": pretty_events}, json_dumps_params={"indent": 3})
