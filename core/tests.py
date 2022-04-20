from django.test import TestCase
from django.utils.dateparse import parse_datetime

from core.models import Event, Invite, RRule, User


class ModelTests(TestCase):
    def setUp(self):
        user = User.objects.create(name="John Doe", email="johndoe@gmail.com")
        event = Event.objects.create(
            title="Test title",
            start=parse_datetime("2022-04-19T15:00:00Z"),
            end=parse_datetime("2022-04-19T16:30:00Z"),
            owner_id=user.id,
            is_recurring=True,
        )
        rrule = RRule.daily(
            event_id=event.id,
            start=event.start,
        )
        rrule.save()

        guest_user = User.objects.create(name="Guest", email="guest@gmail.com")
        Invite.objects.create(
            user_id=guest_user.id,
            event_id=event.id,
        )

    def test_user_creation(self):
        user = User.objects.get(email="johndoe@gmail.com")
        self.assertEqual("John Doe", user.name)

    def test_event_repeats(self):
        event = Event.objects.all()[0]
        instances = event.get_instances()
        start, end = next(instances)
        self.assertTupleEqual(
            (start, end),
            (parse_datetime("2022-04-19T15:00:00Z"), parse_datetime("2022-04-19T16:30:00Z")),
        )
        start, end = next(instances)
        self.assertTupleEqual(
            (start, end),
            (parse_datetime("2022-04-20T15:00:00Z"), parse_datetime("2022-04-20T16:30:00Z")),
        )
        start, end = next(instances)
        self.assertTupleEqual(
            (start, end),
            (parse_datetime("2022-04-21T15:00:00Z"), parse_datetime("2022-04-21T16:30:00Z")),
        )

    def test_pending_invite(self):
        guest_user = User.objects.filter(email="guest@gmail.com")[0]
        pending = guest_user.get_invites_by_status(Invite.Status.PENDING)
        self.assertTrue(len(pending) == 1)

    def test_user_events_by_period(self):
        # firstly when invite hasn't been accepted yet
        guest_user = User.objects.filter(email="guest@gmail.com")[0]
        instances = guest_user.get_events_instances_by_time_period(
            from_time=parse_datetime("2022-04-19T14:00:00Z"),
            till_time=parse_datetime("2022-04-19T18:00:00Z"),
        )
        self.assertTrue(len(instances) == 0)

        # accept invite and try again
        pending = guest_user.get_invites_by_status(Invite.Status.PENDING)
        invite = pending[0]
        invite.status = Invite.Status.ACCEPTED
        invite.save()
        instances = guest_user.get_events_instances_by_time_period(
            from_time=parse_datetime("2022-04-19T14:00:00Z"),
            till_time=parse_datetime("2022-04-19T18:00:00Z"),
        )
        self.assertTrue(len(instances) == 1)

        # try empty period
        instances = guest_user.get_events_instances_by_time_period(
            from_time=parse_datetime("2022-04-19T17:00:00Z"),
            till_time=parse_datetime("2022-04-19T18:00:00Z"),
        )
        self.assertTrue(len(instances) == 0)

    def test_user_occupied_time_slots(self):
        user = User.objects.get(email="johndoe@gmail.com")
        slots = user.get_occupied_time_slots()
        start, end = next(slots)
        self.assertTupleEqual(
            (start, end),
            (parse_datetime("2022-04-19T15:00:00Z"), parse_datetime("2022-04-19T16:30:00Z")),
        )
