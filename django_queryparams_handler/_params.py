import re
from enum import Enum

from django_queryparams_handler._exceptions import InvalidQueryParameter


RE_POSITIVE_INT = re.compile("\\b[1-9]\d*\\b")
RE_POSITIVE_INT_ZERO_PADDED = re.compile("^\d*$")


class ParamTypes(Enum):
    pass


class QueryParam:
    def __init__(
        self,
        name,
        type_,
        *,
        required=False,
        multiple=False,
        min_length=None,  # str length
        max_length=None,  # str length
        min_value=None,  # applicable to int/float/date/datetime/year
        max_value=None,  # applicable to int/float/date/datetime/year
    ):
        self.name = name
        if type_ not in (int, float, str):
            raise ValueError(f"data type {type_} not supported")
        self.type_ = type_
        self.required = required

    def __eq__(self, other):
        return self.__dict__ == other.__dict__

    def validate(self, value):
        if self.type_ == int:
            if RE_POSITIVE_INT.match(value) is None:
                raise InvalidQueryParameter(value)
        elif self.type_ == float:
            pass
        elif self.type_ == "date":  # iso
            pass
        elif self.type_ == "datetime":  # iso
            pass
        elif self.type_ == "date_american":
            raise NotImplementedError()
        elif self.type_ == "year":
            raise NotImplementedError()
