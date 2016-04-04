# -*- coding: utf-8 -*-

from django.core.management.base import BaseCommand
from django.db.utils import IntegrityError
from isgtool.contrib import log
from www.models import UserNotificationRecord, UserNotification


class Command(BaseCommand):
    help = 'Import user notification records'

    def add_arguments(self, parser):
        parser.add_argument('file_name', help='UID list\'s file name')

    def handle(self, *args, **options):
        logger = log(self)
        logger.info(u'Start records import')
        notification = UserNotification.objects.get_active()
        logger.info(u'Active notification: {}'.format(notification.name))
        counter = 0
        for line in open(options['file_name']):
            uid = line.strip()
            logger.debug(u'Create record for the UID {}'.format(uid))
            try:
                record = UserNotificationRecord.objects.create(uid=uid, notification=notification)
            except IntegrityError:
                logger.debug(u'UID {} already exists'.format(uid))
            else:
                logger.debug(u'Create record #{0} for the UID {1}'.format(record.id, uid))
                counter += 1

        logger.info(u'Records import finished. {0} new items were imported.'.format(counter))