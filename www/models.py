# -*- coding: utf-8 -*-

from django.core.cache import cache
from django.db import models
from django.core.exceptions import ValidationError
from isg.models import CoaCommand, CoaQueue
from isgtool.contrib import log
from json import loads


class UserNotificationManager(models.Manager):
    ACTIVE_KEY = 'active-notification'

    def get_active(self):
        active = cache.get(self.ACTIVE_KEY)
        if active:
            return active
        else:
            active = self.get(is_active=True)
            cache.set(self.ACTIVE_KEY, active, None)
            return active


class UserNotification(models.Model):
    name = models.CharField(max_length=255, verbose_name=u'Name')
    template = models.CharField(max_length=255, verbose_name=u'Notification Template')
    coa = models.ForeignKey(CoaCommand, verbose_name=u'Initialisation CoA', limit_choices_to={'is_active': True},
                            related_name='main_coa')
    successful_coa = models.ForeignKey(CoaCommand, verbose_name=u'Successful CoA', limit_choices_to={'is_active': True},
                                       related_name='success_coa')
    is_active = models.BooleanField(default=False, verbose_name=u'Is Active')

    objects = UserNotificationManager()

    # TODO Override self.save(...) for active cache update

    class Meta:
        ordering = ('name',)

    def __unicode__(self):
        if self.id:
            return self.name
        else:
            return u'New Notification Template'

    def clean(self):
        super(UserNotification, self).clean()
        if self.is_active:
            qs = UserNotification.objects.filter(is_active=True)
            if self.id:
                qs = qs.exclude(id=self.id)
            if qs.exists():
                raise ValidationError('Only one notification template can be active at the same time.')


RECORD_KEY_TEMPLATE = 'record_{uid}_{nid}'
RECORD_ID_KEY_TEMPLATE = 'record_id_{id}'


class UserNotificationRecordManager(models.Manager):
    def get_by_uid(self, uid, notification=None):
        if not notification:
            notification = UserNotification.objects.get_active()
        key = RECORD_KEY_TEMPLATE.format(uid=uid, nid=notification.id)
        record = cache.get(key)
        if record:
            return record
        else:
            record = self.get(uid=uid, notification=notification)
            record.update_cache()
            return record

    def get_by_id(self, id):
        key = RECORD_ID_KEY_TEMPLATE.format(id=id)
        record = cache.get(key)
        if record:
            return record
        else:
            record = self.get(id=id)
            record.update_cache()
            return record


class UserNotificationRecord(models.Model):
    notification = models.ForeignKey('UserNotification', verbose_name=u'Notification Template')
    uid = models.CharField(max_length=255, verbose_name=u'User ID')
    refreshed = models.DateTimeField(verbose_name=u'Refreshed', blank=True, null=True)
    completed = models.DateTimeField(verbose_name=u'Completed', blank=True, null=True)
    json_result = models.TextField(verbose_name=u'JSON Result', blank=True, null=True)
    is_completed = models.BooleanField(default=False, verbose_name=u'Completed')
    is_acknowledged = models.BooleanField(default=False, verbose_name=u'Ack')

    objects = UserNotificationRecordManager()

    class Meta:
        unique_together = ['notification', 'uid']

    def complete(self, result):
        logger = log(self)
        if not self.is_acknowledged:
            logger.info(u'Notification #{0} UID{1} is completed.'.format(self.id, self.uid))
        self.json_result = result
        self.is_completed = True
        self.save()
        CoaQueue.objects.create(coa=self.notification.successful_coa, uid=self.uid)

    def update_cache(self):
        key1 = RECORD_KEY_TEMPLATE.format(uid=self.uid, nid=self.notification.id)
        key2 = RECORD_ID_KEY_TEMPLATE.format(id=self.id)
        cache.set_many({key1: self, key2: self})

    def save(self, *args, **kwargs):
        super(UserNotificationRecord, self).save(*args, **kwargs)
        self.update_cache()

    def display_answer(self):
        if self.json_result:
            result = loads(self.json_result)
            return ', \n'.join(['{0}: {1}'.format(key, result[key]) for key in result])
        else:
            return '-'
