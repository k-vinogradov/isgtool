# -*- coding: utf-8 -*-

import os, sys, traceback
import curses
from time import time, sleep
from equipment.isg_cache import IsgCache
from equipment.models import Bras, CoaQueue
from www.models import UserNotification, UserNotificationRecord
from django.core.management.base import BaseCommand

REFRESH_DELAY = 2.00

'''
EXAMPLE:
 -----------------------------------------------------
  ISG Tool On-Line Stats
 ------------------------------------------------------
  Load Average:  0.00  0.00  0.00

               CHANGE OF AUTHTORIZATION
 ------------------------------------------------------
  Requests                 Counter         Per-Second
 ------------------------------------------------------
  Success                  332446356       340
  Failed                   3346234         34
  Total                    434634234       374

  CoA Queue Size: 132

                      CACHE STATS
 -------------------------------------------------------
  BRAS                        Last cache update
 -------------------------------------------------------
  ks36-m                      Sun Oct 25 13:24:10 2015
  abk19-p78a                  Never

 ------------------------------------------------------
  Requests              Counter            Per-Second
 ------------------------------------------------------
  Total Items           332446344456       340
  Set Commands          3346234444         34
  Get Commands          434644434234       374

                  NOTIFICATION STATS
 ------------------------------------------------------
  Notification                Seen         Completed
 ------------------------------------------------------
  Плюс 100                    31415        2323

  Press key: Q - quit.
'''

SCREEN_TEPLATE = u'''
 -----------------------------------------------------
  ISG Tool On-Line Stats v.0.1
  Bug-Report: mail@k-vinogradov.ru
 ------------------------------------------------------
  Load Average:  {load_average}

               CHANGE OF AUTHORIZATION
 ------------------------------------------------------
  Requests                 Counter         Per-Second
 ------------------------------------------------------
  Success                  {success_coa:<15} {success_coa_ps:.2f}
  Failed                   {failed_coa:<15} {failed_coa_ps:.2f}
  Total                    {total_coa:<15} {total_coa_ps:.2f}

  CoA Queue Size: {coa_queue_size}

                      CACHE STATS
 -------------------------------------------------------
  BRAS                        Last Cache Update
 -------------------------------------------------------
{bras_stats}

 ------------------------------------------------------
  Requests              Counter            Per-Second
 ------------------------------------------------------
  Total Items           {memcache_items:<18}
  Set Commands          {memcache_set:<18} {memcache_set_ps:.2f}
  Get Commands          {memcache_get:<18} {memcache_get_ps:.2f}

                  NOTIFICATION STATS
 ------------------------------------------------------
  Notification                Seen         Completed
 ------------------------------------------------------
{notification_stats}

  Press key: Q - quit.
'''

BRAS_ROW_TEMPLATE = u'  {name:<27} {datetime}'
NOTIFICATION_TEMPLATE = u'  {name:<27} {seen:<12} {completed}'


class Command(BaseCommand):
    def __init__(self, *args, **kwargs):
        super(Command, self).__init__(*args, **kwargs)
        self._prev_time = None
        self._success_coa = 0
        self._failed_coa = 0
        self._total_coa = 0
        self._memcache_set = 0
        self._memcache_get = 0

    def screen(self):
        params = {}

        cache = IsgCache()

        bras_stats = []
        for bras in Bras.objects.all():
            name = u'{0}*'.format(bras.name) if bras.is_active else bras.name
            bras_stats.append(BRAS_ROW_TEMPLATE.format(name=name, datetime=cache.get_bras_last_update(bras)))

        params['bras_stats'] = '\n'.join(bras_stats)

        notification_stats = []
        for notification in UserNotification.objects.all():
            name = u'{0}*'.format(notification.name) if notification.is_active else notification.name
            seen = UserNotificationRecord.objects.filter(notification=notification).count()
            completed = UserNotificationRecord.objects.filter(notification=notification, completed=True).count()
            notification_stats.append(NOTIFICATION_TEMPLATE.format(name=name, seen=seen, completed=completed))

        params['notification_stats'] = '\n'.join(notification_stats)

        prev_time = self._prev_time
        self._prev_time = time()

        coa_stats = cache.coa_counters()
        cache_stats = cache.get_stats()
        params['total_coa'] = coa_stats[0]
        params['success_coa'] = coa_stats[1]
        params['failed_coa'] = coa_stats[2]

        params['total_coa_ps'] = 0.0
        params['success_coa_ps'] = 0.0
        params['failed_coa_ps'] = 0.0

        params['memcache_items'] = cache_stats['curr_items']
        params['memcache_set'] = cache_stats['cmd_set']
        params['memcache_get'] = cache_stats['cmd_get']

        params['memcache_set_ps'] = 0.0
        params['memcache_get_ps'] = 0.0

        if prev_time:
            if self._total_coa:
                params['total_coa_ps'] = (params['total_coa'] - self._total_coa) / (self._prev_time - prev_time)
            if self._success_coa:
                params['success_coa_ps'] = (params['success_coa'] - self._success_coa) / (self._prev_time - prev_time)
            if self._failed_coa:
                params['failed_coa_ps'] = (params['failed_coa'] - self._failed_coa) / (self._prev_time - prev_time)
            if self._memcache_get:
                params['memcache_get_ps'] = (params['memcache_get'] - self._memcache_get) / (
                    self._prev_time - prev_time)
            if self._memcache_set:
                params['memcache_set_ps'] = (params['memcache_set'] - self._memcache_set) / (
                    self._prev_time - prev_time)

        self._total_coa = params['total_coa']
        self._success_coa = params['success_coa']
        self._failed_coa = params['failed_coa']

        self._memcache_set = params['memcache_set']
        self._memcache_get = params['memcache_get']

        params['coa_queue_size'] = CoaQueue.objects.all().count()

        params['load_average'] = '  '.join(map(str, os.getloadavg()))

        return SCREEN_TEPLATE.format(**params)

    def handle(self, *args, **options):

        try:
            window = curses.initscr()
            curses.noecho()
            window.clear()
            window.nodelay(True)
        except:
            curses.endwin()
            traceback.print_exc()
            sys.exit(1)

        key_pressed = None
        screen_refreshed = 0.00
        while key_pressed not in ['q', 'Q']:
            if time() - screen_refreshed >= REFRESH_DELAY:
                window.clear()
                try:
                    s = str(self.screen().encode('utf-8'))
                    window.addstr(1, 1, s)
                except:
                    curses.endwin()
                    traceback.print_exc()
                    sys.exit(1)
                screen_refreshed = time()
            try:
                key_pressed = window.getkey()
            except:
                key_pressed = None
            sleep(0.5)
        curses.endwin()
