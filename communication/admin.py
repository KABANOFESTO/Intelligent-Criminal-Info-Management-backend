from django.contrib import admin
from .models import CommunicationLog, Case

@admin.register(Case)
class CaseAdmin(admin.ModelAdmin):
    list_display = ['case_id', 'title', 'status', 'created_at', 'updated_at']
    list_filter = ['status', 'created_at']
    search_fields = ['case_id', 'title', 'description']
    readonly_fields = ['created_at', 'updated_at']


@admin.register(CommunicationLog)
class CommunicationLogAdmin(admin.ModelAdmin):
    list_display = [
        'sender', 'receiver', 'subject', 'message_type', 
        'priority', 'is_read', 'timestamp', 'related_case'
    ]
    list_filter = [
        'message_type', 'priority', 'is_read', 'timestamp', 'related_case'
    ]
    search_fields = [
        'sender__username', 'receiver__username', 'subject', 
        'message_content', 'related_case__case_id'
    ]
    readonly_fields = ['timestamp', 'read_at']
    raw_id_fields = ['sender', 'receiver', 'related_case']
    
    fieldsets = (
        ('Communication Details', {
            'fields': ('sender', 'receiver', 'subject', 'message_content')
        }),
        ('Classification', {
            'fields': ('message_type', 'priority', 'related_case')
        }),
        ('Status', {
            'fields': ('is_read', 'read_at', 'timestamp'),
            'classes': ('collapse',)
        }),
        ('Additional Data', {
            'fields': ('attachments',),
            'classes': ('collapse',)
        }),
    )
    
    def get_queryset(self, request):
        return super().get_queryset(request).select_related(
            'sender', 'receiver', 'related_case'
        )
