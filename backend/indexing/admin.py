from django.contrib import admin

from .models import URLSubmission


@admin.register(URLSubmission)
class URLSubmissionAdmin(admin.ModelAdmin):
    list_display = ('url', 'inspection_status', 'indexing_request_status',
                    'created_at', 'updated_at')
    list_filter = ('inspection_status', 'indexing_request_status')
    search_fields = ('url',)
    readonly_fields = ('url_hash', 'created_at', 'updated_at')
    ordering = ('-created_at',)