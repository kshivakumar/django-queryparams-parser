class QueryParamError(Exception):
    pass


class InvalidQueryParameter(QueryParamError):
    pass


class MissingRequiredQueryParameter(QueryParamError):
    pass
