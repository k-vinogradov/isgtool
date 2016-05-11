# -*- coding: utf-8 -*-

import logging
import subprocess
import telnetlib

from django.db import models
from django.core.cache import cache
from isg.libcache import *
from isgtool.contrib import log


class BrasManager(models.Manager):
    def get_by_ip(self, ip):
        key = 'bras_by_ip_{0}'.format(ip)
        bras = cache.get(key)
        if bras:
            return bras
        else:
            bras = self.get(ip_address=ip)
            cache.set(key, bras, 0)
            return bras

    def active(self):
        return self.filter(is_active=True)


class Bras(models.Model):
    METHODS = (
        ('tln', 'Telnet'),
        ('rsh', 'RShell')
    )

    name = models.CharField(max_length=255, verbose_name=u'Name')
    ip_address = models.CharField(max_length=15, verbose_name=u'IP Address', unique=True)
    is_active = models.BooleanField(default=True, blank=True, verbose_name=u'Is Active')
    username = models.CharField(max_length=255, verbose_name=u'Telnet Username')
    password = models.CharField(max_length=255, verbose_name=u'Telnet Password')
    timeout = models.IntegerField(verbose_name=u'Telnet Timeout', help_text=u'seconds')
    command_prompt = models.CharField(max_length=255, verbose_name=u'Command Prompt')
    coa_secret = models.CharField(max_length=255, verbose_name=u'CoA Secret')
    coa_port = models.IntegerField(verbose_name=u'CoA Port')
    method = models.CharField(max_length=3, verbose_name=u'Method', default='tln', choices=METHODS)

    objects = BrasManager()

    class Meta:
        ordering = ['name']
        verbose_name_plural = u'BRASs'

    def __unicode__(self):
        if self.id:
            return u'{0}'.format(self.name)
        else:
            return u'New BRAS'

    def _telnet_output(self, command):
        tn = telnetlib.Telnet(self.ip_address, 23, self.timeout)
        tn.read_until('TACACS+ Username: ', timeout=self.timeout)
        tn.write('{0}\n'.format(self.username))
        tn.read_until('Password: ', timeout=self.timeout)
        tn.write('{0}\n'.format(self.password))
        tn.read_until(str(self.command_prompt))
        tn.write('terminal length 0\n')
        tn.read_until(str(self.command_prompt))
        tn.write('{0}\n'.format(command))
        result = tn.read_until(str(self.command_prompt))
        tn.write('logout\n')
        tn.close()
        return result

    def _rsh_output(self, command):
        cmd = '/usr/bin/rsh -l rsh {0} {1}'.format(self.ip_address, command)
        p = subprocess.Popen(cmd, stdout=subprocess.PIPE, shell=True)
        (output, error) = p.communicate()
        p.wait()
        return output

    def aaa_list_update(self):
        logger = log(self)
        if self.method == 'tln':
            logger.info(u'Get sessiong list from BRAS \'{0}\' by command-line interface'.format(self.name))
            output = self._telnet_output('show aaa sessions')
        else:
            logger.info(u'Get session list from BRAS \'{0}\' by RShell'.format(self.name))
            output = self._rsh_output('show aaa sessions')
        sessions = []
        counter = 0
        session_id = None
        uid = None
        ip_address = None
        logger.info(u'Parse {} output'.format('telnet' if self.method == 'tln' else 'RShell'))
        for raw_line in output.split('\n'):
            try:
                param, value = raw_line.strip().split(': ')
            except ValueError:
                continue
            if param == 'Session Id':
                session_id = value
                uid = None
                ip_address = None
            elif param == 'User Name' and value != '*not available*':
                uid = value
            elif param == 'IP Address':
                ip_address = value
                if not uid:
                    uid = value
            else:
                continue

            if uid and session_id and ip_address and ip_address != '0.0.0.0':
                counter += 1
                sessions.append(dict(ip=ip_address, uid=uid, bid=self.ip_address, sid='{:X}'.format(int(session_id))))

        logger.info(u'Parsed {0} sessions(s).'.format(counter))

        logger.info(u'Caching query result')
        cache_session_data(sessions)
        set_bras_last_update(self.id, counter)

    def last_update_datetime(self):
        dt, sss = get_bras_last_update(self.id)
        return dt

    def last_update_sessions(self):
        dt, sss = get_bras_last_update(self.id)
        return sss


class CoaCommand(models.Model):
    name = models.CharField(max_length=255, verbose_name=u'Name')
    is_active = models.BooleanField(default=True, blank=True, verbose_name=u'Is Active')
    message = models.TextField(verbose_name=u'RADIUS Message')

    class Meta:
        ordering = ['name']

    def __unicode__(self):
        if self.id:
            return self.name
        else:
            return u'New Command'

    def run(self, uid, log_level='info'):
        logger = log(self)
        log_level = getattr(logging, log_level.upper())
        logger.log(log_level, u'Run CoA \'{0}\' to user ID \'{1}\''.format(self.name, uid))

        bid, sid = get_session_detail(uid)

        if not (bid and sid):
            logger.log(log_level, u'No cached session info for user \'{0}\''.format(uid))
            return None

        bras = Bras.objects.get(ip_address=bid)

        message = self.message.format(user_id=uid, aaa_session_id=sid)
        cmd = 'radclient -x -t 3 -r 1 {bid}:{port} coa {secret}'.format(bid=bid, port=bras.coa_port,
                                                                        secret=bras.coa_secret)
        if get_last_coa_sid(self.id, uid) == sid:
            logger.log(log_level,
                       u'User \'{0}\' session ID {1} hasn\'t changed since last CoA. Avoid CoA'.format(uid, sid))
            return None
        logger.log(log_level, u'Send CoA to \'{0}\''.format(bras.ip_address))
        p = subprocess.Popen(cmd, stdout=subprocess.PIPE, stdin=subprocess.PIPE, shell=True)
        (output, error) = p.communicate(input=message)
        increase_coa_counter()
        if p.returncode == 0:
            logger.debug(u'CoA Response:\n{0}'.format(output))
            set_coa_sid(self.id, uid, sid)
        else:
            logger.log(log_level, u'CoA request failed:\n{0}'.format(output))
        return p.returncode


class CoaQueue(models.Model):
    coa = models.ForeignKey('CoaCommand')
    uid = models.CharField(max_length=255)

    class Meta:
        ordering = ('id',)

    def run(self):
        self.coa.run(self.uid)
        self.delete()

    def save(self, *args, **kwargs):
        if self.id:
            new_record = True
        else:
            new_record = False
        result = super(CoaQueue, self).save(*args, **kwargs)
        if new_record:
            log(self).info(u'Pending CoA #{0} ({1}->{2} created.'.format(self.id, self.coa.name, self.uid))
        return result
