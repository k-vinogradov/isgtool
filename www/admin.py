# -*- coding: utf-8 -*-

from django.contrib import admin
from www.models import *


class AnswerFilter(admin.SimpleListFilter):
    title = 'answer'
    parameter_name = 'answer'

    def lookups(self, request, model_admin):
        result = []
        for notification in UserNotification.objects.all():
            a_dict = notification.answer_dict()
            for key in a_dict:
                result.append((
                    '{0}-{1}'.format(notification.id, key),
                    '{0} ({1})'.format(a_dict[key].encode('utf-8'), notification.name.encode('utf-8')),))
        return result

    def queryset(self, request, queryset):
        if self.value():
            notification_id, answer_code = self.value().split('-')
            notification = UserNotification.objects.get(id=notification_id)
            return queryset.filter(notification=notification, answer=answer_code)


def acknowledge_records(modeladmin, request, queryset):
    queryset.update(acknowledged='p')


acknowledge_records.short_description = u'Acknowledged records'


@admin.register(UserNotification)
class UserNotificationAdmin(admin.ModelAdmin):
    pass


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
    list_display_links = ('user_id', )
    list_filter = ('notification', 'completed', AnswerFilter, 'complete_datetime', 'acknowledged')
    search_fields = ('user_id',)
    date_hierarchy = 'complete_datetime'
    # list_editable = ('acknowledged',)
    save_on_top = True
    readonly_fields = ('notification', 'user_id', 'completed', 'answer', 'seen_datetime', 'complete_datetime',)
    actions = [acknowledge_records, ]
