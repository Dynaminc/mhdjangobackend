# apps/appointments/simple_queue.py
import time
from datetime import datetime

class SimpleQueue:
    def __init__(self):
        self._queue = []           # List of patient IDs
        self._position_cache = {}  # Cache for quick position lookup
        self._heartbeats = {}      # Track last seen time
        self._names = {}           # Store patient names
        self._admitted = []        # Track admitted patients (history)
        self._completed = []       # Track completed patients (history)
    
    def join(self, patient_id, name=""):
        """Add patient to queue"""
        if patient_id in self._queue:
            return {"error": "Already in queue"}
        
        self._queue.append(patient_id)
        position = len(self._queue)
        self._position_cache[patient_id] = position
        self._heartbeats[patient_id] = time.time()
        if name:
            self._names[patient_id] = name
        
        return {
            "position": position,
            "patients_ahead": position - 1,
            "queue_length": len(self._queue)
        }
    
    def leave(self, patient_id):
        """Remove patient from queue (patient leaves voluntarily)"""
        if patient_id not in self._queue:
            return {"error": "Not in queue"}
        
        self._queue.remove(patient_id)
        self._heartbeats.pop(patient_id, None)
        self._names.pop(patient_id, None)
        self._update_positions()
        
        return {"success": True}
    
    def next(self):
        """Get and remove next patient (doctor calls them)"""
        if not self._queue:
            return {"error": "Queue empty"}
        
        patient_id = self._queue.pop(0)
        self._heartbeats.pop(patient_id, None)
        self._update_positions()
        
        # ✅ Add to admitted history
        self._admitted.append({
            "patient_id": patient_id,
            "name": self._names.get(patient_id, ""),
            "admitted_at": time.time()
        })
        
        return {
            "patient_id": patient_id,
            "name": self._names.get(patient_id, ""),
            "remaining": len(self._queue)
        }
    
    def admit(self, patient_id):
        """
        ✅ Admit a specific patient (remove from queue)
        Use this when doctor manually selects a patient
        """
        if patient_id not in self._queue:
            return {"error": "Patient not in queue"}
        
        # Remove from queue
        self._queue.remove(patient_id)
        self._heartbeats.pop(patient_id, None)
        self._update_positions()
        
        # Add to admitted history
        self._admitted.append({
            "patient_id": patient_id,
            "name": self._names.get(patient_id, ""),
            "admitted_at": time.time()
        })
        
        return {
            "success": True,
            "patient_id": patient_id,
            "name": self._names.get(patient_id, ""),
            "remaining": len(self._queue),
            "message": f"Patient {self._names.get(patient_id, patient_id)} admitted"
        }
    
    def complete(self, patient_id):
        """✅ Mark a patient as completed (consultation done)"""
        self._completed.append({
            "patient_id": patient_id,
            "name": self._names.get(patient_id, ""),
            "completed_at": time.time()
        })
        # Remove from admitted if present
        self._admitted = [a for a in self._admitted if a["patient_id"] != patient_id]
        
        return {
            "success": True,
            "patient_id": patient_id,
            "message": f"Patient {self._names.get(patient_id, patient_id)} completed"
        }
    
    def admit_and_complete(self, patient_id):
        """✅ Admit and immediately complete (for quick consultations)"""
        result = self.admit(patient_id)
        if result.get("success"):
            return self.complete(patient_id)
        return result
    
    def heartbeat(self, patient_id):
        """Update last seen timestamp"""
        if patient_id not in self._queue:
            return {"error": "Not in queue"}
        
        self._heartbeats[patient_id] = time.time()
        return {"status": "ok"}
    
    def get_position(self, patient_id):
        """Get patient's current position - ALSO acts as heartbeat!"""
        if patient_id in self._queue:
            self._heartbeats[patient_id] = time.time()
            position = self._queue.index(patient_id) + 1
            return {
                "position": position,
                "patients_ahead": position - 1,
                "queue_length": len(self._queue)
            }
        return None
    
    def cleanup_inactive(self, timeout_seconds=120):
        """Remove patients who haven't checked position or sent heartbeat"""
        now = time.time()
        to_remove = []
        
        for patient_id, last_seen in self._heartbeats.items():
            if now - last_seen > timeout_seconds:
                to_remove.append(patient_id)
        
        removed = 0
        for patient_id in to_remove:
            result = self.leave(patient_id)
            if result.get("success"):
                removed += 1
        
        return {"removed": removed, "remaining": len(self._queue)}
    
    def get_queue(self):
        """Get full queue with positions and online status"""
        now = time.time()
        queue_data = []
        
        for i, patient_id in enumerate(self._queue, 1):
            last_seen = self._heartbeats.get(patient_id)
            is_online = last_seen and (now - last_seen < 120)
            
            queue_data.append({
                "patient_id": patient_id,
                "position": i,
                "name": self._names.get(patient_id, ""),
                "is_online": is_online,
                "last_seen": datetime.fromtimestamp(last_seen).isoformat() if last_seen else None
            })
        
        return queue_data
    
    def get_admitted(self):
        """Get list of admitted patients"""
        return self._admitted.copy()
    
    def get_completed(self):
        """Get list of completed patients"""
        return self._completed.copy()
    
    def get_queue_length(self):
        """Get number of patients in queue"""
        return len(self._queue)
    
    def is_in_queue(self, patient_id):
        """Check if patient is in queue"""
        return patient_id in self._queue
    
    def _update_positions(self):
        """Recalculate position cache"""
        self._position_cache = {p: i + 1 for i, p in enumerate(self._queue)}
    
    def __len__(self):
        return len(self._queue)