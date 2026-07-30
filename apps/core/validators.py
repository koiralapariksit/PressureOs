from django.core.exceptions import ValidationError


def validate_non_negative(value: float) -> None:
    if value < 0:
        raise ValidationError("Value cannot be negative.")


def validate_percentage(value: float) -> None:
    if not 0 <= value <= 100:
        raise ValidationError("Value must be between 0 and 100 inclusive.")


def validate_positive(value: float) -> None:
    if value <= 0:
        raise ValidationError("Value must be greater than zero.")
