# -*- coding: utf-8 -*-

from datetime import datetime
from django.conf import settings
from django.core.urlresolvers import reverse_lazy
from django.http import HttpResponseRedirect, Http404
from django.shortcuts import render_to_response
from django.template import RequestContext
from django.views.generic import TemplateView
from isg.libcache import get_uid
from isgtool.contrib import log
from json import dumps
from www.models import UserNotification, UserNotificationRecord


def handler404(request):
    response = render_to_response('404.html', {},
                                  context_instance=RequestContext(request))
    response.status_code = 404
    return response


def raise_exception(error):
    if settings.DEBUG:
        if isinstance(error, Exception) or error is Http404:
            raise error
        else:
            raise BaseException(error)
    else:
        raise Http404


def redirect(request):
    if 'sib.transtk.ru' in request.get_host():
        url = '/admin/'
    else:
        url = '/sttk-notification/'
    return HttpResponseRedirect(url)


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
        except UserNotification.DoesNotExist as ex:
            self.logger.critical(u'Active notification doesn\'t exist.')
            raise_exception(ex)

    def get_template_names(self):
        return [self.notification.template + '/notification.html']

    def get_context_data(self, **kwargs):
        context = super(NotificationView, self).get_context_data(**kwargs)
        uid = get_uid(self.request.META['REMOTE_ADDR'])
        if uid:
            try:
                record = UserNotificationRecord.objects.get_by_uid(uid, self.notification)
                if record.is_completed:
                    raise_exception(Http404)
            except UserNotificationRecord.DoesNotExist as ex:
                self.logger.error(
                    u'Not notification record for the UID \'{0}\' ({1})'.format(uid, self.notification.name))
                raise_exception(ex)
            else:
                context['rid'] = record.id
                context['answer_url'] = reverse_lazy('answer_view')
                return context
        else:
            self.logger.error(u'No cached session info with IP {0}'.format(self.request.META['REMOTE_ADDR']))
            raise_exception(u'No cached session info with IP {0}'.format(self.request.META['REMOTE_ADDR']))


class AnswerView(TemplateView):
    def __init__(self):
        super(AnswerView, self).__init__()
        self.logger = log(self)
        try:
            self.notification = UserNotification.objects.get_active()
        except UserNotification.DoesNotExist as ex:
            self.logger.critical(u'Active notification doesn\'t exist.')
            raise_exception(ex)

    def get_template_names(self):
        return [self.notification.template + '/answer.html']

    def get_context_data(self, **kwargs):
        try:
            record = UserNotificationRecord.objects.get_by_id(self.request.GET['rid'])
            if record.is_completed:
                self.logger.debug(
                    u'Notification {0} for user \{1}\ already has been completed'.format(record.id, record.uid))
                raise_exception(
                    u'Notification {0} for user \{1}\ already has been completed'.format(record.id, record.uid))
            record.complete(dumps(self.request.GET))
        except KeyError as ex:
            self.logger.error('Invalid GET query.')
            raise_exception(ex)
        except UserNotificationRecord.DoesNotExist as ex:
            self.logger.error('Invalid notification record ID {}'.format(self.request.GET['rid']))
            raise_exception(ex)
        context = super(AnswerView, self).get_context_data(**kwargs)
        context.update(self.request.GET)
        return context
