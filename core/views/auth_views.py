import json
from json import JSONDecodeError

from django.contrib.auth import authenticate, login, logout
from django.http import HttpResponse, HttpResponseBadRequest
from django.views.decorators.csrf import csrf_exempt


@csrf_exempt
def login_view(request):
    if request.method != "POST":
        return HttpResponseBadRequest("The HTTP request should be POST type")

    try:
        body_data = json.loads(request.body)
        username = body_data["username"]
        password = body_data["password"]
    except JSONDecodeError:
        return HttpResponseBadRequest("Request body is not valid JSON")
    except KeyError as e:
        return HttpResponseBadRequest(f"Your POST query has no key {e}")

    user = authenticate(request, username=username, password=password)
    if user is not None:
        login(request, user)
        return HttpResponse(f"Logged in as {user}")
    else:
        return HttpResponseBadRequest("Failed login. Invalid username or password")


def logout_view(request):
    logout(request)
    return HttpResponse("Logged out")
