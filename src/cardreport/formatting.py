"""Immutable display settings; never change parsing or process-wide locale."""

from dataclasses import dataclass
from datetime import UTC, date, datetime
from functools import lru_cache
from typing import Literal
from unicodedata import category

from babel import Locale, UnknownLocaleError
from babel.dates import PATTERN_CHARS, DateTimeFormat, parse_pattern, tokenize_pattern
from langcodes import Language, standardize_tag
from langcodes.tag_parser import LanguageTagError

from .model import ValidationError


def _apply_pattern(pattern: str, value: date, locale: Locale | str) -> str:
    formatter = DateTimeFormat(value, locale)
    parts: list[str] = []
    for kind, token in tokenize_pattern(pattern):
        if kind == "chars":
            assert isinstance(token, str)
            parts.append(token)
        else:
            assert isinstance(token, tuple)
            char, count = token
            if char == "S":
                if not isinstance(value, datetime):
                    raise ValueError("fractional seconds require datetime")
                # Babel 2.x rounds through float; LDML requires exact truncation.
                rendered = f"{value.microsecond:06d}"[:count].ljust(count, "0")
            elif char == "u":
                # Extended years never use the two-digit abbreviation of yy/YY.
                rendered = f"{value.year:0{count}d}"
            else:
                rendered = formatter[char * count]
            if rendered is None:
                raise ValueError("unsupported LDML field")
            parts.append(str(rendered))
    return "".join(parts)


def _check_pattern(pattern: str) -> None:
    quoted = False
    i = 0
    while i < len(pattern):
        char = pattern[i]
        if char == "'":
            if i + 1 < len(pattern) and pattern[i + 1] == "'":
                i += 2
                continue
            quoted = not quoted
        elif (
            not quoted
            and char.isascii()
            and char.isalpha()
            and char not in PATTERN_CHARS
        ):
            raise ValueError("literal ASCII letters must be quoted")
        i += 1
    if quoted:
        raise ValueError("unclosed quoted literal")
    parse_pattern(pattern)


def language_tag(value: str) -> str:
    if not isinstance(value, str) or not value or len(value) > 100:
        raise ValidationError("language: expected a language tag up to 100 characters")
    try:
        return standardize_tag(value)
    except (ValueError, LanguageTagError) as exc:
        raise ValidationError("language: invalid language tag") from exc


@lru_cache(maxsize=128)
def date_locale(tag: str) -> Locale:
    language = Language.get(language_tag(tag))
    # Unicode extensions/private-use subtags are metadata, not Babel options.
    parts = [language.language or "und", language.script, language.territory]
    parts.extend(language.variants or [])
    try:
        return Locale.parse("-".join(p for p in parts if p), sep="-")
    except (ValueError, UnknownLocaleError) as exc:
        raise ValidationError(
            "formatting.locale: no date locale data for language"
        ) from exc


def empty_label(language: str) -> str:
    return {"es": "Sin datos", "ru": "Нет данных"}.get(
        language.split("-")[0], "No data"
    )


@dataclass(frozen=True)
class Formatting:
    decimal: Literal[".", ","] = "."
    group: Literal[",", ".", "'", "space", "none"] = ","
    number_decimals: int = 2
    percent_decimals: int = 1
    currency_decimals: int = 2
    date_format: str | None = None
    datetime_format: str | None = None
    locale: str | None = None

    def __post_init__(self) -> None:
        if self.decimal not in (".", ","):
            raise ValidationError("formatting.decimal: expected dot or comma")
        if (
            self.group not in (",", ".", "'", "space", "none")
            or self.group == self.decimal
        ):
            raise ValidationError(
                "formatting.group: invalid or equal to decimal separator"
            )
        for name in ("number_decimals", "percent_decimals", "currency_decimals"):
            value = getattr(self, name)
            if (
                isinstance(value, bool)
                or not isinstance(value, int)
                or not 0 <= value <= 6
            ):
                raise ValidationError(
                    f"formatting.{name}: expected integer from 0 to 6"
                )
        if self.locale is not None:
            try:
                object.__setattr__(self, "locale", language_tag(self.locale))
            except ValidationError as exc:
                raise ValidationError(
                    "formatting.locale: invalid language tag"
                ) from exc
        for name in ("date_format", "datetime_format"):
            pattern = getattr(self, name)
            if pattern is not None:
                if not isinstance(pattern, str) or not 1 <= len(pattern) <= 200:
                    raise ValidationError(
                        f"formatting.{name}: expected pattern of 1..200 characters"
                    )
                if any(
                    category(char) == "Cc" and char not in "\n\r\t" for char in pattern
                ):
                    raise ValidationError(
                        f"formatting.{name}: unsupported control character"
                    )
                try:
                    _check_pattern(pattern)
                    sample = datetime(2026, 11, 4, 13, 25, 36, 123456, tzinfo=UTC)
                    _apply_pattern(
                        pattern,
                        sample.date() if name == "date_format" else sample,
                        "en",
                    )
                except (
                    ValueError,
                    KeyError,
                    AttributeError,
                    NotImplementedError,
                ) as exc:
                    raise ValidationError(
                        f"formatting.{name}: invalid LDML pattern for value type"
                    ) from exc

    @property
    def group_character(self) -> str:
        return {"space": "\u00a0", "none": ""}.get(self.group, self.group)

    def _pattern_value(
        self, pattern: str, value: date, language: str, field: str
    ) -> str:
        try:
            return _apply_pattern(pattern, value, date_locale(self.locale or language))
        except (ValueError, LookupError, AttributeError, NotImplementedError) as exc:
            raise ValidationError(
                f"formatting.{field}: cannot format value for date locale"
            ) from exc

    def dates(self, value: date, *, date_only: bool, language: str) -> str:
        if isinstance(value, datetime):
            if value.utcoffset() is None:
                raise ValidationError("value: naive datetime is unsupported")
            value = value.astimezone(UTC)
            if date_only:
                return self.dates(value.date(), date_only=True, language=language)
            if self.datetime_format is not None:
                return self._pattern_value(
                    self.datetime_format, value, language, "datetime_format"
                )
            if self.date_format is not None:
                return (
                    self.dates(value.date(), date_only=True, language=language)
                    + " "
                    + value.timetz().isoformat()
                )
            return value.isoformat()
        if self.date_format is None:
            return value.isoformat()
        return self._pattern_value(self.date_format, value, language, "date_format")
