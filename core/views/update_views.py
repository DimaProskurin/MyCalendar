from django.http import HttpResponse, HttpResponseBadRequest, JsonResponse
from django.views.decorators.csrf import csrf_exempt

from core.models import Invite


def exist_invite(invite_id):
    invite_query = Invite.objects.filter(id=invite_id)
    if len(invite_query) == 0:
        return None, HttpResponseBadRequest(f"No invite with such id = {invite_id}")
    return invite_query[0], None


@csrf_exempt
def update_invite(request, invite_id):
    if request.method != "PUT":
        return HttpResponseBadRequest("The HTTP request should be PUT type")

    new_status = request.GET.get("status")
    if new_status is None:
        return HttpResponseBadRequest("No new status provided")

    if new_status not in Invite.Status.names:
        return HttpResponseBadRequest(f"Status {new_status} is not valid")

    invite, err = exist_invite(invite_id)
    if err:
        return err

    if invite.user_id != request.user.id:
        return HttpResponseBadRequest("You are not able to change not yours invites")

    new_status = Invite.Status[new_status]
    invite.status = new_status
    invite.save()
    return HttpResponse(str(invite))
