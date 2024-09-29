from django.conf import settings
from django.http import HttpResponseBadRequest
from django.utils.datastructures import MultiValueDict

from django_queryparams_handler._main import QueryParams


def QueryParamsHandler(get_response):
    def handler(request):
        breakpoint()
        parsed, errors = QueryParams.validate(request.path, request.GET)
        if errors:
            if settings.DEBUG:
                # return DetailedReport
                return HttpResponseBadRequest("<br>".join(errors))
            # TODO: Choose json or template response using content negotiation
            return HttpResponseBadRequest()
            # TODO: log the errors
        request.parsed_query_params = MultiValueDict(parsed)
        resp = get_response(request)
        return resp

    return handler
