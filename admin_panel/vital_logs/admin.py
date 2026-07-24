import csv
from django.http import HttpResponse
from django.contrib import admin
from .models import UserSession, VitalSignLog

@admin.register(UserSession)
class UserSessionAdmin(admin.ModelAdmin):
    list_display = ('session_id', 'user', 'start_time', 'end_time')
    search_fields = ('session_id', 'user__username')

@admin.register(VitalSignLog)
class VitalSignLogAdmin(admin.ModelAdmin):
    list_display = ('session', 'timestamp', 'bpm', 'rr', 'signal_quality')
    list_filter = ('session', 'timestamp')
    search_fields = ('session__session_id',)
    actions = ['export_to_csv']

    def export_to_csv(self, request, queryset):
        response = HttpResponse(content_type='text/csv')
        response['Content-Disposition'] = 'attachment; filename="vital_logs_export.csv"'

        writer = csv.writer(response)
        writer.writerow(['Session', 'Timestamp', 'BPM', 'RR', 'Quality'])

        for obj in queryset:
            writer.writerow([obj.session, obj.timestamp, obj.bpm, obj.rr, obj.signal_quality])

        return response

    export_to_csv.short_description = "Export selected logs to CSV"
