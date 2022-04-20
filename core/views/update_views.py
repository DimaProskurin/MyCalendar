from django.http import HttpResponse, HttpResponseBadRequest, JsonResponse
from django.views.decorators.csrf import csrf_exempt

from core.models import Invite


@csrf_exempt
def update_invite(request, id):
    if request.method != "PUT":
        return HttpResponseBadRequest("The HTTP request should be PUT type")

    invite_query = Invite.objects.filter(id=id)
    if len(invite_query) == 0:
        return HttpResponseBadRequest(f"No invite with such id = {id}")
    invite = invite_query[0]

    new_status = request.GET.get("status")
    if new_status is None:
        return HttpResponseBadRequest("No new status provided")

    if new_status not in Invite.Status.names:
        return HttpResponseBadRequest(f"Status {new_status} is not valid")

    new_status = Invite.Status[new_status]
    invite.status = new_status
    invite.save()
    return HttpResponse(str(invite))
