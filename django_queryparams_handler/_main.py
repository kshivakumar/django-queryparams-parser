from django.urls import path as _path
from django.urls.resolvers import URLPattern

from django_queryparams_handler._params import QueryParam
from django_queryparams_handler._exceptions import MissingRequiredQueryParameter


class QueryParamGroup:
    def __init__(self, query_params, required=False): ...


class _QueryParams:
    def __init__(self):
        self.mapping = {}

    def map(self, pattern, params):
        self.mapping[pattern] = params

    def validate(self, path, query_dict):
        # TODO: Optimize
        path = path.lstrip("/")
        for pattern, declared_query_params in self.mapping.items():
            if pattern.match(path):
                for param in declared_query_params:
                    if param.name in query_dict:
                        param.validate(query_dict[param.name])
                    elif param.required:
                        raise MissingRequiredQueryParameter(param.name)


QueryParams = _QueryParams()

# TODO: handle multiple `path`s with same routes


def _save_pathqueries(urlpattern, query_params, transform):
    if query_params and len(query_params) > 0:
        QueryParams.map(urlpattern.pattern, query_params)
        return


def path(url, view, *, query_params=None, transform=False, **kwargs):
    urlpattern = _path(url, view, **kwargs)
    _save_pathqueries(urlpattern, query_params, transform)
    return urlpattern


def pathquery(urlpattern, *, query_params=None, transform=False):
    if isinstance(urlpattern, URLPattern):
        _save_pathqueries(urlpattern, query_params, transform)
        return urlpattern
    raise TypeError(f"expected URLPattern, received {type(urlpattern)}")
