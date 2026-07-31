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

    def test_invalid_login_shows_an_error_message(self):
        response = self.client.post(
            reverse('accounts:login'),
            {'username': 'missing', 'password': 'wrong-password'},
        )

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'The username or password you entered is incorrect')

    def test_logout_accepts_get_and_redirects_home(self):
        user = get_user_model().objects.create_user(username='logoutdemo', password='StrongPass123!')
        self.client.force_login(user)

        response = self.client.get(reverse('accounts:logout'))

        self.assertEqual(response.status_code, 302)
        self.assertRedirects(response, reverse('core:home'))
