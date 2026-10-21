# apps/files/admin.py
from django.contrib import admin
from django.utils.html import format_html
from .models import SecureFile


@admin.register(SecureFile)
class SecureFileAdmin(admin.ModelAdmin):
    list_display = ('filename', 'owner', 'size_display', 'mime', 'created_at', 'download_link')
    list_filter = ('mime', 'created_at')
    search_fields = ('filename', 'owner__email', 'owner__username')
    readonly_fields = ('id', 'path', 'size', 'created_at', 'download_link')
    exclude = ('data',)   # (no data field anymore, but safe)
    date_hierarchy = 'created_at'
    ordering = ('-created_at',)

    fields = (
        'id', 'owner', 'filename', 'mime',
        'size', 'path', 'created_at', 'download_link',
    )

    @admin.display(description='Size')
    def size_display(self, obj):
        kb = obj.size / 1024
        return format_html('{:.1f} KB', kb) if kb < 1024 else format_html('{:.1f} MB', kb / 1024)

    @admin.display(description='Download')
    def download_link(self, obj):
        return format_html('<a href="/api/v1/files/{}/" target="_blank">Open</a>', obj.id)