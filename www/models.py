# -*- coding: utf-8 -*-

from django.db import models
from django.core.exceptions import ValidationError
from django.conf import settings
from equipment.models import CoaCommand, CoaQueue
from isgtool.contrib import log


class UserNotification(models.Model):
    name = models.CharField(max_length=255, verbose_name=u'Name')
    template = models.CharField(max_length=255, verbose_name=u'Notification Template')
    answers = models.TextField(verbose_name=u'Answers',
                               help_text=u'Syntax: ID:Answer (example: 1:Yes). One option per line')
    successful_coa = models.ForeignKey(CoaCommand, verbose_name=u'Successful CoA',
                                       limit_choices_to={'is_active': True})
    is_active = models.BooleanField(default=False, verbose_name=u'Is Active')

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

    def answer_dict(self):
        result = {}
        for raw_line in self.answers.split(u'\n'):
            line = raw_line.strip()
            if u':' in line:
                a_list = line.split(u':')
                result[a_list[0]] = a_list[1]
        return result

    def display_answer(self, code):
        a_dict = self.answer_dict()
        if code in a_dict:
            return a_dict[code]
        else:
            return u'Unknown code'


class UserNotificationRecord(models.Model):
    notification = models.ForeignKey('UserNotification', verbose_name=u'Notification Template')
    user_id = models.CharField(max_length=255, verbose_name=u'User ID')
    completed = models.BooleanField(default=False, verbose_name=u'Completed')
    answer = models.CharField(max_length=255, verbose_name=u'Answer')
    seen_datetime = models.DateTimeField(verbose_name=u'Seen', auto_now_add=True)
    complete_datetime = models.DateTimeField(verbose_name=u'Answered', blank=True, null=True)
    acknowledged = models.BooleanField(default=False, verbose_name=u'Ack')

    def display_answer(self):
        if self.completed:
            return self.notification.display_answer(self.answer)
        else:
            return u'N/A'

    def save(self, *args, **kwargs):
        logger = log(self)
        if not self.id:
            logger.info(u'Notification (user ID {0}, notification \'{1}\') created.'.format(self.user_id,
                                                                                            self.notification.name))
        if self.completed and not self.acknowledged:
            logger.info(u'Notification #{0} (user ID {1}, notification \'{2}\') completed.'.format(
                self.id,
                self.user_id,
                self.notification.name))
            if settings.PENDING_COA:
                CoaQueue.objects.create(coa=self.notification.successful_coa, user_id=self.user_id)
            else:
                self.notification.successful_coa.run(self.user_id)
        return super(UserNotificationRecord, self).save(*args, **kwargs)
