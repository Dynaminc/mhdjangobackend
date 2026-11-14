# apps/appointments/simple_queue.py
"""
In-memory consultation queue.

Email side effects:
  • join()   → notifies ops + (optionally) the assigned doctor
  • admit()  → notifies ops + the admitting doctor
  • Both use plain-text emails; no template rendering.
  • Mail failures are logged and swallowed — they never block the queue.
"""
import logging
import time
from datetime import datetime

from django.conf import settings
from django.core.mail import send_mail

logger = logging.getLogger(__name__)


# Always CC'd on queue emails
QUEUE_NOTIFICATION_RECIPIENTS = [
    'info@marvellehealth.com',
    'demilademuyiwa@gmail.com',
]


class SimpleQueue:
    def __init__(self):
        self._queue = []           # List of patient IDs
        self._position_cache = {}  # Cache for quick position lookup
        self._heartbeats = {}      # Track last seen time
        self._names = {}           # Store patient names
        self._admitted = []        # Admitted history
        self._completed = []       # Completed history
        self.mh_user_id = {}       # Patient public IDs

    # =========================================================
    # Internal — email helpers
    # =========================================================
    def _recipients(self, doctor_email=None):
        """Static ops list + optional doctor, de-duplicated."""
        recipients = list(QUEUE_NOTIFICATION_RECIPIENTS)
        if doctor_email and doctor_email not in recipients:
            recipients.append(doctor_email)
        return recipients

    def _send_join_email(self, name, mh_user_id, doctor_email=None):
        """
        Plain-text email: "a patient joined the queue".
        Never raises — a mail failure must not block the join.
        """
        recipients = self._recipients(doctor_email)
        display_name = name or '(name not provided)'
        display_id = mh_user_id or '(id not provided)'

        subject = f"Queue: new patient joined — {display_name}"
        body = (
            "A new patient has joined the consultation queue.\n"
            "\n"
            f"Name:       {display_name}\n"
            f"Patient ID: {display_id}\n"
            f"Joined at:  {datetime.now().isoformat(timespec='seconds')}\n"
            f"Queue size: {len(self._queue)}\n"
        )

        try:
            send_mail(
                subject=subject,
                message=body,
                from_email=settings.DEFAULT_FROM_EMAIL,
                recipient_list=recipients,
                fail_silently=True,
            )
        except Exception:
            logger.exception(
                'Failed to send queue-join email '
                '(recipients=%s, patient=%s)',
                recipients, mh_user_id,
            )

    def _send_admit_email(self, name, mh_user_id,
                          doctor_email=None, doctor_name=None):
        """
        Plain-text email: "this patient has been admitted".
        Never raises.
        """
        recipients = self._recipients(doctor_email)
        display_name = name or '(name not provided)'
        display_id = mh_user_id or '(id not provided)'
        doctor_label = f"Dr. {doctor_name}" if doctor_name else "the doctor"

        subject = f"Queue: {display_name} admitted by {doctor_label}"
        body = (
            f"{display_name} has been admitted from the queue "
            f"by {doctor_label}.\n"
            "\n"
            f"Name:       {display_name}\n"
            f"Patient ID: {display_id}\n"
            f"Admitted at:{datetime.now().isoformat(timespec='seconds')}\n"
        )

        try:
            send_mail(
                subject=subject,
                message=body,
                from_email=settings.DEFAULT_FROM_EMAIL,
                recipient_list=recipients,
                fail_silently=True,
            )
        except Exception:
            logger.exception(
                'Failed to send queue-admit email '
                '(recipients=%s, patient=%s)',
                recipients, mh_user_id,
            )

    # =========================================================
    # Queue operations
    # =========================================================
    def join(self, patient_id, mh_user_id, name="", doctor_email=None):
        """
        Add patient to queue.

        doctor_email — optional. When the patient has an open appointment
        with a specific doctor, pass that doctor's email so they are CC'd
        on the join notification.
        """
        if patient_id in self._queue:
            return {"error": "Already in queue"}

        self._queue.append(patient_id)
        position = len(self._queue)
        self._position_cache[patient_id] = position
        self._heartbeats[patient_id] = time.time()
        self.mh_user_id[patient_id] = mh_user_id
        if name:
            self._names[patient_id] = name

        self._send_join_email(name, mh_user_id, doctor_email=doctor_email)

        return {
            "position": position,
            "patients_ahead": position - 1,
            "queue_length": len(self._queue),
        }

    def leave(self, patient_id):
        """Remove patient from queue (patient leaves voluntarily)."""
        if patient_id not in self._queue:
            return {"error": "Not in queue"}

        self._queue.remove(patient_id)
        self._heartbeats.pop(patient_id, None)
        self._names.pop(patient_id, None)
        self.mh_user_id.pop(patient_id, None)
        self._update_positions()
        return {"success": True}

    def next(self):
        """Get and remove next patient (doctor calls them)."""
        if not self._queue:
            return {"error": "Queue empty"}

        patient_id = self._queue.pop(0)
        self._heartbeats.pop(patient_id, None)
        self._update_positions()

        self._admitted.append({
            "patient_id": patient_id,
            "name": self._names.get(patient_id, ""),
            "admitted_at": time.time(),
        })

        return {
            "patient_id": patient_id,
            "name": self._names.get(patient_id, ""),
            "remaining": len(self._queue),
        }

    def admit(self, patient_id, doctor_email=None, doctor_name=None,
              send_email=True):
        """
        Admit a specific patient (remove from queue).

        send_email — set to False for bookkeeping removals that should
                     NOT produce an "admitted" email (e.g. conflict path).
        """
        if patient_id not in self._queue:
            return {"error": "Patient not in queue"}

        self._queue.remove(patient_id)
        self._heartbeats.pop(patient_id, None)
        self._update_positions()

        name = self._names.get(patient_id, "")
        mh_user_id = self.mh_user_id.get(patient_id, "")

        self._admitted.append({
            "patient_id": patient_id,
            "name": name,
            "mh_user_id": mh_user_id,
            "admitted_at": time.time(),
        })

        if send_email:
            self._send_admit_email(
                name, mh_user_id,
                doctor_email=doctor_email,
                doctor_name=doctor_name,
            )

        return {
            "success": True,
            "patient_id": patient_id,
            "name": name,
            "mh_user_id": mh_user_id,
            "remaining": len(self._queue),
            "message": f"Patient {name or patient_id} admitted",
        }

    def complete(self, patient_id):
        """Mark a patient as completed (consultation done)."""
        self._completed.append({
            "patient_id": patient_id,
            "name": self._names.get(patient_id, ""),
            "completed_at": time.time(),
        })
        self._admitted = [
            a for a in self._admitted if a["patient_id"] != patient_id
        ]
        return {
            "success": True,
            "patient_id": patient_id,
            "message": (
                f"Patient {self._names.get(patient_id, patient_id)} completed"
            ),
        }

    def admit_and_complete(self, patient_id, doctor_email=None,
                           doctor_name=None):
        """Admit and immediately complete (for quick consultations)."""
        result = self.admit(
            patient_id,
            doctor_email=doctor_email,
            doctor_name=doctor_name,
        )
        if result.get("success"):
            return self.complete(patient_id)
        return result

    # =========================================================
    # Heartbeat / lookup
    # =========================================================
    def heartbeat(self, patient_id):
        if patient_id not in self._queue:
            return {"error": "Not in queue"}
        self._heartbeats[patient_id] = time.time()
        return {"status": "ok"}

    def get_position(self, patient_id):
        """Get patient position — also acts as a heartbeat."""
        if patient_id in self._queue:
            self._heartbeats[patient_id] = time.time()
            position = self._queue.index(patient_id) + 1
            return {
                "position": position,
                "patients_ahead": position - 1,
                "queue_length": len(self._queue),
            }
        return None

    def cleanup_inactive(self, timeout_seconds=120):
        """Remove patients with stale heartbeats."""
        now = time.time()
        to_remove = [
            pid for pid, last_seen in self._heartbeats.items()
            if now - last_seen > timeout_seconds
        ]
        removed = 0
        for pid in to_remove:
            if self.leave(pid).get("success"):
                removed += 1
        return {"removed": removed, "remaining": len(self._queue)}

    def get_queue(self):
        """Full queue with positions and online status."""
        now = time.time()
        queue_data = []
        for i, patient_id in enumerate(self._queue, 1):
            last_seen = self._heartbeats.get(patient_id)
            is_online = bool(last_seen and (now - last_seen < 120))
            queue_data.append({
                "patient_id": patient_id,
                "position": i,
                "name": self._names.get(patient_id, ""),
                "mh_user_id": self.mh_user_id.get(patient_id, ""),
                "is_online": is_online,
                "last_seen": (
                    datetime.fromtimestamp(last_seen).isoformat()
                    if last_seen else None
                ),
            })
        return queue_data

    def get_admitted(self):
        return self._admitted.copy()

    def get_completed(self):
        return self._completed.copy()

    def get_queue_length(self):
        return len(self._queue)

    def is_in_queue(self, patient_id):
        return patient_id in self._queue

    def _update_positions(self):
        self._position_cache = {p: i + 1 for i, p in enumerate(self._queue)}

    def __len__(self):
        return len(self._queue)