from datetime import date, timedelta

from django.contrib.auth import get_user_model
from django.test import TestCase
from django.urls import reverse

from .models import PomodoroSession


class PomodoroTests(TestCase):
    def setUp(self):
        self.user = get_user_model().objects.create_user(username='pom', email='pom@example.com', password='TestPass123')

    def test_start_and_stop_session(self):
        self.client.login(username='pom', password='TestPass123')
        start_url = reverse('pomodoro:start_session')
        resp = self.client.post(start_url, {'mode': 'pomodoro'})
        self.assertEqual(resp.status_code, 200)
        data = resp.json()
        sid = data['id']
        sess = PomodoroSession.objects.get(id=sid)
        self.assertIsNotNone(sess)

        stop_url = reverse('pomodoro:stop_session')
        resp2 = self.client.post(stop_url, {'id': sid})
        self.assertEqual(resp2.status_code, 200)
        sess.refresh_from_db()
        self.assertTrue(sess.completed)

    def test_daily_totals_endpoint(self):
        self.client.login(username='pom', password='TestPass123')
        # create past sessions
        PomodoroSession.objects.create(owner=self.user, mode='pomodoro', duration=1500, interruptions=0, completed=True)
        url = reverse('pomodoro:daily_totals')
        resp = self.client.get(url)
        self.assertEqual(resp.status_code, 200)
        data = resp.json()
        self.assertIn('total_seconds', data)
