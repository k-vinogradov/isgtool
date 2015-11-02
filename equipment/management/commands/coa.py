# -*- coding: utf-8 -*-

from django.core.management.base import BaseCommand
from equipment.models import CoaCommand
from isgtool.contrib import log
from equipment.isg_cache import IsgCache
from www.models import UserNotification, UserNotificationRecord
from time import sleep

BLOCK_SIZE = 500
BLOCK_DELAY = 10


class Command(BaseCommand):
    help = 'Send CoA Request'

    def add_arguments(self, parser):
        parser.add_argument('-c', '--coa', type=str, dest='coa', required=True, metavar='COA',
                            help='Type of CoA-command')
        parser.add_argument('-u', '--user_id', type=str, dest='user_id', default=None, metavar='USER_ID',
                            help='Specified user ID')
        parser.add_argument('-f', '--file', type=str, dest='file', default=None, metavar='FILE',
                            help='Path to the file which contains user ID list.')
        parser.add_argument('-n', '--notification', type=str, dest='notification', default=None, metavar='NOTIFICATION',
                            help='Notification class. User ID which already have been completed for this class '
                                 'will be ignored.')
        parser.add_argument('-l', '--limit', type=int, dest='limit', default=0, metavar='LIMIT',
                            help='Limit uid list size')

    def handle(self, *args, **options):

        logger = log(self)
        logger.info(u'Run CoA-commands job.')
        user_ids = []
        try:
            coa = CoaCommand.objects.get(name=options['coa'])
        except CoaCommand.DoesNotExist:
            logger.error(u'CoA-command \'{0}\' doesn\'t exist.'.format(options['coa'].decode('utf-8')))
            return None
        if options['notification']:
            try:
                notification = UserNotification.objects.get(name=options['notification'])
            except UserNotification.DoesNotExist:
                logger.error(u'Notification \'{0}\' doen\'t exist.'.format(options['notification']))
                return None
        else:
            notification = None
        if options['user_id']:
            user_ids.append(options['user_id'])
        elif options['file']:
            try:
                user_ids = list(open(options['file']))
            except IOError as e:
                logger.error(u'{0}: {1}'.format(e.strerror, e.filename))
                return None
            user_ids = map(lambda s: s.strip(), user_ids)
        if options['limit'] > 0:
            user_ids = user_ids[0:options['limit']]
        if len(user_ids) == 0:
            logger.error(u'No user IDs was sent.')
            return None
        else:
            logger.info(u'Total user ID(s): {0}'.format(len(user_ids)))
            cache = IsgCache()
            if notification:
                completed = UserNotificationRecord.objects.filter(completed=True, user_id__in=user_ids).values_list(
                    'user_id', flat=True)
                user_ids = [uid for uid in user_ids if uid not in completed]
                logger.info(u'Uncompleted notification(s): {0}.'.format(len(user_ids)))
            logger.info(u'Execute CoA command(s) for {0} user ID(s).'.format(len(user_ids)))
            success = 0
            failed = 0
            counter = 0
            block = []
            offline = 0
            already_ran = 0
            wait = False
            process_block = False
            for uid in user_ids:
                if len(block) == BLOCK_SIZE or counter == len(user_ids):

                    if wait:
                        logger.info(u'Waite the next block.')
                        sleep(BLOCK_DELAY)
                    wait = True

                    logger.info(
                        u'Processing next block which contains {0} uid(s). Counter: {1} of {2}.'.format(len(block),
                                                                                                        counter,
                                                                                                        len(user_ids)))

                    if cache.get_pending_coa():
                        logger.info(u'Waite pending coa unlocking.')
                    while cache.get_pending_coa():
                        sleep(0.1)

                    cache.lock_pending_coa()
                    for uid2 in block:
                        sleep(0.05)
                        if coa.run(uid2, log_level='debug'):
                            success += 1
                        else:
                            failed += 1
                    cache.unlock_pending_coa()

                    block = []
                    process_block = False

                counter += 1

                session_info = cache.get_session_info(uid)
                if not session_info:
                    offline += 1
                    continue
                if cache.check_last_coa_aaa_id(uid, coa, session_info['session_id']):
                    already_ran += 1
                    continue
                if UserNotificationRecord.objects.filter(completed=True, user_id=uid).exists():
                    already_ran += 1
                    continue

                block.append(uid)
                process_block = True

            if process_block:
                if wait:
                    logger.info(u'Waite the next block.')
                    sleep(BLOCK_DELAY)

                logger.info(
                    u'Processing next block which contains {0} uid(s). Counter: {1} of {2}.'.format(len(block),
                                                                                                    counter,
                                                                                                    len(user_ids)))

                if cache.get_pending_coa():
                    logger.info(u'Waite pending coa unlocking.')
                while cache.get_pending_coa():
                    sleep(0.1)

                cache.lock_pending_coa()
                for uid2 in block:
                    sleep(0.05)
                    if coa.run(uid2, log_level='debug'):
                        success += 1
                    else:
                        failed += 1
                cache.unlock_pending_coa()

            logger.info(
                u'CoA command(s) executed: offline: {offline}, skipped: {skipped}, '
                u'sent {sent}, successfully {success}, failed {failed}.'.format(
                    offline=offline,
                    skipped=already_ran,
                    sent=success + failed,
                    success=success,
                    failed=failed))
            logger.info(u'Finish CoA job.')
