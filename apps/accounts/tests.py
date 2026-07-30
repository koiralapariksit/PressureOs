from django.test import TestCase
from django.contrib.auth import get_user_model
from django.urls import reverse


class AuthenticationFlowTests(TestCase):
    def test_registration_and_login_work(self):
        register_response = self.client.post(
            reverse('accounts:register'),
            {
                'username': 'opsdemo',
                'email': 'opsdemo@example.com',
                'first_name': 'Ops',
                'last_name': 'Demo',
                'password1': 'StrongPass123!',
                'password2': 'StrongPass123!',
            },
        )

        self.assertEqual(register_response.status_code, 302)
        user = get_user_model().objects.get(username='opsdemo')
        self.assertTrue(user.check_password('StrongPass123!'))

        login_response = self.client.post(
            reverse('accounts:login'),
            {'username': 'opsdemo', 'password': 'StrongPass123!'},
        )

        self.assertEqual(login_response.status_code, 302)
