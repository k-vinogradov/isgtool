# -*- coding: utf-8 -*-

import logging
import memcache

from django.core.cache import cache
from datetime import datetime
from django.conf import settings

PENDING_COA_LOCK_KEY = 'PEINDONG-COA-JOB-RUNNING'

BRAS_POSTFIX = '.brass'
SESSION_POSTFIX = '.session'
USER_POSTFIX = '.user'
BRAS_CACHE_UPDATE_POSTFIX = '.bras-key-updated'
TOTAL_COA_COUNTER_KEY = 'total-isg-coa-counter'
SUCCESS_COA_COUNTER_KEY = 'success-isg-coa-counter'
FAILED_COA_COUNTER_KEY = 'failed-isg-coa-counter'

LAST_COA_AAA_ID = '{uid}.{coa_id}.last_coa_aaa_id'
LAST_COA_AAA_ID_TIMEOUT = 86400


class IsgCache:
    def __init__(self):
        self._data = {}
        self._cache = cache
        self._mc = memcache.Client((settings.CACHES['default']['LOCATION'],))
        pass

    def get_stats(self):
        stats = self._mc.get_stats()[0][1]
        for key in stats:
            try:
                stats[key] = int(stats[key])
            except ValueError:
                pass
        return stats

    def prepare_data(self, **kwargs):
        for key in kwargs:
            self._data[key] = kwargs[key]

    def prepare_session_data(self, bras, session_id, user_id, ip_address):
        data = {
            user_id + BRAS_POSTFIX: bras.id,
            user_id + SESSION_POSTFIX: session_id,
            ip_address + USER_POSTFIX: user_id
        }
        return self.prepare_data(**data)

    def save(self):
        self._cache.set_many(self._data)
        self._data = {}

    def get_session_info(self, user_id):
        from equipment.models import Bras
        session_info = self._cache.get_many([user_id + BRAS_POSTFIX, user_id + SESSION_POSTFIX])
        if session_info:
            try:
                bras = Bras.objects.get_by_ip(session_info[user_id + BRAS_POSTFIX])
            except Bras.DoesNotExist:
                logger = logging.getLogger(__name__)
                logger.error(u'Bras ID \'{0}\' doesn\'t exist'.format(session_info[user_id + BRAS_POSTFIX]))
                return None
            return {
                'user_id': user_id,
                'bras': bras,
                'session_id': session_info[user_id + SESSION_POSTFIX], }
        else:
            return None

    def get_user_id(self, ip_address=None):
        if ip_address:
            return self._cache.get(ip_address + USER_POSTFIX)
        else:
            return None

    def increase_coa_counter(self, success=True):
        key = SUCCESS_COA_COUNTER_KEY if success else FAILED_COA_COUNTER_KEY
        if self._cache.get(TOTAL_COA_COUNTER_KEY):
            self._cache.incr(TOTAL_COA_COUNTER_KEY)
        else:
            self._cache.set(TOTAL_COA_COUNTER_KEY, 1, None)
        if self._cache.get(key):
            self._cache.incr(key)
        else:
            self._cache.set(key, 1, 0)

    def coa_counters(self):
        cached = self._cache.get_many([TOTAL_COA_COUNTER_KEY, SUCCESS_COA_COUNTER_KEY, FAILED_COA_COUNTER_KEY])
        return (
            cached[TOTAL_COA_COUNTER_KEY] if TOTAL_COA_COUNTER_KEY in cached else 0,
            cached[SUCCESS_COA_COUNTER_KEY] if SUCCESS_COA_COUNTER_KEY in cached else 0,
            cached[FAILED_COA_COUNTER_KEY] if FAILED_COA_COUNTER_KEY in cached else 0,)

    def set_bras_last_update(self, bras):
        self._cache.set('{0}{1}'.format(bras.name, BRAS_CACHE_UPDATE_POSTFIX), datetime.now().strftime('%c'))

    def get_bras_last_update(self, bras):
        result = self._cache.get('{0}{1}'.format(bras.name, BRAS_CACHE_UPDATE_POSTFIX))
        return result if result else 'Never'

    def lock_pending_coa(self):
        self._cache.set(PENDING_COA_LOCK_KEY, True, None)

    def unlock_pending_coa(self):
        self._cache.set(PENDING_COA_LOCK_KEY, False, None)

    def get_pending_coa(self):
        return self._cache.get(PENDING_COA_LOCK_KEY)

    def set_last_coa_aaa_id(self, uid, coa, session_id):
        return self._cache.set(LAST_COA_AAA_ID.format(uid=uid, coa_id=coa.id), session_id, LAST_COA_AAA_ID_TIMEOUT)

    def check_last_coa_aaa_id(self, uid, coa, session_id):
        if self._cache.get(LAST_COA_AAA_ID.format(uid=uid, coa_id=coa.id)) == session_id:
            return True
        else:
            return False
