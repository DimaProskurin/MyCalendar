import datetime

from django.db import models
from django.utils.translation import gettext_lazy as _
from django.contrib.auth.models import User as DjangoUser

from core.common.min_generator import min_stream


class User(DjangoUser):
    class Meta:
        proxy = True

    @property
    def name(self):
        if self.last_name:
            return f"{self.first_name} {self.last_name}"
        else:
            return self.first_name

    def get_owned_events(self):
        return Event.objects.filter(owner_id=self.id)

    def get_all_invites(self):
        return Invite.objects.filter(user_id=self.id)

    def get_invites_by_status(self, status):
        all_invites = self.get_all_invites()
        return [invite for invite in all_invites if invite.status == status]

    def get_my_events(self):
        accepted_invites = self.get_invites_by_status(status=Invite.Status.ACCEPTED)
        accepted_events = [invite.get_event() for invite in accepted_invites]
        return list(self.get_owned_events()) + accepted_events

    def get_events_instances_by_time_period(self, from_time, till_time):
        result = []
        events = self.get_my_events()
        for event in events:
            for start, end in event.get_instances():
                if start >= from_time and end <= till_time:
                    result.append(((start, end), event))
                if start > till_time:
                    break
        return result

    def get_occupied_time_slots(self):
        events = self.get_my_events()
        yield from min_stream([event.get_instances() for event in events])

    def __str__(self):
        return f"{self.name} ({self.email})"


class Calendar(models.Model):
    title = models.CharField(max_length=100)
    description = models.CharField(max_length=1024, blank=True)
    owner = models.ForeignKey(User, on_delete=models.CASCADE)

    def get_owner(self):
        return User.objects.filter(id=self.owner.id)[0]

    def __str__(self):
        return self.title


class CalendarPermission(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    calendar = models.ForeignKey(Calendar, on_delete=models.CASCADE)

    class Action(models.TextChoices):
        READ = "RE", _("Read")
        EDIT = "ED", _("Edit")

    action = models.CharField(
        max_length=2,
        choices=Action.choices,
        default=Action.READ,
    )

    def __str__(self):
        return f"{self.user} {self.calendar} {self.action}"


class Event(models.Model):
    title = models.CharField(max_length=100)
    description = models.CharField(max_length=1024, blank=True)
    start = models.DateTimeField()
    end = models.DateTimeField()
    owner = models.ForeignKey(User, on_delete=models.CASCADE)
    is_recurring = models.BooleanField(default=False)
    is_private = models.BooleanField(default=False)
    calendars = models.ManyToManyField(Calendar)

    def get_owner(self):
        return User.objects.filter(id=self.owner.id)[0]

    def get_related_user_ids(self):
        owner_id = self.owner_id
        invited_user_ids = [
            invite.user_id for invite in Invite.objects.filter(event_id=self.id)
        ]
        return [owner_id] + invited_user_ids

    def get_rrules(self):
        return RRule.objects.filter(event_id=self.id)

    def get_instances(self):
        if not self.is_recurring:
            yield self.start, self.end
        else:
            rrules = self.get_rrules()
            yield from min_stream([rrule.get_repeats() for rrule in rrules])

    def deep_description(self):
        description = {
            "title": self.title,
            "description": self.description,
            "start": self.start,
            "end": self.end,
            "owner": str(self.get_owner()),
            "is_recurring": self.is_recurring,
            "is_private": self.is_private,
        }
        if self.is_recurring:
            rrules = self.get_rrules()
            description["repeats"] = [str(rrule) for rrule in rrules]

        # add invites to description
        invites = Invite.objects.filter(event_id=self.id)
        pending_users = [
            str(invite.get_user())
            for invite in invites
            if invite.status == Invite.Status.PENDING
        ]
        accepted_users = [
            str(invite.get_user())
            for invite in invites
            if invite.status == Invite.Status.ACCEPTED
        ]
        rejected_users = [
            str(invite.get_user())
            for invite in invites
            if invite.status == Invite.Status.REJECTED
        ]
        description["invites"] = {
            "PENDING": pending_users,
            "ACCEPTED": accepted_users,
            "REJECTED": rejected_users,
        }

        return description

    def hidden_description(self):
        description = {
            "owner": str(self.get_owner()),
            "start": self.start,
            "end": self.end,
            "is_recurring": self.is_recurring,
            "is_private": self.is_private,
        }
        if self.is_recurring:
            rrules = self.get_rrules()
            description["repeats"] = [str(rrule) for rrule in rrules]
        return description

    def __str__(self):
        return self.title


class RRule(models.Model):
    event = models.ForeignKey(Event, on_delete=models.CASCADE)
    start = models.DateTimeField()
    interval = models.DurationField()
    end = models.DateTimeField(default=None, blank=True, null=True)

    def get_event(self):
        return Event.objects.filter(id=self.event.id)[0]

    def get_repeats(self):
        event = self.get_event()
        event_duration = event.end - event.start
        start = self.start
        while (self.end is None) or (start + event_duration <= self.end):
            yield start, start + event_duration
            start += self.interval

    def __str__(self):
        return f"Repeat start={self.start} with interval={self.interval}"

    @classmethod
    def daily(cls, event_id, start, end=None):
        return cls(
            event_id=event_id, start=start, interval=datetime.timedelta(days=1), end=end
        )

    @classmethod
    def weekly(cls, event_id, start, end=None):
        return cls(
            event_id=event_id,
            start=start,
            interval=datetime.timedelta(weeks=1),
            end=end,
        )

    @classmethod
    def monthly(cls, event_id, start, end=None):
        # WARNING: this is made for "testing task" to show how to develop such methods
        # This is not very CORRECT implementation due to months have different number of days
        # Best way to use side-libraries e.g. https://github.com/dateutil/dateutil/
        # Method https://dateutil.readthedocs.io/en/stable/relativedelta.html
        return cls(
            event_id=event_id,
            start=start,
            interval=datetime.timedelta(days=30),
            end=end,
        )

    @classmethod
    def yearly(cls, event_id, start, end=None):
        # WARNING: look at "monthly" method comment
        return cls(
            event_id=event_id,
            start=start,
            interval=datetime.timedelta(days=365),
            end=end,
        )


class Invite(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    event = models.ForeignKey(Event, on_delete=models.CASCADE)

    class Status(models.TextChoices):
        PENDING = "PE", _("Pending")
        ACCEPTED = "AC", _("Accepted")
        REJECTED = "RE", _("Rejected")

    status = models.CharField(
        max_length=2,
        choices=Status.choices,
        default=Status.PENDING,
    )

    def get_event(self):
        return Event.objects.filter(id=self.event_id)[0]

    def get_user(self):
        return User.objects.filter(id=self.user_id)[0]

    def __str__(self):
        return f"id={self.id} user={self.user} event={self.event} status={self.status}"
