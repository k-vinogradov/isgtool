# -*- coding: utf-8 -*-

from django.core.management.base import BaseCommand
from equipment.models import Bras
from isgtool.contrib import log


class Command(BaseCommand):
    help = 'Update AAA sessions list'

    def handle(self, *args, **options):
        logger = log(self)
        logger.info('Run session cache update job.')
        for bras in Bras.objects.filter(is_active=True):
            logger.info(u'Run session list update procedure from bras \'{0}\''.format(bras.name))
            bras.aaa_list_update()
        logger.info(u'Sessions update job complete.')
