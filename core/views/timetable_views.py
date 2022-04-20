import datetime

from django.http import HttpResponseBadRequest, JsonResponse
from django.utils.dateparse import parse_duration
from django.utils.timezone import make_aware

from core.common.segment_union import union_stream
from core.models import User


def get_first_free_time_slot(request):
    # get and validate user_ids param
    user_ids_param = request.GET.get("user_ids")
    if user_ids_param is None:
        return HttpResponseBadRequest("No user_ids are provided")
    user_ids = user_ids_param.split(",")
    try:
        user_ids = [int(id) for id in user_ids]
    except ValueError:
        return HttpResponseBadRequest("Provided user_ids are not valid")

    # get and validate duration param
    duration = request.GET.get("duration")
    if duration is None:
        return HttpResponseBadRequest("No duration is provided")
    duration = parse_duration(duration)
    if duration is None or duration <= datetime.timedelta(0):
        return HttpResponseBadRequest("Your duration is not valid")

    # found user for each user_id
    users = User.objects.filter(id__in=user_ids)
    if len(users) < len(user_ids):
        not_found_ids = set(user_ids) - set(user.id for user in users)
        return HttpResponseBadRequest(f"No user found for ids = {not_found_ids}")

    min_start = make_aware(datetime.datetime.now())
    occupied_timeline = union_stream([user.get_occupied_time_slots() for user in users])
    try:
        start, end = next(occupied_timeline)
        if min_start + duration <= start:
            return JsonResponse({"start": min_start, "end": min_start + duration})
    except StopIteration:
        # all users are free
        return JsonResponse({"start": min_start, "end": min_start + duration})

    prev_start, prev_end = start, end
    for start, end in occupied_timeline:
        if prev_end + duration <= start:
            return JsonResponse({"start": prev_end, "end": prev_end + duration})
        prev_start, prev_end = start, end

    return JsonResponse({"start": end, "end": end + duration})
