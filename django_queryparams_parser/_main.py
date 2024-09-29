from collections import defaultdict

from django.urls import path as _path
from django.urls.resolvers import URLPattern

from django_queryparams_parser.params import InvalidQueryParameter


class QueryParamGroup:
    def __init__(self, query_params, required=False): ...


class _QueryParams:
    def __init__(self):
        self.mapping = {}

    def map(self, pattern, params):
        self.mapping[pattern] = params

    def validate(self, path, query_dict):
        # TODO: Optimize
        parsed, errors = defaultdict(list), []
        for pattern, declared_query_params in self.mapping.items():
            # REVIEW: Use view func instead of url to identify and validate the query params
            if pattern.match(path.lstrip("/")):
                for param in declared_query_params:
                    if param.name in query_dict:
                        try:
                            parsed[param.name].append(
                                param.validate(query_dict[param.name])
                            )
                        except InvalidQueryParameter as exc:
                            errors.append(f"{str(exc)}: {param.name}")
                    elif param.required:
                        errors.append(f"Missing required query param: {param.name}")
        return parsed, errors


QueryParams = _QueryParams()

# TODO: handle multiple `path`s with same routes


def _save_pathqueries(urlpattern, query_params):
    if query_params and len(query_params) > 0:
        QueryParams.map(urlpattern.pattern, query_params)
        return


def path(url, view, *, query_params=None, **kwargs):
    urlpattern = _path(url, view, **kwargs)
    _save_pathqueries(urlpattern, query_params)
    return urlpattern


def pathquery(urlpattern, *, query_params=None):
    if isinstance(urlpattern, URLPattern):
        _save_pathqueries(urlpattern, query_params)
        return urlpattern
    raise TypeError(f"expected URLPattern, received {type(urlpattern)}")
