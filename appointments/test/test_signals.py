# apps/appointments/tests/test_signals.py
"""
Tests for apps/appointments/signals.py

Run:  python manage.py test apps.appointments.tests.test_signals -v 2

Assumptions about the model layer (adjust if yours differ):
  • Clinic.appointment_duration  (int)
  • Clinic.doctors               (M2M to DoctorProfile, reverse = doctor.clinics)
  • QueueEntry.wait_time_minutes (field or property)
  • QueueEntry.queue_position    (int, nullable or 0-default)
"""
from datetime import date, time

from django.core.exceptions import ValidationError
from django.test import TestCase

# ── with these two ─────────────────────────────
from django.contrib.auth import get_user_model
from accounts.models import DoctorProfile, PatientProfile, Profile
from django.contrib.auth.models import User
from appointments.models import Appointment, Clinic, QueueEntry


# =========================================================
# Base fixtures
# =========================================================
class SignalTestBase(TestCase):

    @classmethod
    def setUpTestData(cls):
        # Patient
        u = User.objects.create_user(
            username='patient1', password='x', email='p1@example.com',
        )
        p = Profile.objects.create(user=u, role='patient')
        cls.patient = PatientProfile.objects.create(profile=p)

        # Doctor
        du = User.objects.create_user(
            username='doctor1', password='x', email='d1@example.com',
        )
        dp = Profile.objects.create(user=du, role='doctor')
        cls.doctor = DoctorProfile.objects.create(profile=dp, specialty='General')

        # Clinic linked to the doctor (reverse M2M = doctor.clinics)
        cls.clinic = Clinic.objects.create(name='Test Clinic', appointment_duration=30)
        cls.clinic.doctors.add(cls.doctor)

    # ── helpers ────────────────────────────────────────
    @classmethod
    def make_patient(cls, username):
        u = User.objects.create_user(username=username, password='x')
        p = Profile.objects.create(user=u, role='patient')
        return PatientProfile.objects.create(profile=p)

    def appt(self, **overrides):
        data = {
            'patient_profile': self.patient,
            'appointment_date': date(2026, 6, 1),
            'start_time': time(9, 0),
            'end_time': time(9, 30),
            'status': 'scheduled',
        }
        data.update(overrides)
        return Appointment.objects.create(**data)

    def queue_entry(self, **overrides):
        data = {
            'patient_profile': self.patient,
            'doctor_profile': self.doctor,
            'status': 'waiting',
            'queue_position': 0,
        }
        data.update(overrides)
        return QueueEntry.objects.create(**data)


# =========================================================
# validate_appointment_time
# =========================================================
class ValidateAppointmentTimeTests(SignalTestBase):

    def test_valid_times_accepted(self):
        self.assertIsNotNone(self.appt().pk)

    def test_start_after_end_rejected(self):
        with self.assertRaises(ValidationError):
            self.appt(start_time=time(10, 0), end_time=time(9, 0))

    def test_start_equal_to_end_rejected(self):
        with self.assertRaises(ValidationError):
            self.appt(start_time=time(9, 0), end_time=time(9, 0))

    def test_status_only_update_skips_validation(self):
        """Legacy bad row must still be updatable if time fields untouched."""
        a = self.appt()
        # Corrupt times directly in DB, bypassing signals
        Appointment.objects.filter(pk=a.pk).update(
            start_time=time(10, 0), end_time=time(9, 0),
        )
        a.refresh_from_db()

        a.status = 'confirmed'
        a.save(update_fields=['status'])
        a.refresh_from_db()
        self.assertEqual(a.status, 'confirmed')

    def test_time_update_does_validate(self):
        a = self.appt()
        a.start_time = time(11, 0)
        a.end_time = time(10, 0)
        with self.assertRaises(ValidationError):
            a.save(update_fields=['start_time', 'end_time'])


# =========================================================
# set_end_time_if_not_provided
# =========================================================
class SetEndTimeTests(SignalTestBase):

    def test_end_time_computed_from_clinic_duration(self):
        a = Appointment.objects.create(
            patient_profile=self.patient,
            clinic=self.clinic,                 # appointment_duration=30
            appointment_date=date(2026, 6, 1),
            start_time=time(9, 0),
            status='scheduled',
        )
        a.refresh_from_db()
        self.assertEqual(a.end_time, time(9, 30))

    def test_end_time_defaults_to_30_without_clinic(self):
        a = Appointment.objects.create(
            patient_profile=self.patient,
            appointment_date=date(2026, 6, 1),
            start_time=time(14, 0),
            status='scheduled',
        )
        a.refresh_from_db()
        self.assertEqual(a.end_time, time(14, 30))

    def test_existing_end_time_preserved(self):
        a = self.appt(end_time=time(10, 0))     # 60 min, not 30
        a.refresh_from_db()
        self.assertEqual(a.end_time, time(10, 0))

    def test_skips_when_end_time_not_in_update_fields(self):
        a = self.appt()
        Appointment.objects.filter(pk=a.pk).update(end_time=None)
        a.refresh_from_db()

        a.status = 'confirmed'
        a.save(update_fields=['status'])
        a.refresh_from_db()
        self.assertIsNone(a.end_time)


# =========================================================
# track_appointment_previous_state
# =========================================================
class TrackAppointmentStateTests(SignalTestBase):

    def test_new_instance_gets_none_markers(self):
        a = Appointment(
            patient_profile=self.patient,
            appointment_date=date(2026, 6, 1),
            start_time=time(9, 0),
            end_time=time(9, 30),
            status='scheduled',
        )
        a.save()
        self.assertIsNone(a._previous_status)
        self.assertIsNone(a._previous_doctor_id)

    def test_update_captures_previous_status(self):
        a = self.appt(status='scheduled')
        a.status = 'confirmed'
        a.save()
        self.assertEqual(a._previous_status, 'scheduled')

    def test_update_captures_previous_doctor(self):
        a = self.appt(doctor_profile=self.doctor)
        a.doctor_profile = None
        a.save()
        self.assertEqual(a._previous_doctor_id, self.doctor.id)


# =========================================================
# track_queue_previous_state
# =========================================================
class TrackQueueStateTests(SignalTestBase):

    def test_new_instance_gets_none_markers(self):
        q = QueueEntry(
            patient_profile=self.patient,
            doctor_profile=self.doctor,
            status='waiting',
            queue_position=1,
        )
        q.save()
        self.assertIsNone(q._original_queue_position)
        self.assertIsNone(q._original_status)

    def test_update_captures_previous(self):
        q = self.queue_entry()
        # Force a known position (post_save may have recalculated it)
        QueueEntry.objects.filter(pk=q.pk).update(queue_position=1)
        q.refresh_from_db()

        q.queue_position = 2
        q.status = 'in_progress'
        q.save()

        self.assertEqual(q._original_queue_position, 1)
        self.assertEqual(q._original_status, 'waiting')


# =========================================================
# update_queue_positions
# =========================================================
class UpdateQueuePositionsTests(SignalTestBase):

    @classmethod
    def setUpTestData(cls):
        super().setUpTestData()
        cls.patient2 = cls.make_patient('patient2')
        cls.patient3 = cls.make_patient('patient3')

    def test_single_entry_gets_position_1(self):
        q = self.queue_entry(status='waiting')
        q.refresh_from_db()
        self.assertEqual(q.queue_position, 1)

    def test_two_entries_get_sequential_positions(self):
        q1 = self.queue_entry(patient_profile=self.patient, status='waiting')
        q2 = self.queue_entry(patient_profile=self.patient2, status='waiting')

        q1.refresh_from_db()
        q2.refresh_from_db()
        self.assertEqual(q1.queue_position, 1)
        self.assertEqual(q2.queue_position, 2)

    def test_targeted_position_update_skips_recalc(self):
        """Saving with update_fields=['queue_position'] must not recurse."""
        q = self.queue_entry(patient_profile=self.patient, status='waiting')
        q.queue_position = 5
        q.save(update_fields=['queue_position'])
        q.refresh_from_db()
        self.assertEqual(q.queue_position, 5)

    def test_full_save_triggers_recalc(self):
        """
        A full save (update_fields=None) MUST trigger recalc.

        This is the test that catches the re-entry-guard bug:
          `update_fields = kwargs.get('update_fields') or set()` incorrectly
        treats full saves as targeted saves and skips recalculation.
        """
        q1 = self.queue_entry(patient_profile=self.patient, status='waiting')
        q2 = self.queue_entry(patient_profile=self.patient2, status='waiting')

        # Corrupt q1's position directly
        QueueEntry.objects.filter(pk=q1.pk).update(queue_position=99)

        # Full save on q2 → update_fields=None
        q2 = QueueEntry.objects.get(pk=q2.pk)
        q2.save()

        q1.refresh_from_db()
        self.assertEqual(q1.queue_position, 1)

    def test_non_waiting_entries_ignored(self):
        q1 = self.queue_entry(patient_profile=self.patient, status='waiting')
        self.queue_entry(patient_profile=self.patient2, status='in_progress')

        q1.refresh_from_db()
        self.assertEqual(q1.queue_position, 1)

    def test_no_doctor_skips_recalc(self):
        """Entry without a doctor is outside recalc scope — signal returns early."""
        q = self.queue_entry(
            patient_profile=self.patient, doctor_profile=None,
            status='waiting',
        )
        q.refresh_from_db()
        self.assertEqual(q.queue_position, 0)


# =========================================================
# create_appointment_on_admit
# =========================================================
class CreateAppointmentOnAdmitTests(SignalTestBase):

    def test_admit_creates_appointment(self):
        q = self.queue_entry(patient_profile=self.patient, status='waiting')

        q.status = 'admitted'
        q.save()

        appts = Appointment.objects.filter(
            patient_profile=self.patient,
            doctor_profile=self.doctor,
        )
        self.assertEqual(appts.count(), 1)
        a = appts.first()
        self.assertEqual(a.status, 'in_progress')
        self.assertEqual(a.type, 'physical')
        self.assertEqual(a.clinic_id, self.clinic.id)
        self.assertIn(f'Queue entry #{q.id}', a.notes)

    def test_second_save_after_admit_does_not_duplicate(self):
        q = self.queue_entry(patient_profile=self.patient, status='waiting')
        q.status = 'admitted'
        q.save()

        # Re-save the same row — no new appointment
        q.refresh_from_db()
        q.save()

        self.assertEqual(
            Appointment.objects.filter(
                notes__contains=f'Queue entry #{q.id}',
            ).count(),
            1,
        )

    def test_no_doctor_skips_creation(self):
        q = self.queue_entry(
            patient_profile=self.patient, doctor_profile=None,
            status='waiting',
        )
        q.status = 'admitted'
        q.save()

        self.assertFalse(
            Appointment.objects.filter(
                notes__contains=f'Queue entry #{q.id}',
            ).exists()
        )

    def test_existing_appointment_prevents_duplicate(self):
        q = self.queue_entry(patient_profile=self.patient, status='waiting')

        # Pre-create an appointment with the marker
        Appointment.objects.create(
            patient_profile=self.patient,
            doctor_profile=self.doctor,
            clinic=self.clinic,
            appointment_date=date(2026, 6, 1),
            start_time=time(9, 0),
            end_time=time(9, 30),
            status='in_progress',
            notes=f'Queue entry #{q.id} - pre-existing',
        )

        q.status = 'admitted'
        q.save()

        self.assertEqual(
            Appointment.objects.filter(
                notes__contains=f'Queue entry #{q.id}',
            ).count(),
            1,
        )

    def test_creation_with_admitted_status_creates_appointment(self):
        q = self.queue_entry(
            patient_profile=self.patient, status='admitted',
            doctor_profile=self.doctor, queue_position=1,
        )
        # _original_status is None on a new instance → creation path fires

        self.assertEqual(
            Appointment.objects.filter(
                notes__contains=f'Queue entry #{q.id}',
            ).count(),
            1,
        )

    def test_non_admitted_status_does_not_create(self):
        q = self.queue_entry(patient_profile=self.patient, status='waiting')
        self.assertFalse(
            Appointment.objects.filter(
                notes__contains=f'Queue entry #{q.id}',
            ).exists()
        )