# -*- coding: utf-8 -*-

from django.contrib import admin
from www.models import *
from django.http import HttpResponse
from xlsxwriter.workbook import Workbook
from io import BytesIO
from json import loads


@admin.register(UserNotification)
class UserNotificationAdmin(admin.ModelAdmin):
    pass


@admin.register(UserNotificationRecord)
class UserNotificationRecordAdmin(admin.ModelAdmin):
    list_display = (
        'is_acknowledged',
        'uid',
        'notification',
        'is_active',
        'is_excluded',
        'is_completed',
        'completed',)
    list_display_links = ('uid',)
    list_filter = ('notification', 'is_active', 'is_excluded', 'is_completed', 'completed', 'is_acknowledged')
    search_fields = ('uid',)
    date_hierarchy = 'completed'
    save_on_top = True
    fields = ['notification', 'uid', 'is_acknowledged', 'is_active', 'is_excluded', 'is_completed', 'refreshed',
              'completed', 'display_answer', ]
    readonly_fields = ['is_completed', 'refreshed', 'completed', 'display_answer']
    actions = ['acknowledge_records', 'export_to_excel']

    def acknowledge_records(modeladmin, request, queryset):
        queryset.update(acknowledged='p')

    def export_to_excel(self, request, queryset):
        column_keys = ['datetime', 'notification', 'uid']
        column_formats = {
            'datetime': dict(title=u'Date Time', width=16),
            'notification': dict(title=u'Notification', width=15),
            'uid': dict(title=u'UID', width=16)
        }
        rows = []
        for record in queryset.all():
            row = dict(datetime='', notification=record.notification.name, uid=record.uid)
            if record.completed:
                row['datetime'] = record.completed.strftime('%d.%m.%Y %H:%M')
            if record.json_result:
                json_data = loads(record.json_result)
                for key in json_data:
                    if key not in column_keys:
                        column_keys.append(key)
                    if key not in column_formats:
                        column_formats[key] = dict(title=key.title(), width=len(json_data[key]) + 2)
                    else:
                        if column_formats[key]['width'] < len(json_data[key]) + 2:
                            column_formats[key]['width'] = len(json_data[key]) + 2
                    row[key] = json_data[key]
            rows.append(row)

        output = BytesIO()
        workbook = Workbook(output, {'in_memory': True})
        header_format = workbook.add_format(
            properties={
                'bg_color': 'yellow',
                'border_color': 'black',
                'border': 1,
                'text_wrap': True,
                'valign': 'top'})
        worksheet = workbook.add_worksheet(u'Records')
        worksheet.write_row(0, 0, [column_formats[key]['title'] for key in column_keys], header_format)
        index = 0
        while index < len(column_keys):
            worksheet.set_column(index, index, column_formats[column_keys[index]]['width'])
            index += 1
        index = 1
        for data in rows:
            worksheet.write_row(index, 0, [data[key] if key in data else '' for key in column_keys])
            index += 1
        workbook.close()
        output.seek(0)
        response = HttpResponse(output.read(),
                                content_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet")
        response['Content-Disposition'] = 'attachment; filename="User Notification Records.xlsx"'
        return response

    acknowledge_records.short_description = u'Acknowledge records'
    export_to_excel.short_description = u'Export to *.xlsx'
