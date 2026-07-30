from __future__ import annotations

from decimal import Decimal

from django.conf import settings
from django.core.exceptions import ValidationError
from django.db import models
from django.utils import timezone

from apps.core.validators import validate_non_negative, validate_positive


class BudgetHistory(models.Model):
    INITIAL_BUDGET = Decimal("12000")
    DAILY_FAILURES = {
        1: Decimal("100"),
        2: Decimal("200"),
        3: Decimal("400"),
        4: Decimal("800"),
    }
    class ChangeType(models.TextChoices):
        INITIAL = "initial", "Initial"
        DEDUCTION = "deduction", "Deduction"
        RESET = "reset", "Reset"
        ADJUSTMENT = "adjustment", "Adjustment"

    owner = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="budget_history")
    amount = models.DecimalField(max_digits=10, decimal_places=2, validators=[validate_non_negative])
    change_type = models.CharField(max_length=20, choices=ChangeType.choices, default=ChangeType.INITIAL)
    reason = models.CharField(max_length=220, blank=True)
    created_at = models.DateTimeField(default=timezone.now)
    remaining_budget = models.DecimalField(max_digits=10, decimal_places=2, default=0, validators=[validate_non_negative])

    class Meta:
        ordering = ["-created_at"]
        indexes = [
            models.Index(fields=["owner", "created_at"]),
        ]

    def clean(self) -> None:
        if self.amount < 0:
            raise ValidationError({"amount": "Budget amount cannot be negative."})

    def save(self, *args, **kwargs):
        self.full_clean()
        return super().save(*args, **kwargs)

    def __str__(self) -> str:
        return f"{self.change_type} - {self.amount}"

    @classmethod
    def get_penalty_for_failure(cls, failure_count: int) -> Decimal:
        if failure_count <= 0:
            return Decimal("0")
        if failure_count in cls.DAILY_FAILURES:
            return cls.DAILY_FAILURES[failure_count]
        return cls.DAILY_FAILURES[4] * (Decimal(2) ** Decimal(failure_count - 4))

    @classmethod
    def get_or_create_initial_entry(cls, owner):
        existing = cls.objects.filter(owner=owner, change_type=cls.ChangeType.INITIAL).order_by("-created_at").first()
        if existing:
            return existing

        entry = cls.objects.create(
            owner=owner,
            amount=cls.INITIAL_BUDGET,
            change_type=cls.ChangeType.INITIAL,
            reason="Initial budget",
            remaining_budget=cls.INITIAL_BUDGET,
        )
        return entry

    @classmethod
    def apply_penalty(cls, owner, failure_count: int, reason: str = "Daily failure"):
        initial_entry = cls.get_or_create_initial_entry(owner)
        last_entry = cls.objects.filter(owner=owner).order_by("-created_at").first()
        current_budget = last_entry.remaining_budget if last_entry else initial_entry.remaining_budget
        penalty_amount = cls.get_penalty_for_failure(failure_count)
        new_budget = max(current_budget - penalty_amount, Decimal("0"))

        cls.objects.create(
            owner=owner,
            amount=penalty_amount,
            change_type=cls.ChangeType.DEDUCTION,
            reason=reason,
            remaining_budget=new_budget,
        )
        return new_budget, penalty_amount

    @classmethod
    def reset_budget(cls, owner, reason: str = "Successful day"):
        initial_entry = cls.get_or_create_initial_entry(owner)
        cls.objects.create(
            owner=owner,
            amount=initial_entry.amount,
            change_type=cls.ChangeType.RESET,
            reason=reason,
            remaining_budget=initial_entry.amount,
        )
        return initial_entry.amount
