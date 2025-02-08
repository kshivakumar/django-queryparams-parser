from collections import defaultdict
from typing import Any, Callable, Dict, List, Tuple

from django.urls import path as django_path
from django.urls.resolvers import URLPattern

from django_queryparams_parser._utils import (
    get_closure_function_ids,
    is_middleware_disabled,
)
from django_queryparams_parser.params import InvalidQueryParameter, QueryParam


class PatternAlreadyRegisteredError(Exception):
    pass


class QueryParamCollection:
    """Group of related query parameters that should be validated together"""

    def __init__(self, query_params: List[QueryParam]):
        for param in query_params:
            if not isinstance(param, QueryParam):
                raise TypeError(f"Expected QueryParam, received {type(param)}")
        self.query_params = query_params


class QueryParamRegistry:
    """Central registry for URL pattern query parameter definitions and validation"""

    def __init__(self):
        self.pattern_params: Dict[Any, List[QueryParam]] = {}
        self._view_params: Dict[int, List[QueryParam | QueryParamCollection]] = {}

    def register_pattern(self, pattern: Any, params: List[Any]) -> None:
        """Register query parameters for a URL pattern."""
        if pattern in self.pattern_params:
            raise PatternAlreadyRegisteredError(pattern)
        normalized_params = self._normalize_params(params)
        self.pattern_params[pattern] = normalized_params

    def validate_request_params(
        self, path: str, query_dict: Dict
    ) -> Tuple[Dict, List[str]]:
        """Validate query parameters for a given request path"""
        parsed = defaultdict(list)
        errors = []

        for pattern, declared_params in self.pattern_params.items():
            if pattern.match(path.lstrip("/")):
                for param in declared_params:
                    if param.name in query_dict:
                        try:
                            parsed[param.name].extend(
                                param.validate_all(query_dict.getlist(param.name))
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

    @staticmethod
    def _normalize_params(params: List[Any]) -> List[QueryParam]:
        """Convert mixed parameter types into a flat list of QueryParams"""
        normalized = []
        for param in params:
            if isinstance(param, QueryParamCollection):
                normalized.extend(param.query_params)
            elif isinstance(param, QueryParam):
                normalized.append(param)
            else:
                raise TypeError(
                    f"Expected QueryParam or QueryParamCollection, received {type(param)}"
                )
        return normalized

    def __str__(self) -> str:
        return "\n".join(
            f"{pattern._route}: {[str(qp) for qp in query_params]}"
            for pattern, query_params in self.pattern_params.items()
        )


# Global registry instance
param_registry = QueryParamRegistry()


def register_path_params(urlpattern: URLPattern, query_params: List[Any]) -> None:
    """Register query parameters for a URL pattern"""
    if query_params:
        try:
            param_registry.register_pattern(urlpattern.pattern, query_params)
        except PatternAlreadyRegisteredError:
            raise ValueError(
                f"query params are defined at both urlconf {urlpattern.pattern} and its view"
            )

    # Check for parameters registered via decorator
    func_ids = get_closure_function_ids(urlpattern.callback)
    for func_id, params in param_registry._view_params.items():
        if func_id in func_ids:
            try:
                param_registry.register_pattern(urlpattern.pattern, params)
            except PatternAlreadyRegisteredError:
                # TODO: print view func name, if possible
                raise ValueError(
                    f"query params are defined at both urlconf '{urlpattern.pattern}' and its view"
                )
            del param_registry._view_params[func_id]
            break


def path(
    url: str, view: Callable, *, query_params: List[Any] = None, **kwargs
) -> URLPattern:
    """Extended Django `path()` that supports query parameter validation"""
    urlpattern = django_path(url, view, **kwargs)

    if is_middleware_disabled():
        return urlpattern

    register_path_params(urlpattern, query_params)

    return urlpattern


def parse_query_params(query_params: List[Any]):
    """Decorator to register query parameters for a view function"""

    def wrapper(view: Callable) -> Callable:
        if is_middleware_disabled():
            return view

        param_registry._view_params[id(view)] = query_params

        return view

    return wrapper
