from decimal import Decimal

from django.contrib.auth import get_user_model
from django.test import TestCase

from apps.budget.models import BudgetHistory


class BudgetPenaltyTests(TestCase):
    def setUp(self):
        self.user = get_user_model().objects.create_user(username="budgeter", email="budgeter@example.com", password="strong-pass")

    def test_penalty_doubles_and_resets(self):
        budget, penalty = BudgetHistory.apply_penalty(self.user, 1, reason="First miss")
        self.assertEqual(penalty, Decimal("100"))
        self.assertEqual(budget, Decimal("11900.00"))

        budget, penalty = BudgetHistory.apply_penalty(self.user, 2, reason="Second miss")
        self.assertEqual(penalty, Decimal("200"))
        self.assertEqual(budget, Decimal("11700.00"))

        budget, penalty = BudgetHistory.apply_penalty(self.user, 3, reason="Third miss")
        self.assertEqual(penalty, Decimal("400"))
        self.assertEqual(budget, Decimal("11300.00"))

        budget, penalty = BudgetHistory.apply_penalty(self.user, 4, reason="Fourth miss")
        self.assertEqual(penalty, Decimal("800"))
        self.assertEqual(budget, Decimal("10500.00"))

        budget, penalty = BudgetHistory.apply_penalty(self.user, 5, reason="Fifth miss")
        self.assertEqual(penalty, Decimal("1600"))
        self.assertEqual(budget, Decimal("8900.00"))

        reset_budget = BudgetHistory.reset_budget(self.user, reason="Successful day")
        self.assertEqual(reset_budget, Decimal("12000"))
        self.assertEqual(BudgetHistory.objects.filter(owner=self.user).count(), 7)
