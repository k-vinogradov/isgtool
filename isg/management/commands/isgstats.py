# -*- coding: utf-8 -*-

import curses, traceback, sys
from django.core.management.base import BaseCommand
from isg.libcache import cache_stats, coa_counter, get_bras_last_update
from isg.models import Bras, CoaQueue
from os import getloadavg
from time import time, sleep
from www.models import UserNotificationRecord

SCREEN_TEMPLATE = '''
 -----------------------------------------------------
  ISG Tool On-Line Stats
  Bug-Report: mail@k-vinogradov.ru
 ------------------------------------------------------
  Load Average:  {la}

  CoA Message Counter: {cm:<15}   {cmps:<4.2f} msg/sec
  CoA Queue Size: {cq}

                      CACHE STATS
 -------------------------------------------------------
  BRAS                        Last Cache Update
 -------------------------------------------------------
{bras}

  Total items cached: {mi}

  Cache set commands: {ms:<15} {msps:.2f} cmd/sec
  Cache get commands: {mg:<15} {mgps:.2f} cmd/sec

  Active notifications are completed: {nc} ({ncp:.2f}%)

  Press key: Q - quit.
'''

REFRESH_DELAY = 2.00


class Command(BaseCommand):
    help = 'Show ISG Tool stats'

    def __init__(self):
        super(Command, self).__init__()
        self.previos_time = 0.00
        self.previos_cm = 0
        self.previos_ms = 0
        self.previos_ms = 0
        self.previos_mg = 0

    def add_arguments(self, parser):
        parser.add_argument('-z', '--zenoss', dest='zenoss', action='store_true',
                            help='Zenoss data source syntax')
        parser.add_argument('-s', '--screen', dest='screen', action='store_true',
                            help='Show performance stats screen')

    def screen(self):
        bras_stats = ''
        for bras in Bras.objects.active():
            bras_stats += ' {0}: {1} sessions were cached at {2}'.format(bras.name, bras.last_update_sessions(),
                                                                         bras.last_update_datetime())
        current_time = time()
        delta = current_time - self.previos_time
        cm = coa_counter()
        stats = cache_stats()
        completed_notifications_num = UserNotificationRecord.objects.filter(is_completed=True).count()
        notifications_num = UserNotificationRecord.objects.count()
        result = SCREEN_TEMPLATE.format(
            cm=cm,
            cmps=(cm - self.previos_cm) / delta,
            cq=CoaQueue.objects.all().count(),
            bras=bras_stats,
            mi=stats['curr_items'],
            ms=stats['cmd_set'],
            msps=(stats['cmd_set'] - self.previos_ms) / delta,
            mg=stats['cmd_get'],
            mgps=(stats['cmd_get'] - self.previos_mg) / delta,
            la='  '.join(map(str, getloadavg())),
            nc=completed_notifications_num,
            ncp=completed_notifications_num / notifications_num * 100
        )
        self.previos_time = current_time
        self.previos_cm = cm
        self.previos_mg = stats['cmd_get']
        self.previos_ms = stats['cmd_set']
        return result

    def handle(self, *args, **options):
        stats = cache_stats()
        stats['coa_counter'] = coa_counter()

        if options['zenoss']:
            formatted_stats = 'OK | ' + ' '.join(['{0}={1}'.format(key, stats[key]) for key in stats])
            print(formatted_stats)
        elif options['screen']:
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
        else:
            for key in stats:
                print ('{0} : {1}'.format(key, stats[key]))
