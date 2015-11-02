# -*- coding: utf-8 -*-

from django.views.generic import TemplateView
from django.http import HttpResponseRedirect
from django.core.urlresolvers import reverse_lazy
from django.shortcuts import render_to_response
from django.template import RequestContext
from django.conf import settings
from django.http import Http404
from www.models import UserNotification, UserNotificationRecord
from equipment.isg_cache import IsgCache
from datetime import datetime
from isgtool.contrib import log


def handler404(request):
    response = render_to_response('404.html', {},
                                  context_instance=RequestContext(request))
    response.status_code = 404
    return response


def redirect(request):
    return HttpResponseRedirect(settings.NOTIFICATION_URL)


class TemplatePreView(TemplateView):
    def get_template_names(self):
        if 'template' in self.request.GET:
            return self.request.GET['template']
        else:
            raise Http404

    def get_context_data(self, **kwargs):
        context = super(TemplatePreView, self).get_context_data(**kwargs)
        for key in self.request.GET:
            context[key] = self.request.GET[key]
        return context


class NotificationView(TemplateView):
    def __init__(self):
        super(NotificationView, self).__init__()
        self.logger = log(self)
        try:
            self.notification = UserNotification.objects.get_active()
        except UserNotification.DoesNotExist:
            self.logger.critical(u'Active notification doesn\'t exist.')
            raise Http404

    def get_template_names(self):
        return [self.notification.template + '/notification.html']

    def get_context_data(self, **kwargs):
        context = super(NotificationView, self).get_context_data(**kwargs)
        cache = IsgCache()
        user_id = cache.get_user_id(self.request.META['REMOTE_ADDR'])
        if user_id:
            if UserNotificationRecord.objects.is_completed(user_id):
                self.logger.debug(u'Notification \'{0}\' for user ID \'{1}\' already has been completed'.format(
                    self.notification.name, user_id))
                raise Http404
            if not UserNotificationRecord.objects.status_cached(user_id):
                UserNotificationRecord.objects.get_or_create(user_id=user_id, notification=self.notification)
        else:
            self.logger.error(u'No cached session info with IP {0}'.format(self.request.META['REMOTE_ADDR']))
            raise Http404
        context['user_id'] = user_id
        context['answer_url'] = reverse_lazy('answer_view')
        return context


class AnswerView(TemplateView):
    def __init__(self):
        super(AnswerView, self).__init__()
        self.logger = log(self)
        try:
            self.notification = UserNotification.objects.get_active()
        except UserNotification.DoesNotExist:
            self.logger.critical(u'Active notification doesn\'t exist.')
            raise Http404

    def get_template_names(self):
        return [self.notification.template + '/answer.html']

    def get_context_data(self, **kwargs):
        context = super(AnswerView, self).get_context_data(**kwargs)
        if 'user_id' in self.request.GET:
            user_id = self.request.GET['user_id']
            context['user_id'] = user_id
        else:
            user_id = None
        if 'code' in self.request.GET:
            code = self.request.GET['code']
            context['code'] = code
        else:
            code = None
        if user_id and code:
            if UserNotificationRecord.objects.is_completed(user_id):
                self.logger.debug(u'Notification \'{0}\' for user ID \'{1}\' already has been completed'.format(
                    self.notification.name, user_id))
                raise Http404
            record, created = UserNotificationRecord.objects.get_or_create(user_id=user_id,
                                                                           notification=self.notification)
            if not record.completed:
                record.answer = code
                record.complete_datetime = datetime.now()
                record.completed = True
                record.save()
            else:
                self.logger.error(u'Notification \'{0}\' for user ID \'{1}\' already has been completed'.format(
                    self.notification.name, user_id))
                raise Http404
        else:
            self.logger.error(u'Invalid GET params: {0}'.format(self.request.GET))
            raise Http404

        return context
