import json

from django.core.exceptions import ValidationError
from django.core.validators import validate_email
from django.http import HttpResponse, HttpResponseBadRequest, JsonResponse
from django.utils.dateparse import parse_datetime
from django.views.decorators.csrf import csrf_exempt

from core.models import Event, Invite, RRule, User


@csrf_exempt
def create_user(request):
    if request.method != "POST":
        return HttpResponseBadRequest("The HTTP request should be POST type")

    body_data = json.loads(request.body)
    # required parameters
    try:
        name = body_data["name"]
        email = body_data["email"]
    except KeyError as e:
        return HttpResponseBadRequest(f"Your POST query has no key {e}")

    # validate email
    try:
        validate_email(email)
    except ValidationError:
        return HttpResponseBadRequest(f"Your email {email} is not valid")

    # check if such user exists
    if len(User.objects.filter(email=email)) > 0:
        return HttpResponseBadRequest("User with such email already exists")

    # create and save user
    user = User(name=name, email=email)
    user.save()
    return HttpResponse(f"{user} has been created")


@csrf_exempt
def create_event(request):
    if request.method != "POST":
        return HttpResponseBadRequest("The HTTP request should be POST type")

    body_data = json.loads(request.body)
    # required fields
    try:
        title = body_data["title"]
        start = parse_datetime(body_data["start"])
        end = parse_datetime(body_data["end"])
        owner_email = body_data["owner_email"]
    except KeyError as e:
        return HttpResponseBadRequest(f"Your POST query has no key {e}")

    # validate start & end
    if start is None or end is None:
        return HttpResponseBadRequest(f"Your {body_data['start']} and {body_data['end']} aren't valid format")
    if start > end:
        return HttpResponseBadRequest("End date should be greater than start date")

    # validate email
    try:
        validate_email(owner_email)
    except ValidationError:
        return HttpResponseBadRequest(f"Owner email {owner_email} is not valid")

    # optional fields
    description = body_data.get("description") or ""
    is_private = bool(body_data.get("is_private") or False)
    is_recurring = bool(body_data.get("is_recurring") or False)
    invited_emails = body_data.get("invited_emails") or []

    # create event
    owner_query = User.objects.filter(email=owner_email)
    if len(owner_query) == 0:
        return HttpResponseBadRequest(f"No user with such email {owner_email}")
    owner = owner_query[0]
    event = Event(
        title=title,
        description=description,
        start=start,
        end=end,
        owner_id=owner.id,
        is_recurring=is_recurring,
        is_private=is_private,
    )
    event.save()

    # create repeats
    if is_recurring:
        if (repeats := body_data.get("repeats")) is None:
            return HttpResponseBadRequest("Event is recurring but no repeats provided")
        default_rrules = {
            "daily": RRule.daily(event.id, event.start),
            "weekly": RRule.weekly(event.id, event.start),
            "monthly": RRule.monthly(event.id, event.start),
            "yearly": RRule.yearly(event.id, event.start),
        }
        for repeat in repeats:
            if repeat not in default_rrules:
                return HttpResponseBadRequest(f"Repeat value {repeat} is not valid. Valid is {default_rrules.keys()}")
        for repeat in repeats:
            default_rrules[repeat].save()

    # create invites
    invited_users = User.objects.filter(email__in=invited_emails)
    for invited_user in invited_users:
        Invite(
            user_id=invited_user.id,
            event_id=event.id,
        ).save()

    return JsonResponse(event.deep_description(), json_dumps_params={"indent": 3})
