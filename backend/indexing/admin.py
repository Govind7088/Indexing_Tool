from django.contrib import admin

from .models import URLSubmission


@admin.register(URLSubmission)
class URLSubmissionAdmin(admin.ModelAdmin):
    list_display = ('url', 'created_at')
    ordering = ('-created_at',)