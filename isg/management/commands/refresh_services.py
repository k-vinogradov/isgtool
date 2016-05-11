# -*- coding: utf-8 -*-

from datetime import datetime
from django.core.management.base import BaseCommand
from isg.libcache import lock_coa, unlock_coa, coa_is_locked
from isgtool.contrib import log
from time import sleep
from www.models import UserNotificationRecord
from django.conf import settings

class Command(BaseCommand):
    help = 'Send CoA for service activation'

    def add_arguments(self, parser):
        parser.add_argument('-l', '--limit', type=int, dest='limit', default=0, metavar='LIMIT',
                            help='Limit uid list size')

    def handle(self, *args, **options):
        logger = log(self)
        logger.info('Start services refresh')
        counter = 0
        skipped = 0
        failed = 0

        qs = UserNotificationRecord.objects.get_active().filter(is_completed=False)
        if options['limit'] > 0:
            qs = qs[:options['limit']]

        logger.info('Waiting for CoA is unlocked...')
        while coa_is_locked():
            sleep(0.2)
        lock_coa()
        for record in qs:

            if counter > 0 and counter % settings.COA_BLOCK_SIZE == 0:
                unlock_coa()
                logger.info('Records are refreshed: {}. Waiting for the next block...'.format(counter))
                sleep(settings.COA_BLOCK_DELAY)
                logger.info('Waiting for CoA is unlocked...')
                while coa_is_locked():
                    sleep(0.2)
                lock_coa()

            return_code = record.notification.coa.run(record.uid)
            sleep(settings.COA_MESSAGE_INTERVAL)
            if return_code is None:
                skipped += 1
            elif return_code == 0:
                counter += 1
                failed += 1
            else:
                counter += 1
                record.refreshed = datetime.now()
                record.save()
        unlock_coa()
        logger.info('Services refresh finished')