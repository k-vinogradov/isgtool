# -*- coding: utf-8 -*-

from django.contrib import admin
from django.utils import timezone
from www.models import *
from django.http import HttpResponse
from xlsxwriter.workbook import Workbook
from io import BytesIO


def acknowledge_records(modeladmin, request, queryset):
    queryset.update(acknowledged='p')


acknowledge_records.short_description = u'Acknowledge records'


@admin.register(UserNotification)
class UserNotificationAdmin(admin.ModelAdmin):
    pass


@admin.register(UserNotificationRecord)
class UserNotificationRecordAdmin(admin.ModelAdmin):
    list_display = (
        'is_acknowledged',
        'uid',
        'notification',
        'is_completed',
        'completed',)
    list_display_links = ('uid',)
    list_filter = ('notification', 'is_completed', 'completed', 'is_acknowledged')
    search_fields = ('uid',)
    date_hierarchy = 'completed'
    save_on_top = True
    fields = ['notification', 'uid', 'is_completed', 'is_acknowledged', 'refreshed', 'completed', 'display_answer', ]
    readonly_fields = ['is_completed', 'refreshed', 'completed', 'display_answer']
    actions = [acknowledge_records, ]


"""
@admin.register(UserNotificationRecord)
class UserNotificationRecordAdmin(admin.ModelAdmin):
    list_display = (
        'acknowledged',
        'notification',
        'user_id',
        'completed',
        'display_answer',
        'seen_datetime',
        'complete_datetime',)
    list_display_links = ('user_id',)
    list_filter = ('notification', 'completed', AnswerFilter, 'complete_datetime', 'acknowledged')
    search_fields = ('user_id',)
    date_hierarchy = 'complete_datetime'
    save_on_top = True
    readonly_fields = ('notification', 'user_id', 'completed', 'answer', 'seen_datetime', 'complete_datetime',)
    actions = [acknowledge_records, ]
    actions = ['export_to_excel',]

    def export_to_excel(self, request, queryset):
        self.message_user(request, 'Export {0} records to MS Excel format...'.format(queryset.count()))
        columns_formats = [
            {'index': 0, 'title': u'Acknowledged', 'width': 17},
            {'index': 1, 'title': u'Notification', 'width': 15},
            {'index': 2, 'title': u'User ID', 'width': 16},
            {'index': 3, 'title': u'Completed', 'width': 16},
            {'index': 4, 'title': u'Display Answer', 'width': 20},
            {'index': 5, 'title': u'Seen', 'width': 20},
            {'index': 6, 'title': u'Answered', 'width': 20},
        ]
        output = BytesIO()
        workbook = Workbook(output, {'in_memory': True})
        header_format = workbook.add_format(
            properties={
                'bg_color': 'yellow',
                'border_color': 'black',
                'border': 1,
                'text_wrap': True,
                'valign': 'top'})
        text_wrap = workbook.add_format(properties={'text_wrap': True, 'valign': 'top'})
        worksheet = workbook.add_worksheet(u'Records')
        worksheet.write_row(0, 0, [col['title'] for col in columns_formats], header_format)
        for col in columns_formats:
            worksheet.set_column(col['index'], col['index'], col['width'])
        row_index = 1
        for r in queryset.all():
            cells = [
                u'Yes' if r.acknowledged else u'No',
                r.notification.name,
                r.user_id,
                u'Yes' if r.completed else u'No',
                r.display_answer(),
                r.seen_datetime.strftime('%d.%m.%Y %H:%M:%S') if r.seen_datetime else u'',
                r.complete_datetime.strftime('%d.%m.%Y %H:%M:%S') if r.complete_datetime else u'', ]
            worksheet.write_row(row_index, 0, cells, text_wrap)
            row_index += 1
        workbook.close()
        output.seek(0)
        response = HttpResponse(output.read(),
                                content_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet")
        response['Content-Disposition'] = 'attachment; filename="User Notification Records.xlsx"'
        return response

    export_to_excel.short_description = 'Export to MS Excel'
"""
