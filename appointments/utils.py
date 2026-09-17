# apps/appointments/utils.py
from django.db.models import Q, Count
from django.utils import timezone
from datetime import datetime, timedelta


def auto_assign_doctor(clinic, appointment_data):
    """
    Auto-assign a doctor based on availability
    
    Args:
        clinic: Clinic instance
        appointment_data: Dict with appointment details
    
    Returns:
        DoctorProfile or None
    """
    from .models import Appointment
    
    # Get all doctors at this clinic
    clinic_doctors = clinic.doctors.all()
    
    if not clinic_doctors.exists():
        return None
    
    date = appointment_data.get('appointment_date')
    start_time = appointment_data.get('start_time')
    end_time = appointment_data.get('end_time')
    
    # Get available doctors for this time slot
    available_doctors = get_available_doctors(
        clinic_doctors,
        date,
        start_time,
        end_time
    )
    
    if available_doctors.exists():
        # Use round-robin or least-loaded strategy
        return assign_doctor_strategy(available_doctors, date, 'round_robin')
    
    return None


def get_available_doctors(doctors, date, start_time, end_time):
    """
    Get doctors available for a specific time slot
    
    Args:
        doctors: QuerySet of DoctorProfile
        date: Date of appointment
        start_time: Start time of appointment
        end_time: End time of appointment
    
    Returns:
        QuerySet of available doctors
    """
    from .models import DoctorAvailability, Appointment
    
    if not date:
        return doctors.none()
    
    # Get day of week (0=Monday, 6=Sunday)
    day_of_week = date.weekday()
    
    # Doctors that have availability set for this day
    available_doctors = doctors.filter(
        availability__day_of_week=day_of_week,
        availability__is_available=True,
        availability__start_time__lte=start_time,
        availability__end_time__gte=end_time
    ).distinct()
    
    # Exclude doctors who already have appointments at this time
    existing_appointments = Appointment.objects.filter(
        appointment_date=date,
        start_time__lt=end_time,
        end_time__gt=start_time,
        status__in=['scheduled', 'confirmed', 'in_progress']
    ).values_list('doctor_profile_id', flat=True)
    
    available_doctors = available_doctors.exclude(
        id__in=existing_appointments
    )
    
    return available_doctors


def assign_doctor_strategy(available_doctors, date, strategy='round_robin'):
    """
    Assign a doctor using different strategies
    
    Strategies:
        - 'round_robin': Distribute appointments evenly
        - 'least_loaded': Assign to doctor with fewest appointments
        - 'first_available': Assign to first available doctor
    """
    from .models import Appointment
    
    if not available_doctors.exists():
        return None
    
    if strategy == 'round_robin':
        # Get the doctor with the fewest appointments on that day
        doctor_appointments = Appointment.objects.filter(
            appointment_date=date,
            doctor_profile__in=available_doctors,
            status__in=['scheduled', 'confirmed', 'in_progress']
        ).values('doctor_profile').annotate(
            count=Count('id')
        )
        
        # Find doctor with fewest appointments
        doctor_counts = {doc.id: 0 for doc in available_doctors}
        for item in doctor_appointments:
            doctor_counts[item['doctor_profile']] = item['count']
        
        # Find doctor with minimum appointments
        min_doctor_id = min(doctor_counts, key=doctor_counts.get)
        doctor_to_assign = available_doctors.get(id=min_doctor_id)
        
    elif strategy == 'least_loaded':
        # Get appointment counts for all doctors
        doctor_appointments = Appointment.objects.filter(
            appointment_date=date,
            doctor_profile__in=available_doctors,
            status__in=['scheduled', 'confirmed', 'in_progress']
        ).values('doctor_profile').annotate(
            count=Count('id')
        )
        
        doctor_counts = {doc.id: 0 for doc in available_doctors}
        for item in doctor_appointments:
            doctor_counts[item['doctor_profile']] = item['count']
        
        # Find doctor with minimum appointments
        min_doctor_id = min(doctor_counts, key=doctor_counts.get)
        doctor_to_assign = available_doctors.get(id=min_doctor_id)
        
    else:  # 'first_available'
        doctor_to_assign = available_doctors.first()
    
    return doctor_to_assign


def get_next_available_slot(doctor_profile, date=None, duration=30):
    """
    Get the next available time slot for a doctor
    
    Args:
        doctor_profile: DoctorProfile instance
        date: Date to check (default: today)
        duration: Appointment duration in minutes
    
    Returns:
        Dict with date, start_time, end_time or None
    """
    from .models import Appointment, DoctorAvailability
    
    if not date:
        date = timezone.now().date()
    
    day_of_week = date.weekday()
    
    # Get availability for this day
    availability = DoctorAvailability.objects.filter(
        doctor_profile=doctor_profile,
        day_of_week=day_of_week,
        is_available=True
    ).first()
    
    if not availability:
        return None
    
    # Get existing appointments for this day
    existing_appointments = Appointment.objects.filter(
        doctor_profile=doctor_profile,
        appointment_date=date,
        status__in=['scheduled', 'confirmed', 'in_progress']
    ).order_by('start_time')
    
    # Find first available slot
    current_time = availability.start_time
    end_time = availability.end_time
    
    # Convert to datetime for easier comparison
    current_datetime = datetime.combine(date, current_time)
    end_datetime = datetime.combine(date, end_time)
    
    for appointment in existing_appointments:
        appointment_start = datetime.combine(date, appointment.start_time)
        appointment_end = datetime.combine(date, appointment.end_time)
        
        # Check if there's a gap before this appointment
        gap = (appointment_start - current_datetime).total_seconds() / 60
        if gap >= duration:
            return {
                'date': date,
                'start_time': current_datetime.time(),
                'end_time': (current_datetime + timedelta(minutes=duration)).time()
            }
        
        # Move current time to after this appointment
        current_datetime = appointment_end
    
    # Check if there's time at the end of the day
    gap = (end_datetime - current_datetime).total_seconds() / 60
    if gap >= duration:
        return {
            'date': date,
            'start_time': current_datetime.time(),
            'end_time': (current_datetime + timedelta(minutes=duration)).time()
        }
    
    return None