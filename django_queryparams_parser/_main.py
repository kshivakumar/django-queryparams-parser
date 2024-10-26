from collections import defaultdict

from django.conf import settings
from django.urls import path as _path
from django.urls.resolvers import URLPattern

from django_queryparams_parser.params import QueryParam, InvalidQueryParameter


class QueryParamGroup:
    def __init__(self, query_params):
        for qp in query_params:
            if not isinstance(qp, QueryParam):
                raise TypeError(f"expected QueryParam, received {type(qp)}")
        self.query_params = query_params


class _QueryParams:
    def __init__(self):
        self.mapping = {}
        self.view_func_qps = {}

    def map(self, pattern, params):
        qps = validate_query_params(params)
        self.mapping[pattern] = qps

    def validate(self, path, query_dict):
        # TODO: Optimize
        parsed, errors = defaultdict(list), []
        for pattern, declared_query_params in self.mapping.items():
            # REVIEW: Use view func instead of url to identify and validate the query params
            if pattern.match(path.lstrip("/")):
                for param in declared_query_params:
                    if param.name in query_dict:
                        try:
                            parsed[param.name].extend(
                                param.validate_all(query_dict.getlist(param.name))
                            )
                        except InvalidQueryParameter as exc:
                            errors.append(f"{str(exc)}: {param.name}")
                    elif param.required:
                        errors.append(f"Missing required query param: {param.name}")
        return parsed, errors


def validate_query_params(params):
    qps = []
    for param in params:
        if isinstance(param, QueryParamGroup):
            qps.extend(param.query_params)
        elif isinstance(param, QueryParam):
            qps.append(param)
        else:
            raise TypeError(
                f"expected QueryParam or QueryParamGroup, received {type(param)}"
            )
    return qps


QueryParams = _QueryParams()

# TODO: handle multiple `path`s with same routes


def _save_pathqueries(urlpattern, query_params):
    if query_params and len(query_params) > 0:
        QueryParams.map(urlpattern.pattern, query_params)
        return

    # Check if the query_params are added at the view level
    ids = collect_function_ids(urlpattern.callback)
    for id_, qps in list(QueryParams.view_func_qps.items()):
        if id_ in ids:
            QueryParams.mapping[urlpattern.pattern] = qps
            del QueryParams.view_func_qps[id_]
            break


def path(url, view, *, query_params=None, **kwargs):
    if _middleware_disabled():
        return _path(url, view, **kwargs)

    urlpattern = _path(url, view, **kwargs)
    _save_pathqueries(urlpattern, query_params)

    return urlpattern


def pathquery(urlpattern, *, query_params=None):
    if _middleware_disabled():
        return urlpattern

    if isinstance(urlpattern, URLPattern):
        _save_pathqueries(urlpattern, query_params)
        return urlpattern

    raise TypeError(f"expected URLPattern, received {type(urlpattern)}")


# view decorator
def parse_query_params(query_params):
    def wrapper(view):
        if _middleware_disabled():
            return view

        QueryParams.view_func_qps[id(view)] = validate_query_params(query_params)

        return view

    return wrapper


def _middleware_disabled():
    return (
        "django_queryparams_parser.middleware.QueryParamsParser"
        not in settings.MIDDLEWARE
    )


def collect_function_ids(func):
    """Recursively collect the id() of inner functions"""
    ids = [id(func)]

    if hasattr(func, "__closure__"):
        for cell in func.__closure__ or []:
            inner_func = cell.cell_contents
            if callable(inner_func):
                ids.extend(collect_function_ids(inner_func))

    return ids
