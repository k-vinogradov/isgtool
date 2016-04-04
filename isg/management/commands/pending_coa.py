import sys

from django.core.management.base import BaseCommand
from isg.libcache import coa_is_locked, lock_coa, unlock_coa
from isg.models import CoaQueue
from isgtool.contrib import log
from time import sleep


class Command(BaseCommand):
    help = 'Run pending CoA job'

    def handle(self, *args, **options):
        logger = log(self)
        logger.info(u'Pending CoA job started')
        logger.info('Waiting for CoA is unlocked...')
        while coa_is_locked():
            sleep(0.2)
        lock_coa()
        try:
            for coa in CoaQueue.objects.all():
                coa.run()
                sleep(0.05)
        except:
            logger.critical(u'PCJ catched exception: [{0}] {1}'.format(*sys.exc_info()))
        logger.info(u'Pending CoA job finished')
        unlock_coa()
