from django.conf import settings
from django.http import HttpResponseBadRequest

from django_queryparams_handler._main import QueryParams


def QueryParamsHandler(get_response):
    def handler(request):
        errors = validate(request.path, request.GET)
        if errors:
            if settings.DEBUG:
                # return DetailedReport
                pass
            # TODO: Choose json or template response using content negotiation
            return HttpResponseBadRequest(
                "One or more query parameters have invalid values"
            )
        resp = get_response(request)
        return resp

    return handler


def validate(path, params):
    try:
        QueryParams.validate(path, params)
    except:
        return ["e1", "e2"]
