from typing import Callable, Set

from django.conf import settings


def is_middleware_disabled() -> bool:
    """Check if this package's middleware is disabled."""
    return (
        "django_queryparams_parser.middleware.QueryParamMiddleware"
        not in settings.MIDDLEWARE
    )


def get_closure_function_ids(func: Callable) -> Set[int]:
    """Recursively collect the ID of a function and its closure functions."""
    ids = {id(func)}

    if hasattr(func, "__closure__"):
        for cell in func.__closure__ or []:
            inner_func = cell.cell_contents
            if callable(inner_func):
                ids.update(get_closure_function_ids(inner_func))

    return ids
