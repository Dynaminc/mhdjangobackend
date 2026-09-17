# # apps/payments/admin.py
# from django.contrib import admin
# from django.utils.html import format_html
# from .models import Payment


# # ============================================
# # Payment Admin
# # ============================================
# @admin.register(Payment)
# class PaymentAdmin(admin.ModelAdmin):
#     list_display = (
#         'id',
#         'get_patient',
#         'appointment',
#         'amount_display',
#         'payment_method',
#         'status_badge',
#         'payment_date',
#         'transaction_id'
#     )
#     list_filter = ('status', 'payment_method', 'currency', 'payment_date')
#     search_fields = (
#         'transaction_id',
#         'patient_profile__profile__user__username',
#         'patient_profile__profile__user__email'
#     )
#     raw_id_fields = ('patient_profile', 'appointment')
#     readonly_fields = ('payment_date', 'created_at', 'updated_at')
#     date_hierarchy = 'payment_date'
#     ordering = ('-payment_date',)
    
#     fieldsets = (
#         ('Payment Info', {
#             'fields': ('patient_profile', 'appointment', 'amount', 'currency', 'payment_method')
#         }),
#         ('Status', {
#             'fields': ('status', 'transaction_id', 'payment_date')
#         }),
#         ('Timestamps', {
#             'fields': ('created_at', 'updated_at'),
#             'classes': ('collapse',)
#         }),
#     )
    
#     def get_patient(self, obj):
#         return obj.patient_profile.profile.user.get_full_name()
#     get_patient.short_description = 'Patient'
    
#     def amount_display(self, obj):
#         return f"{obj.currency} {obj.amount:.2f}"
#     amount_display.short_description = 'Amount'
    
#     def status_badge(self, obj):
#         colors = {
#             'pending': '#f59e0b',
#             'completed': '#22c55e',
#             'failed': '#ef4444',
#             'refunded': '#94a3b8'
#         }
#         return format_html(
#             '<span style="color: {}; font-weight: 600;">{}</span>',
#             colors.get(obj.status, '#94a3b8'),
#             obj.get_status_display()
#         )
#     status_badge.short_description = 'Status'
    
#     actions = ['mark_completed', 'mark_failed', 'mark_refunded']
    
#     def mark_completed(self, request, queryset):
#         updated = queryset.update(status='completed')
#         self.message_user(request, f'{updated} payments marked as completed.')
#     mark_completed.short_description = 'Mark as Completed'
    
#     def mark_failed(self, request, queryset):
#         updated = queryset.update(status='failed')
#         self.message_user(request, f'{updated} payments marked as failed.')
#     mark_failed.short_description = 'Mark as Failed'
    
#     def mark_refunded(self, request, queryset):
#         updated = queryset.update(status='refunded')
#         self.message_user(request, f'{updated} payments marked as refunded.')
#     mark_refunded.short_description = 'Mark as Refunded'