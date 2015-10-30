# -*- coding: utf-8 -*-

import sys

from django.core.management.base import BaseCommand
from equipment.models import CoaQueue
from django.core.cache import cache
from isgtool.contrib import log
from time import sleep

CACHE_KEY = 'PEINDONG-COA-JOB-RUNNING'


class Command(BaseCommand):
    help = 'Run pending CoA job'

    def handle(self, *args, **options):
        logger = log(self)
        logger.info(u'Pending CoA job started')
        if cache.get(CACHE_KEY):
            logger.error(u'Can\'t run pending CoA job because \'running\' flag is True')
            return None
        else:
            cache.set(CACHE_KEY, True, None)
            try:
                logger.info(u'Pending CoA queue size: {0} record(s)'.format(CoaQueue.objects.all().count()))
                for item in CoaQueue.objects.all():
                    sleep(0.05)
                    item.run()
            except:
                logger.critical(u'PCJ catched exception: [{0}] {1}'.format(*sys.exc_info()))
            logger.info(u'Pending CoA job finished')
            cache.set(CACHE_KEY, False, None)
