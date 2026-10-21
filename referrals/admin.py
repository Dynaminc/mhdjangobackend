# apps/specialists/admin.py
from django.contrib import admin
from django.utils import timezone
from django.utils.html import format_html
from django.utils.safestring import mark_safe
from django.db.models import Count, Avg

from .models import (
    Specialist,
    SpecialistTimeline,
    SpecialistCredential,
    SpecialistLanguage,
    SpecialistSocialLink,
    SpecialistTag,
    SpecialistWeeklyAvailability,
    SpecialistReview,
    SpecialistReferral,
)


# ═════════════════════════════════════════════════════════════
# Small helpers
# ═════════════════════════════════════════════════════════════
def badge(text, color='#22c55e'):
    return mark_safe(f'<span style="color:{color};font-weight:600;">{text}</span>')


STATUS_COLORS = {
    'available': '#22c55e',
    'busy': '#f59e0b',
    'unavailable': '#ef4444',
    'on_leave': '#8b5cf6',
    'accepting_waitlist': '#3f76c9',
}

VERIFICATION_COLORS = {
    'unverified': '#94a3b8',
    'pending': '#f59e0b',
    'verified': '#22c55e',
    'premium': '#8b5cf6',
}

REFERRAL_STATUS_COLORS = {
    'pending': '#f59e0b',
    'under_review': '#3f76c9',
    'approved': '#22c55e',
    'scheduled': '#0ea5e9',
    'completed': '#16a34a',
    'rejected': '#ef4444',
    'cancelled': '#94a3b8',
}


# ═════════════════════════════════════════════════════════════
# Inlines
# ═════════════════════════════════════════════════════════════
class SpecialistTimelineInline(admin.TabularInline):
    model = SpecialistTimeline
    extra = 1
    fields = ('display_order', 'start_year', 'end_year', 'is_current',
              'title', 'organization', 'location', 'description')
    ordering = ('display_order', '-start_year')


class SpecialistCredentialInline(admin.TabularInline):
    model = SpecialistCredential
    extra = 1
    fields = ('display_order', 'credential_type', 'title', 'institution',
              'year_obtained', 'country', 'is_verified')
    ordering = ('display_order', '-year_obtained')


class SpecialistLanguageInline(admin.TabularInline):
    model = SpecialistLanguage
    extra = 1
    fields = ('display_order', 'language', 'proficiency')
    ordering = ('display_order', 'language')


class SpecialistSocialLinkInline(admin.TabularInline):
    model = SpecialistSocialLink
    extra = 1
    fields = ('display_order', 'platform', 'url', 'label', 'is_public')
    ordering = ('display_order', 'platform')


class SpecialistTagInline(admin.TabularInline):
    model = SpecialistTag
    extra = 1
    fields = ('display_order', 'name', 'color', 'category')
    ordering = ('display_order', 'name')


class SpecialistWeeklyAvailabilityInline(admin.TabularInline):
    model = SpecialistWeeklyAvailability
    extra = 0
    fields = ('date', 'is_available', 'slots_count', 'note')
    ordering = ('date',)


class SpecialistReviewInline(admin.TabularInline):
    model = SpecialistReview
    extra = 0
    fields = ('reviewer', 'reviewer_display_name', 'rating', 'title',
              'is_published', 'is_anonymous')
    readonly_fields = ('created_at',)
    ordering = ('-created_at',)


# ═════════════════════════════════════════════════════════════
# Specialist
# ═════════════════════════════════════════════════════════════
@admin.register(Specialist)
class SpecialistAdmin(admin.ModelAdmin):
    list_display = (
        'name_display',
        'specialty',
        'country',
        'status_badge',
        'verification_badge',
        'rating_display',
        'reviews_display',
        'is_featured',
        'is_active',
        'linked_user_display',
    )
    list_filter = (
        'status',
        'verification_level',
        'specialty',
        'country',
        'is_remote',
        'is_active',
        'is_featured',
    )
    search_fields = (
        'first_name', 'last_name', 'middle_name',
        'headline', 'short_bio', 'credentials',
        'slug', 'user__mh_user_id',
        'user__user__email',
    )
    readonly_fields = (
        'id', 'slug',
        'joined_at', 'created_at', 'updated_at', 'last_active_at',
        'avatar_preview',
    )
    prepopulated_fields = {}
    date_hierarchy = 'created_at'
    ordering = ('-is_featured', 'last_name', 'first_name')
    list_per_page = 25
    save_on_top = True

    inlines = [
        SpecialistTimelineInline,
        SpecialistCredentialInline,
        SpecialistLanguageInline,
        SpecialistSocialLinkInline,
        SpecialistTagInline,
        SpecialistWeeklyAvailabilityInline,
        SpecialistReviewInline,
    ]

    fieldsets = (
        ('Identity', {
            'fields': (
                'id', 'slug',
                'title', 'first_name', 'middle_name', 'last_name',
                'preferred_name', 'pronouns', 'gender',
                'credentials',
            )
        }),
        ('Professional', {
            'fields': (
                'specialty', 'sub_specialties', 'headline',
            )
        }),
        ('Bio', {
            'fields': (
                'short_bio', 'long_bio', 'personal_philosophy',
            )
        }),
        ('Media', {
            'fields': (
                'avatar', 'avatar_preview', 'avatar_url',
                'cover_image', 'video_intro_url',
            )
        }),
        ('Location', {
            'fields': (
                'country', 'state', 'city', 'timezone', 'is_remote',
            )
        }),
        ('Experience', {
            'fields': (
                'years_experience', 'years_in_practice_start',
                'total_consultations',
            )
        }),
        ('Consultation', {
            'fields': (
                'languages',
                'consultation_formats',
                'session_length_minutes', 'session_length_max_minutes',
                'response_time_hours', 'follow_up_included',
            )
        }),
        ('Fees (internal)', {
            'fields': (
                'consultation_fee_min', 'consultation_fee_max',
                'currency', 'accepts_insurance', 'insurance_providers',
            ),
            'classes': ('collapse',)
        }),
        ('Stats', {
            'fields': (
                'average_rating', 'total_reviews',
                'response_rate_percent', 'recommendation_rate',
            )
        }),
        ('Tags & Expertise', {
            'fields': ('tags', 'areas_of_expertise')
        }),
        ('Status & Verification', {
            'fields': (
                'status', 'is_online_now',
                'verification_level',
                'is_active', 'is_featured',
            )
        }),
        ('Linked User', {
            'fields': ('user',)
        }),
        ('Internal Notes', {
            'fields': ('internal_notes',),
            'classes': ('collapse',)
        }),
        ('Timestamps', {
            'fields': (
                'joined_at', 'created_at', 'updated_at', 'last_active_at',
            ),
            'classes': ('collapse',)
        }),
    )

    # ── Column methods ───────────────────────────────────────
    @admin.display(description='Name', ordering='last_name')
    def name_display(self, obj):
        return obj.full_name or f"{obj.first_name} {obj.last_name}"

    @admin.display(description='Status')
    def status_badge(self, obj):
        color = STATUS_COLORS.get(obj.status, '#94a3b8')
        return badge(obj.get_status_display(), color)

    @admin.display(description='Verification')
    def verification_badge(self, obj):
        color = VERIFICATION_COLORS.get(obj.verification_level, '#94a3b8')
        return badge(obj.get_verification_level_display(), color)

    @admin.display(description='Rating')
    def rating_display(self, obj):
        if not obj.average_rating:
            return '—'
        return format_html(
            '<span style="color:#d4a017;font-weight:700;">★ {}</span>',
            f"{obj.average_rating:.2f}"
        )

    @admin.display(description='Reviews')
    def reviews_display(self, obj):
        return obj.total_reviews

    @admin.display(description='Linked user')
    def linked_user_display(self, obj):
        if not obj.user:
            return '—'
        return obj.user.mh_user_id or obj.user.user.email

    @admin.display(description='Avatar preview')
    def avatar_preview(self, obj):
        if obj.avatar:
            return format_html(
                '<img src="{}" style="max-height:120px;border-radius:12px;" />',
                obj.avatar.url
            )
        if obj.avatar_url:
            return format_html(
                '<img src="{}" style="max-height:120px;border-radius:12px;" />',
                obj.avatar_url
            )
        return '—'

    # ── Bulk actions ─────────────────────────────────────────
    actions = [
        'mark_available', 'mark_unavailable',
        'mark_verified', 'mark_featured', 'unmark_featured',
        'activate', 'deactivate',
    ]

    @admin.action(description='Set status → Available')
    def mark_available(self, request, queryset):
        n = queryset.update(status='available')
        self.message_user(request, f'{n} specialists set to Available.')

    @admin.action(description='Set status → Unavailable')
    def mark_unavailable(self, request, queryset):
        n = queryset.update(status='unavailable')
        self.message_user(request, f'{n} specialists set to Unavailable.')

    @admin.action(description='Set verification → Verified')
    def mark_verified(self, request, queryset):
        n = queryset.update(verification_level='verified')
        self.message_user(request, f'{n} specialists marked Verified.')

    @admin.action(description='Mark as Featured')
    def mark_featured(self, request, queryset):
        n = queryset.update(is_featured=True)
        self.message_user(request, f'{n} specialists featured.')

    @admin.action(description='Remove Featured')
    def unmark_featured(self, request, queryset):
        n = queryset.update(is_featured=False)
        self.message_user(request, f'{n} specialists un-featured.')

    @admin.action(description='Activate')
    def activate(self, request, queryset):
        n = queryset.update(is_active=True)
        self.message_user(request, f'{n} specialists activated.')

    @admin.action(description='Deactivate')
    def deactivate(self, request, queryset):
        n = queryset.update(is_active=False)
        self.message_user(request, f'{n} specialists deactivated.')


# ═════════════════════════════════════════════════════════════
# Standalone registration for sub-models (so they're reachable
# from the admin index, even though they're edited via inlines)
# ═════════════════════════════════════════════════════════════
@admin.register(SpecialistTimeline)
class SpecialistTimelineAdmin(admin.ModelAdmin):
    list_display = ('specialist', 'year_range_display', 'title', 'organization', 'is_current')
    list_filter = ('is_current',)
    search_fields = ('specialist__first_name', 'specialist__last_name',
                     'title', 'organization')
    ordering = ('specialist', 'display_order', '-start_year')

    @admin.display(description='Years')
    def year_range_display(self, obj):
        return obj.year_range


@admin.register(SpecialistCredential)
class SpecialistCredentialAdmin(admin.ModelAdmin):
    list_display = ('specialist', 'title', 'credential_type', 'institution',
                    'year_obtained', 'is_verified')
    list_filter = ('credential_type', 'is_verified', 'year_obtained')
    search_fields = ('specialist__first_name', 'specialist__last_name',
                     'title', 'institution')
    ordering = ('specialist', 'display_order', '-year_obtained')


@admin.register(SpecialistLanguage)
class SpecialistLanguageAdmin(admin.ModelAdmin):
    list_display = ('specialist', 'language', 'proficiency', 'display_order')
    list_filter = ('proficiency', 'language')
    search_fields = ('specialist__first_name', 'specialist__last_name', 'language')
    ordering = ('specialist', 'display_order', 'language')


@admin.register(SpecialistSocialLink)
class SpecialistSocialLinkAdmin(admin.ModelAdmin):
    list_display = ('specialist', 'platform', 'url_display', 'is_public', 'display_order')
    list_filter = ('platform', 'is_public')
    search_fields = ('specialist__first_name', 'specialist__last_name', 'url')
    ordering = ('specialist', 'display_order', 'platform')

    @admin.display(description='URL')
    def url_display(self, obj):
        return format_html('<a href="{}" target="_blank">{}</a>', obj.url, obj.url)


@admin.register(SpecialistTag)
class SpecialistTagAdmin(admin.ModelAdmin):
    list_display = ('specialist', 'name', 'color', 'category', 'display_order')
    list_filter = ('color', 'category')
    search_fields = ('specialist__first_name', 'specialist__last_name', 'name')
    ordering = ('specialist', 'display_order', 'name')


@admin.register(SpecialistWeeklyAvailability)
class SpecialistWeeklyAvailabilityAdmin(admin.ModelAdmin):
    list_display = ('specialist', 'date', 'is_available', 'slots_count', 'note')
    list_filter = ('is_available', 'date')
    search_fields = ('specialist__first_name', 'specialist__last_name')
    ordering = ('specialist', 'date')
    date_hierarchy = 'date'


@admin.register(SpecialistReview)
class SpecialistReviewAdmin(admin.ModelAdmin):
    list_display = ('specialist', 'rating_stars', 'reviewer_display_name',
                    'title', 'is_published', 'is_anonymous', 'created_at')
    list_filter = ('rating', 'is_published', 'is_anonymous', 'created_at')
    search_fields = ('specialist__first_name', 'specialist__last_name',
                     'title', 'body', 'reviewer_display_name',
                     'reviewer__mh_user_id')
    readonly_fields = ('created_at',)
    ordering = ('-created_at',)
    date_hierarchy = 'created_at'
    actions = ['publish_reviews', 'unpublish_reviews']

    @admin.display(description='Rating')
    def rating_stars(self, obj):
        stars = '★' * obj.rating + '☆' * (5 - obj.rating)
        return format_html(
            '<span style="color:#d4a017;font-weight:700;">{}</span>', stars
        )

    @admin.action(description='Publish selected reviews')
    def publish_reviews(self, request, queryset):
        n = queryset.update(is_published=True)
        self.message_user(request, f'{n} reviews published.')

    @admin.action(description='Unpublish selected reviews')
    def unpublish_reviews(self, request, queryset):
        n = queryset.update(is_published=False)
        self.message_user(request, f'{n} reviews unpublished.')


# ═════════════════════════════════════════════════════════════
# SpecialistReferral — the intake form
# ═════════════════════════════════════════════════════════════
@admin.register(SpecialistReferral)
class SpecialistReferralAdmin(admin.ModelAdmin):
    list_display = (
        'reference_id',
        'patient_name',
        'email',
        'status_badge',
        'assigned_specialist',
        'submitted_at',
        'linked_user_display',
        'onboarding_complete',
    )
    list_filter = (
        'status',
        'onboarding_complete',
        'sex',
        'duration',
        'severity',
        'frequency',
        'submitted_at',
        'country',
    )
    search_fields = (
        'reference_id',
        'first_name', 'last_name',
        'email', 'phone',
        'complaint', 'symptoms',
    )
    readonly_fields = (
        'id', 'reference_id',
        'submitted_at', 'created_at', 'updated_at',
        'consented_at', 'approved_at', 'rejected_at',
        'linked_at', 'linked_user',
        'reviewed_by',
        'linked_user_display',
    )
    date_hierarchy = 'submitted_at'
    ordering = ('-submitted_at',)
    list_per_page = 25
    raw_id_fields = ('assigned_specialist',)

    fieldsets = (
        ('Reference', {
            'fields': ('id', 'reference_id', 'status', 'submitted_at')
        }),
        ('Personal', {
            'fields': (
                'first_name', 'last_name', 'age', 'sex',
                'marital_status', 'religion', 'tribe',
            )
        }),
        ('Contact', {
            'fields': (
                'email', 'phone', 'country', 'state', 'city',
            )
        }),
        ('Complaint', {
            'fields': (
                'complaint', 'symptoms',
                'duration', 'severity', 'frequency',
                'progression', 'expectations',
            )
        }),
        ('Consent', {
            'fields': ('consented_at', 'consent_version')
        }),
        ('Assignment & Schedule', {
            'fields': (
                'assigned_specialist',
                'appointment_date', 'appointment_time',
                'meeting_link',
            )
        }),
        ('Linked account', {
            'fields': (
                'linked_user', 'linked_user_display',
                'linked_at', 'onboarding_complete',
            )
        }),
        ('Review', {
            'fields': (
                'reviewed_by', 'review_notes',
                'approved_at', 'rejected_at', 'rejection_reason',
            ),
            'classes': ('collapse',)
        }),
        ('Timestamps', {
            'fields': ('created_at', 'updated_at'),
            'classes': ('collapse',)
        }),
    )

    # ── Column methods ───────────────────────────────────────
    @admin.display(description='Patient', ordering='last_name')
    def patient_name(self, obj):
        return obj.full_name

    @admin.display(description='Status')
    def status_badge(self, obj):
        color = REFERRAL_STATUS_COLORS.get(obj.status, '#94a3b8')
        return badge(obj.get_status_display(), color)

    @admin.display(description='Linked user')
    def linked_user_display(self, obj):
        if not obj.linked_user:
            return '—'
        return obj.linked_user.email or obj.linked_user.username

    # ── Bulk actions for status flow ─────────────────────────
    actions = [
        'mark_under_review',
        'mark_approved',
        'mark_rejected',
        'mark_cancelled',
    ]

    @admin.action(description='Mark as Under Review')
    def mark_under_review(self, request, queryset):
        n = queryset.update(status='under_review')
        self.message_user(request, f'{n} referral(s) marked Under Review.')

    @admin.action(description='Approve referrals')
    def mark_approved(self, request, queryset):
        n = queryset.update(
            status='approved',
            approved_at=timezone.now(),
            reviewed_by=request.user,
        )
        self.message_user(request, f'{n} referral(s) approved.')

    @admin.action(description='Reject referrals')
    def mark_rejected(self, request, queryset):
        n = queryset.update(
            status='rejected',
            rejected_at=timezone.now(),
            reviewed_by=request.user,
        )
        self.message_user(request, f'{n} referral(s) rejected.')

    @admin.action(description='Cancel referrals')
    def mark_cancelled(self, request, queryset):
        n = queryset.update(status='cancelled')
        self.message_user(request, f'{n} referral(s) cancelled.')

    # ── Row-level convenience ────────────────────────────────
    def get_queryset(self, request):
        qs = super().get_queryset(request)
        # Optimise the FK lookups used in list_display
        return qs.select_related(
            'assigned_specialist',
            'assigned_specialist__user',
            'linked_user',
            'reviewed_by',
        )