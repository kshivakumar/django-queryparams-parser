from collections import defaultdict
from typing import Any, Callable, List

from django.conf import settings
from django.http import HttpResponseBadRequest
from django.http.request import HttpRequest
from django.utils.datastructures import MultiValueDict
from django.views import generic

from django_queryparams_parser.params import InvalidQueryParameter, QueryParam


class QueryParamGroup:
    """Group of related query parameters that should be validated together"""

    def __init__(self, query_params: List[QueryParam]):
        for param in query_params:
            if not isinstance(param, QueryParam):
                raise TypeError(f"Expected QueryParam, received {type(param)}")
        self.query_params = query_params


def parse_query_params(query_params: List[Any]):
    """Decorator to declare query parameters for a view function"""

    declared_params = _normalize_params(query_params)

    def wrapper(view: Callable) -> Callable:
        def validator(self_or_request, *args, **kwargs):
            if isinstance(self_or_request, generic.View):
                request = args[0]
            elif isinstance(self_or_request, HttpRequest):
                request = self_or_request
            else:
                raise ValueError()

            parsed, errors = validate_query_params(declared_params, request.GET)

            if errors:
                if settings.DEBUG:
                    # return DetailedReport
                    return HttpResponseBadRequest("<br>".join(errors))
                # TODO: Choose json or template response using content negotiation
                return HttpResponseBadRequest()

            request.parsed_query_params = MultiValueDict(parsed)

            return view(request, *args, **kwargs)

        return validator

    return wrapper


def validate_query_params(declared_params, request_params):
    parsed = defaultdict(list)
    errors = []

    for param in declared_params:
        if param.name in request_params:
            try:
                parsed[param.name].extend(
                    param.validate_all(request_params.getlist(param.name))
                )
            except InvalidQueryParameter as exc:
                errors.append(f"{str(exc)}: {param.name}")
        elif param.required:
            errors.append(f"Missing required query param: {param.name}")
        else:  # undeclared param
            # TODO: Review
            # Doing nothing reduces strictness
            # raise error? or provide a library-level flag for user to decide
            pass

    return parsed, errors


def _normalize_params(params: List[Any]) -> List[QueryParam]:
    """Convert mixed parameter types into a flat list of QueryParams"""
    normalized = []
    for param in params:
        if isinstance(param, QueryParamGroup):
            normalized.extend(param.query_params)
        elif isinstance(param, QueryParam):
            normalized.append(param)
        else:
            raise TypeError(
                f"Expected QueryParam or QueryParamGroup, received {type(param)}"
            )
    return normalized
