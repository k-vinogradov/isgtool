# -*- coding: utf-8 -*-

import memcache

from django.core.cache import cache
from datetime import datetime
from django.conf import settings

UID_BY_IP_TEMPLATE = 'uid_by_ip_{0}'
SESSION_BY_UID_TEMPLATE = 'session_by_uid_{0}'
COA_LOCK_KEY = 'coa_lock'
COA_COUTER_KEY = 'coa_counter'
COA_SID_TEMPLATE = 'sid_from_cid_{cid}_for_uid_{uid}'

BRAS_UPDATED_TIME = 'bras_{0}_updated_time'
BRAS_UPDATED_SESSIONS = 'bras_{0}_updated_sessions'


def cache_session_data(session_data):
    if type(session_data) == dict:
        session_data = [session_data, ]
    cache_data = {}
    for session in session_data:
        ip = session['ip']
        bid = session['bid']
        uid = session['uid']
        sid = session['sid']
        uid_by_ip_key = UID_BY_IP_TEMPLATE.format(ip)
        session_by_uid_key = SESSION_BY_UID_TEMPLATE.format(uid)
        session_detail = ' '.join([bid, sid])
        cache_data[uid_by_ip_key] = uid
        cache_data[session_by_uid_key] = session_detail
    cache.set_many(cache_data)


def get_uid(ip):
    if settings.DEBUG and ip == '127.0.0.1':
        return settings.DEBUG_UID
    else:
        key = UID_BY_IP_TEMPLATE.format(ip)
        return cache.get(key)


def get_session_detail(uid):
    key = SESSION_BY_UID_TEMPLATE.format(uid)
    session_detail = cache.get(key)
    if session_detail:
        return session_detail.split(' ')
    else:
        return [None, None]


def lock_coa():
    cache.set(COA_LOCK_KEY, True, None)


def unlock_coa():
    cache.set(COA_LOCK_KEY, False, None)


def coa_is_locked():
    return cache.get(COA_LOCK_KEY)


def cache_stats():
    mc = memcache.Client((settings.CACHES['default']['LOCATION'],))
    stats = mc.get_stats()[0][1]
    for key in stats:
        try:
            stats[key] = int(stats[key])
        except ValueError:
            pass
    return stats


def increase_coa_counter():
    if cache.get(COA_COUTER_KEY):
        cache.incr(COA_COUTER_KEY)
    else:
        cache.set(COA_COUTER_KEY, 1, None)


def coa_counter():
    counter = cache.get(COA_COUTER_KEY)
    if counter:
        return int(counter)
    else:
        return 0


def set_bras_last_update(bid, sessions):
    time_key = BRAS_UPDATED_TIME.format(bid)
    sessions_key = BRAS_UPDATED_SESSIONS.format(bid)
    cache.set_many({time_key: datetime.now(), sessions_key: sessions}, None)


def get_bras_last_update(bid):
    time_key = BRAS_UPDATED_TIME.format(bid)
    sessions_key = BRAS_UPDATED_SESSIONS.format(bid)
    return cache.get(time_key), cache.get(sessions_key)


def set_coa_sid(cid, uid, sid):
    cache.set(COA_SID_TEMPLATE.format(cid=cid, uid=uid), sid)


def get_last_coa_sid(cid, uid):
    return cache.get(COA_SID_TEMPLATE.format(cid=cid, uid=uid))
