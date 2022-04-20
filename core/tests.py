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
            (
                parse_datetime("2022-04-19T15:00:00Z"),
                parse_datetime("2022-04-19T16:30:00Z"),
            ),
        )
        start, end = next(instances)
        self.assertTupleEqual(
            (start, end),
            (
                parse_datetime("2022-04-20T15:00:00Z"),
                parse_datetime("2022-04-20T16:30:00Z"),
            ),
        )
        start, end = next(instances)
        self.assertTupleEqual(
            (start, end),
            (
                parse_datetime("2022-04-21T15:00:00Z"),
                parse_datetime("2022-04-21T16:30:00Z"),
            ),
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
            (
                parse_datetime("2022-04-19T15:00:00Z"),
                parse_datetime("2022-04-19T16:30:00Z"),
            ),
        )


class CreateViewsTests(TestCase):
    def test_create_user(self):
        response = self.client.post(
            "/api/create/user",
            content_type="application/json",
            data={"name": "John Doe", "email": "johndoe@gmail.com"},
        )
        self.assertEqual(200, response.status_code)
        user = User.objects.get(email="johndoe@gmail.com")
        self.assertEqual("John Doe", user.name)

        # already exist
        response = self.client.post(
            "/api/create/user",
            content_type="application/json",
            data={"name": "John Doe", "email": "johndoe@gmail.com"},
        )
        self.assertEqual(400, response.status_code)

    def test_create_event(self):
        event_descr = {
            "title": "Example event",
            "start": "2022-04-20T08:00:00",
            "end": "2022-04-20T10:00:00",
            "owner_email": "johndoe@gmail.com",
            "is_recurring": "True",
            "repeats": ["daily"],
            "invited_emails": ["guest@gmail.com"],
        }

        # no users exist -> error while creating
        response = self.client.post(
            "/api/create/event",
            content_type="application/json",
            data=event_descr,
        )
        self.assertEqual(400, response.status_code)

        # create users and repeat
        User.objects.create(name="John Doe", email="johndoe@gmail.com")
        User.objects.create(name="Guest", email="guest@gmail.com")
        response = self.client.post(
            "/api/create/event",
            content_type="application/json",
            data=event_descr,
        )
        self.assertEqual(200, response.status_code)

        # check that event is now created in DB
        events = Event.objects.all()
        self.assertTrue(len(events) > 0)
        event = events[0]
        self.assertEqual("Example event", event.title)


class InfoViewsTests(TestCase):
    def test_info_user(self):
        response = self.client.get("/api/info/user/1")
        self.assertEqual(400, response.status_code)

        user = User.objects.create(name="John Doe", email="johndoe@gmail.com")
        response = self.client.get(f"/api/info/user/{user.id}")
        self.assertEqual(200, response.status_code)
        self.assertDictEqual({"user": "John Doe (johndoe@gmail.com)"}, response.json())

    def test_info_event(self):
        response = self.client.get("/api/info/user/1/event/1")
        self.assertEqual(400, response.status_code)

        user = User.objects.create(name="John Doe", email="johndoe@gmail.com")
        event = Event.objects.create(
            title="Event example",
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

        response = self.client.get(f"/api/info/user/{user.id}/event/{event.id}")
        self.assertEqual(200, response.status_code)

        self.assertDictEqual(
            {
                "title": "Event example",
                "description": "",
                "start": "2022-04-19T15:00:00Z",
                "end": "2022-04-19T16:30:00Z",
                "owner": "John Doe (johndoe@gmail.com)",
                "is_recurring": True,
                "is_private": False,
                "repeats": [
                    "Repeat start=2022-04-19 15:00:00+00:00 with interval=1 day, 0:00:00"
                ],
                "invites": {
                    "PENDING": ["Guest (guest@gmail.com)"],
                    "ACCEPTED": [],
                    "REJECTED": [],
                },
            },
            response.json(),
        )

    def test_info_user_invites(self):
        response = self.client.get("/api/info/user/1/invites")
        self.assertEqual(400, response.status_code)

        user = User.objects.create(name="John Doe", email="johndoe@gmail.com")
        event = Event.objects.create(
            title="Event example",
            start=parse_datetime("2022-04-19T15:00:00Z"),
            end=parse_datetime("2022-04-19T16:30:00Z"),
            owner_id=user.id,
        )
        guest_user = User.objects.create(name="Guest", email="guest@gmail.com")
        invite = Invite.objects.create(
            user_id=guest_user.id,
            event_id=event.id,
        )

        response = self.client.get(f"/api/info/user/{guest_user.id}/invites")
        self.assertEqual(200, response.status_code)
        self.assertDictEqual(
            {
                "invites": [
                    f"id={invite.id} user=Guest (guest@gmail.com) event=Event example status=PE"
                ],
            },
            response.json(),
        )

        response = self.client.get(
            f"/api/info/user/{guest_user.id}/invites?status=ACCEPTED"
        )
        self.assertEqual(200, response.status_code)
        self.assertDictEqual({"invites": []}, response.json())

    def test_info_user_events(self):
        response = self.client.get("/api/info/user/1/events")
        self.assertEqual(400, response.status_code)

        user = User.objects.create(name="John Doe", email="johndoe@gmail.com")
        event = Event.objects.create(
            title="Event example",
            start=parse_datetime("2022-04-19T15:00:00Z"),
            end=parse_datetime("2022-04-19T16:30:00Z"),
            owner_id=user.id,
            is_recurring=True,
        )
        rrule = RRule.daily(event_id=event.id, start=event.start)
        rrule.save()

        response = self.client.get(
            f"/api/info/user/{user.id}/events?from=2022-04-15T00:00:00&till=2022-04-24T00:00:00"
        )
        self.assertEqual(200, response.status_code)
        self.assertDictEqual(
            {
                "events": [
                    "Start=2022-04-19 15:00:00+00:00, End=2022-04-19 16:30:00+00:00, Title=Event example",
                    "Start=2022-04-20 15:00:00+00:00, End=2022-04-20 16:30:00+00:00, Title=Event example",
                    "Start=2022-04-21 15:00:00+00:00, End=2022-04-21 16:30:00+00:00, Title=Event example",
                    "Start=2022-04-22 15:00:00+00:00, End=2022-04-22 16:30:00+00:00, Title=Event example",
                    "Start=2022-04-23 15:00:00+00:00, End=2022-04-23 16:30:00+00:00, Title=Event example",
                ]
            },
            response.json(),
        )


class UpdateViewsTests(TestCase):
    def test_update_invite(self):
        response = self.client.put("/api/update/invite/1")
        self.assertEqual(400, response.status_code)

        user = User.objects.create(name="John Doe", email="johndoe@gmail.com")
        event = Event.objects.create(
            title="Event example",
            start=parse_datetime("2022-04-19T15:00:00Z"),
            end=parse_datetime("2022-04-19T16:30:00Z"),
            owner_id=user.id,
        )
        invite = Invite.objects.create(event_id=event.id, user_id=user.id)

        self.assertEqual(Invite.Status.PENDING, invite.status)
        self.client.put(f"/api/update/invite/{invite.id}?status=ACCEPTED")
        invite.refresh_from_db()
        self.assertEqual(Invite.Status.ACCEPTED, invite.status)


class TimetableViewsTests(TestCase):
    def test_free_time_slot(self):
        owner = User.objects.create(name="John Doe", email="johndoe@gmail.com")
        guest = User.objects.create(name="Guest", email="guest@gmail.com")

        event = Event.objects.create(
            title="Event example",
            start=parse_datetime("2022-04-19T15:00:00Z"),
            end=parse_datetime("2022-04-19T16:30:00Z"),
            owner_id=owner.id,
        )
        Invite.objects.create(
            user_id=guest.id,
            event_id=event.id,
            status=Invite.Status.ACCEPTED,
        )

        response = self.client.get(
            f"/api/timetable/free_time_slot?user_ids={owner.id},{guest.id}&duration=30:00"
        )
        self.assertEqual(200, response.status_code)
        self.assertDictEqual(
            {"start": "2022-04-19T16:30:00Z", "end": "2022-04-19T17:00:00Z"},
            response.json(),
        )
