from django.conf import settings
from django.http import HttpResponseBadRequest
from django.utils.datastructures import MultiValueDict

from django_queryparams_parser._main import QueryParams


def QueryParamsParser(get_response):
    def parser(request):
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

    return parser
