import json
from json import JSONDecodeError

from django.core.exceptions import ValidationError
from django.core.validators import validate_email
from django.contrib.auth.password_validation import validate_password
from django.http import HttpResponse, HttpResponseBadRequest, JsonResponse
from django.utils.dateparse import parse_datetime
from django.views.decorators.csrf import csrf_exempt

from core.models import Event, Invite, RRule, User


@csrf_exempt
def create_user(request):
    if request.method != "POST":
        return HttpResponseBadRequest("The HTTP request should be POST type")

    # required parameters
    try:
        body_data = json.loads(request.body)
        username = body_data["username"]
        password = body_data["password"]
        first_name = body_data["first_name"]
        last_name = body_data["last_name"]
        email = body_data["email"]
    except JSONDecodeError:
        return HttpResponseBadRequest("Request body is not valid JSON")
    except KeyError as e:
        return HttpResponseBadRequest(f"Your POST query has no key {e}")

    # validate email
    try:
        validate_email(email)
    except ValidationError as e:
        return HttpResponseBadRequest(f"Your email {email} is not valid because {e}")

    # validate password
    try:
        validate_password(password)
    except ValidationError as e:
        return HttpResponseBadRequest(f"Your password is not valid because {e}")

    # check if such user exists
    if len(User.objects.filter(email=email)) > 0:
        return HttpResponseBadRequest("User with such email already exists")

    # create and save user
    user = User(
        username=username, first_name=first_name, last_name=last_name, email=email
    )
    user.set_password(password)
    user.save()
    return HttpResponse(f"{user} has been created")


@csrf_exempt
def create_event(request):
    if not request.user.is_authenticated:
        return HttpResponseBadRequest("You are not logged in to create event")

    if request.method != "POST":
        return HttpResponseBadRequest("The HTTP request should be POST type")

    # required fields
    try:
        body_data = json.loads(request.body)
        title = body_data["title"]
        start = parse_datetime(body_data["start"])
        end = parse_datetime(body_data["end"])
    except JSONDecodeError:
        return HttpResponseBadRequest("Request body is not valid JSON")
    except KeyError as e:
        return HttpResponseBadRequest(f"Your POST query has no key {e}")
    except ValueError as e:
        return HttpResponseBadRequest(f"Input params is not valid because {e}")

    # validate start & end
    if start is None or end is None:
        return HttpResponseBadRequest(
            f"Your {body_data['start']} and {body_data['end']} aren't valid format"
        )
    if start > end:
        return HttpResponseBadRequest("End date should be greater than start date")

    # optional fields
    description = body_data.get("description") or ""
    is_private = bool(body_data.get("is_private") or False)
    is_recurring = bool(body_data.get("is_recurring") or False)
    invited_emails = body_data.get("invited_emails") or []

    # validate repeats
    repeats = None
    if is_recurring:
        repeats = body_data.get("repeats")
        if repeats is None:
            return HttpResponseBadRequest("Event is recurring but no repeats provided")
        default_rrules = {"daily", "weekly", "monthly", "yearly"}
        for repeat in repeats:
            if repeat not in default_rrules:
                return HttpResponseBadRequest(
                    f"Repeat value {repeat} is not valid. Valid is {default_rrules}"
                )

    # create event
    owner = request.user
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
    if repeats:
        default_rrules = {
            "daily": RRule.daily(event.id, event.start),
            "weekly": RRule.weekly(event.id, event.start),
            "monthly": RRule.monthly(event.id, event.start),
            "yearly": RRule.yearly(event.id, event.start),
        }
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
