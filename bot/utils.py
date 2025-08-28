import datetime
import enum
import os
import pkgutil
import re
from collections.abc import Iterator
from pathlib import Path


class Unit(enum.Enum):
    NANOSECOND = 1
    MICROSECOND = 10**3
    MILLISECOND = 10**6
    SECOND = 10**9
    MINUTE = 60 * 10**9
    HOUR = 60 * 60 * 10**9
    DAY = 24 * 60 * 60 * 10**9
    WEEK = 7 * 24 * 60 * 60 * 10**9
    MONTH = 30 * 24 * 60 * 60 * 10**9
    YEAR = 365 * 24 * 60 * 60 * 10**9


UNIT_PATTERNS = {
    Unit.NANOSECOND: r"n(ano)?s(ec(onds?)?)?",
    Unit.MICROSECOND: r"([μµu]|(micro))s(ec(onds?)?)?",
    Unit.MILLISECOND: r"m(ill?i)?s(ec(onds?)?)?",
    Unit.SECOND: r"s(ec(onds?)?)?",
    Unit.MINUTE: r"m(in(utes?)?)?",
    Unit.HOUR: r"h(r|(ours?)?)",
    Unit.DAY: r"d(ays?)?",
    Unit.WEEK: r"w(eeks?)?",
    Unit.MONTH: r"months?",
    Unit.YEAR: r"y(ears?)?",
}

VALUTE_PATTERNS = {unit: rf"\d+(\.\d+)?\s*(?={pattern}(\.|,|\s|\d|$))" for unit, pattern in UNIT_PATTERNS.items()}

VALIDATION_PATTERN = r"^\s*(\d+(\.\d+)?\s*({})\s*(\.|,|\s*|$)?\s*)*$".format(
    "|".join(rf"({pattern})" for pattern in UNIT_PATTERNS.values()),
)


_compiled_value_patterns = {
    unit: re.compile(
        pattern,
        re.IGNORECASE,
    )
    for unit, pattern in VALUTE_PATTERNS.items()
}
_compiled_validation_pattern = re.compile(
    VALIDATION_PATTERN,
    re.IGNORECASE,
)


def parse_nanoseconds(
    duration: str,
    validate: bool = True,
) -> int:
    """Parse a duration into nanoseconds.

    Arguments:
        duration: The duration string.
        validate: Require entire duration string
            to follow a valid format. If false,
            parse and combine the parts that are
            valid.

    Returns:
        Duration in nanoseconds.
    """
    ns = 0
    if not duration:
        return ns
    if validate and not _compiled_validation_pattern.fullmatch(duration):
        msg = f"invalid duration format: {duration}"
        raise ValueError(
            msg,
        )
    for unit, pattern in _compiled_value_patterns.items():
        match = pattern.search(duration)
        if match:
            ns += int(unit.value * float(match.group()))
    return ns


def parse(
    duration: str,
    validate: bool = True,
) -> float:
    """Parse a duration into seconds as a floating point number.

    Arguments:
        duration: The duration string.
        validate: Require entire duration string
            to follow a valid format. If false,
            parse and combine the parts that are
            valid.

    Returns:
        Duration in seconds.
    """
    nanoseconds = parse_nanoseconds(
        duration,
        validate,
    )
    return nanoseconds / Unit.SECOND.value


def parse_timedelta(
    duration: str,
    validate: bool = True,
) -> datetime.timedelta:
    """Parse a duration into a :class:`datetime.timedelta`.

    Arguments:
        duration: The duration string.
        validate: Require entire duration string
            to follow a valid format. If false,
            parse and combine the parts that are
            valid.

    Returns:
        Duration as :class:`datetime.timedelta`.
    """
    nanoseconds = parse_nanoseconds(
        duration,
        validate,
    )
    seconds = nanoseconds // Unit.SECOND.value
    microseconds = (nanoseconds % Unit.SECOND.value) / Unit.MICROSECOND.value
    return datetime.timedelta(
        seconds=seconds,
        microseconds=microseconds,
    )


def search_directory(path: str) -> Iterator[str]:
    """Walk through a directory and yield all modules.

    Parameters
    ----------
    path: :class:`str`
        The path to search for modules

    """
    relpath = os.path.relpath(path)  # relative and normalized
    if ".." in relpath:
        msg = "Modules outside the cwd require a package to be specified"
        raise ValueError(msg)

    abspath = Path(path).resolve()
    if not Path(relpath).exists():
        msg = f"Provided path '{abspath}' does not exist"
        raise ValueError(msg)
    if not Path(relpath).is_dir():
        msg = f"Provided path '{abspath}' is not a directory"
        raise ValueError(msg)

    prefix = relpath.replace(os.sep, ".")
    if prefix in ("", "."):
        prefix = ""
    else:
        prefix += "."

    for _, name, ispkg in pkgutil.iter_modules([path]):
        if ispkg:
            yield from search_directory(Path(path) / name)
        else:
            yield prefix + name
