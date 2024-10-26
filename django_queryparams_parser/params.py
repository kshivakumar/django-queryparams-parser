from datetime import date
from inspect import signature

# Notes:
# 1. Do defensive programming in `__init__`
# 2. Write performant code in `validate`
# 3. Use stdlib functions to parse and/or validate. Use regex only if it's faster.

# Performance improvement ideas:
# - Use Metaclasses to dynamically create efficient classes at initialization time
# - Improve validation performance by dynamically clubbing
#   function source codes to reduce function call overhead
# - Replace list comprehensions or for-loops with map and filter

# TODO:
# - Handle null/empty param values
# - Define DateTime
# - Prefix/suffix query param name in all exception messages
# - Implement QueryParamGroup
# - Optimize QueryParam memory usage, use slots?
# - Add annotations
# - Add extensive docstrings
# - Define UUID
# - Define Base64

# Customization Options:
# 1. Pass a list of validating functions to `validators` argument
# 2. Extend `QueryParam` class and define `validate` method


class QueryParamError(Exception):
    pass


class InvalidQueryParameter(QueryParamError):
    pass


class QueryParam:
    def __init__(
        self,
        name,
        *,
        required=False,
        many=False,
        choices=None,
        validators=None,
    ):
        if not isinstance(name, str):
            raise TypeError(f"'name' must be string, not {type(name)}")
        self.name = name

        self._value_checks = []

        if not isinstance(required, bool):
            raise TypeError(f"'required' must be a bool, not {type(required)}")
        self.required = required

        if not isinstance(many, bool):
            raise TypeError(f"'many' must be a bool, not {type(many)}")
        self.many = many

        if choices is not None and validators is not None:
            raise ValueError("Only one of 'choices' or 'validators' is allowed")

        if choices is not None:
            if not isinstance(choices, (tuple, list)):
                raise TypeError(f"'choices' must be a list/tuple, not {type(choices)}")
            if not all(isinstance(c, str) for c in choices):
                raise TypeError("choices must be strings")
            choices = self._validate_choices(choices)
            self._value_checks.append(self._check_one_of_choices)
        self.choices = choices or set()

        if validators is not None:
            if not isinstance(validators, (tuple, list)):
                raise TypeError(
                    f"'validators' must be a list/tuple, not '{type(validators)}'"
                )
            for validator in validators:
                if not callable(validator):
                    raise ValueError(f"Validator {validator.__name__} is not callable")
                sig = signature(validator)
                if len(sig.parameters) != 2:
                    raise ValueError(
                        f"Validator {validator.__name__} must have exactly two parameters"
                    )
            self._value_checks.extend(validators)

    def validate_single(self, value):
        parsed = self.parse(value)
        self._check(value, parsed)
        return parsed

    def validate_all(self, values):
        if self.many or len(values) == 1:
            return [self.validate_single(value) for value in values]
        else:
            raise InvalidQueryParameter(f"Expected 1 value, got {len(values)}")

    # REVIEW: different `validate` function when choices are given, directly do 'in' check

    def parse(self, value):
        raise NotImplementedError("implement in child classes")

    def _check(self, value, parsed):
        for val_check in self._value_checks:
            val_check(value, parsed)

    def _validate_choices(self, choices):
        return {self.validate_single(choice) for choice in choices}

    def _check_one_of_choices(self, value, parsed):
        if parsed not in self.choices:
            raise InvalidQueryParameter()


class BoundedParam(QueryParam):
    def __init__(self, name, *, min_value=None, max_value=None, **kwargs):
        super().__init__(name, **kwargs)

        if self.choices and (min_value is not None or max_value is not None):
            raise ValueError(
                "'min_value' and/or 'max_value' can't be clubbed with 'choices'"
            )

        self.min_value = None if min_value is None else self.validate_single(min_value)
        self.max_value = None if max_value is None else self.validate_single(max_value)

        if (self.min_value and self.max_value) and self.max_value < self.min_value:
            raise ValueError("'max_value' must be >= 'min_value'")

        if min_value is not None and max_value is not None:
            self._value_checks.append(self._check_upper_and_lower_bounds)
        elif min_value is not None:
            self._value_checks.append(self._check_lower_bound)
        elif max_value is not None:
            self._value_checks.append(self._check_upper_bound)

    def check_lower_bound(self, value, parsed):
        if not parsed > self.min_value:
            raise InvalidQueryParameter()

    def check_upper_bound(self, value, parsed):
        if not parsed < self.max_value:
            raise InvalidQueryParameter()

    def check_upper_and_lower_bounds(self, value, parsed):
        if not (self.min_value <= parsed <= self.max_value):
            raise InvalidQueryParameter()


class Number(BoundedParam):
    def __init__(
        self,
        name,
        *,
        allow_lead_zeros=True,
        allow_plus_sign=True,
        **kwargs,
    ):
        super().__init__(name, **kwargs)

        if not isinstance(allow_lead_zeros, bool):
            raise TypeError(
                f"'allow_lead_zeros' must be a bool, not '{type(allow_lead_zeros)}'"
            )

        if not isinstance(allow_plus_sign, bool):
            raise TypeError(
                f"'allow_plus_sign' must be a bool, not '{type(allow_plus_sign)}'"
            )

        if (not allow_lead_zeros) and (not allow_plus_sign):
            self._value_checks.append(self._check_lead_zeros_and_plus_sign)
        elif not allow_lead_zeros:
            self._value_checks.append(self._check_lead_zeros)
        elif not allow_plus_sign:
            self._value_checks.append(self._check_plus_sign)

    def check_lead_zeros(self, value, parsed):
        if value[0] in ("+", "-") and value[1:2] == ["0"] and len(value) > 2:
            raise InvalidQueryParameter()
        elif value[0] == "0" and len(value) > 1:
            raise InvalidQueryParameter()

    def check_plus_sign(self, value, parsed):
        if value[0] == "+":
            raise InvalidQueryParameter()

    def check_lead_zeros_and_plus_sign(self, value, parsed):
        if value[0] == "+":
            raise InvalidQueryParameter()
        elif value[0] == "0" and value != "0":
            raise InvalidQueryParameter()
        elif value != "-0":
            raise InvalidQueryParameter()


class Int(Number):
    def __new__(cls, name, **kwargs):
        # REVIEW: Is this implicit behaviour required?
        if kwargs.get("min_value") == 0:
            return PositiveInt(name, **kwargs)
        return super().__new__(cls)

    def parse(self, value):
        try:
            return int(value)
        except ValueError:
            raise InvalidQueryParameter()


class PositiveInt(Int):
    def __init__(self, name, **kwargs):
        if kwargs.get("min_value", 0) < 0:
            raise ValueError()

        super().__init__(name, **kwargs)

        # REVIEW:
        # self.min_value = 0
        # self._value_checks.append(self._check_lower_bound)

    def parse(self, value):
        try:
            parsed = int(value)
        except ValueError:
            raise InvalidQueryParameter()
        else:
            if parsed < 0:
                raise InvalidQueryParameter()
            return parsed


class Float(Number):
    def __new__(cls, name, **kwargs):
        if kwargs.get("min_value") == 0:
            return PositiveFloat(name, **kwargs)
        return super().__new__(cls)

    def parse(self, value):
        try:
            return float(value)
        except ValueError:
            raise InvalidQueryParameter()


class PositiveFloat(Float):
    def __init__(self, name, **kwargs):
        if kwargs.get("min_value", 0) < 0:
            raise ValueError()

        super().__init__(name, **kwargs)

    def parse(self, value):
        try:
            parsed = float(value)
        except ValueError:
            raise InvalidQueryParameter()
        else:
            if parsed < 0:
                raise InvalidQueryParameter()
            return parsed


class Str(QueryParam):
    def __init__(self, name, *, min_length=None, max_length=None, **kwargs):
        super().__init__(name, **kwargs)

        if self.choices and (min_length is not None or max_length is not None):
            raise ValueError()

        if min_length:
            if not isinstance(min_length, int) or min_length < 1:
                raise ValueError("'min_length' must be a natural number(> 0)")
        self.min_length = min_length

        if max_length:
            if not isinstance(max_length, int) or min_length < 1:
                raise ValueError("'max_length' must be a natural number(> 0)")
        self.min_length = min_length

        if min_length and max_length and (max_length < min_length):
            raise ValueError("'max_length' must be >= 'min_length'")

        if min_length is not None and max_length is not None:
            self._value_checks.append(self._check_min_and_max_length)
        elif min_length is not None:
            self._value_checks.append(self._check_min_length)
        elif max_length is not None:
            self._value_checks.append(self._check_max_length)

    def parse(self, value):
        return value

    def check_empty_string(self, value, parsed):
        if not self.allow_empty and len(value) == 0:
            raise InvalidQueryParameter()

    def check_min_length(self, value, parsed):
        if not len(value) < self.min_length:
            raise InvalidQueryParameter()

    def check_max_length(self, value, parsed):
        if not len(value) > self.max_length:
            raise InvalidQueryParameter()

    def check_min_and_max_length(self, value, parsed):
        if not (self.min_length <= len(value) <= self.max_length):
            raise InvalidQueryParameter()


class Date(BoundedParam):
    def __init__(self, name, *, separator="-", **kwargs):
        if separator not in ("-", "/"):
            raise ValueError()

        self.separator = separator

        super().__init__(name, **kwargs)

    def parse(self, value):
        if self.separator != "-":
            value = value.replace(self.separator, "-")
        try:
            return date.fromisoformat(value)
        except ValueError:
            raise InvalidQueryParameter()


class Bool(QueryParam):
    def __init__(
        self,
        name,
        *,
        required=False,
        explicit=False,
        ignore_case=True,
        custom_bool=None,
    ):
        if not isinstance(name, str):
            raise TypeError(f"'name' must be string, not '{type(name)}'")
        self.name = name

        self.truthy = "true"
        self.falsy = "false"

        # TODO: handle `required` differently
        if not explicit and required:
            raise ValueError("'explicit' must be True if 'required' is True")

        self.required = required
        self.explicit = explicit
        self.ignore_case = ignore_case

        if custom_bool:
            if len(custom_bool) != 2 and not all(
                isinstance(v, str) for v in custom_bool
            ):
                raise ValueError()
            self.truthy, self.falsy = custom_bool

    def validate_all(self, values):
        # TODO: what if multiple values are passed?
        # For the time being, consider the last value as the correct one
        value = values[-1]
        if not self.explicit and value == "":
            return [True]  # TODO: Review
        if self.ignore_case:
            value = value.lower()
        if value == self.truthy:
            return [True]
        elif value == self.falsy:
            return [False]
        else:
            raise InvalidQueryParameter(
                f"Expected one of [{self.truthy}, {self.falsy}], got '{value}'"
            )
