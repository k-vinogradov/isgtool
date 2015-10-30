# -*- coding: utf-8 -*-

from django.db import models
from equipment.isg_cache import IsgCache
from isgtool.contrib import log

import telnetlib
import logging
import subprocess


class BrasSession(models.Model):
    user_id = models.CharField(max_length=255)
    session_id = models.CharField(max_length=255)
    session_id_hex = models.CharField(max_length=255)
    ip_address = models.GenericIPAddressField()
    update_datetime = models.DateTimeField(auto_now_add=True)
    bras = models.ForeignKey('Bras')


class Bras(models.Model):
    name = models.CharField(max_length=255, verbose_name=u'Name')
    ip_address = models.CharField(max_length=15, verbose_name=u'IP Address')
    is_active = models.BooleanField(default=True, blank=True, verbose_name=u'Is Active')
    username = models.CharField(max_length=255, verbose_name=u'Telnet Username')
    password = models.CharField(max_length=255, verbose_name=u'Telnet Password')
    timeout = models.IntegerField(verbose_name=u'Telnet Timeout', help_text=u'seconds')
    command_prompt = models.CharField(max_length=255, verbose_name=u'Command Prompt')
    coa_secret = models.CharField(max_length=255, verbose_name=u'CoA Secret')
    coa_port = models.IntegerField(verbose_name=u'CoA Port')

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

    def aaa_list_update(self, model_store=False, use_telnet=False):
        logger = log(self)
        if use_telnet:
            logger.info(u'Get sessiong list from BRAS \'{0}\' by command-line interface'.format(self.name))
            output = self._telnet_output('show aaa sessions')
        else:
            logger.info(u'Get session list from BRAS \'{0}\' by RShell'.format(self.name))
            output = self._rsh_output('show aaa sessions')
        cache_obj = IsgCache()
        sessions = []
        counter = 0
        session_id = None
        uid = None
        ip_address = None
        logger.info(u'Parse {} output'.format('telnet' if use_telnet else 'RShell'))
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
                if model_store:
                    sessions.append((uid.strip(), session_id.strip(), ip_address))
                    session_id = None
                    uid = None
                    ip_address = None
                else:
                    cache_obj.prepare_session_data(bras=self, user_id=uid,
                                                   session_id='{:X}'.format(int(session_id)), ip_address=ip_address)

        logger.info(u'Parsed {0} sessions(s).'.format(counter))
        if model_store:
            logger.info(u'Flush DB session list')
            BrasSession.objects.filter(bras=self).delete()
            index = 0
            batch_size = 999
            last_index = len(sessions) - 1
            while index <= last_index:
                if index + batch_size <= last_index:
                    finish = index + batch_size
                else:
                    finish = last_index
                logger.info(u'Create session DB-records: {0}-{1}'.format(index + 1, finish + 1))
                BrasSession.objects.bulk_create([BrasSession(
                    user_id=uid,
                    session_id=session_id,
                    session_id_hex=hex(int(session_id)),
                    ip_address=ip_address,
                    bras=self) for uid, session_id, ip_address in sessions[index:finish]])
                index = finish + 1
        else:
            logger.info(u'Caching query result')
            cache_obj.save()
        cache_obj.set_bras_last_update(self)


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

        cache_obj = IsgCache()
        session_info = cache_obj.get_session_info(uid)
        if not session_info:
            logger.log(log_level, u'No cached session info for user \'{0}\''.format(uid))
            return False
        bras = session_info['bras']
        session_id = session_info['session_id']

        message = self.message.format(user_id=uid, aaa_session_id=session_id)
        cmd = 'radclient -x -t 1 -r 1 {ip}:{port} coa {secret}'.format(ip=bras.ip_address, port=bras.coa_port,
                                                                       secret=bras.coa_secret)
        if cache_obj.check_last_coa_aaa_id(uid, self, session_id):
            logger.log(log_level, u'User \'{0}\' session ID {1} hasn\'t changed since last CoA. Avoid CoA'.format(uid, session_id))
            return True
        logger.log(log_level, u'Send CoA to \'{0}\''.format(bras.ip_address))
        p = subprocess.Popen(cmd, stdout=subprocess.PIPE, stdin=subprocess.PIPE, shell=True)
        (output, error) = p.communicate(input=message)
        if p.returncode == 0:
            logger.debug(u'CoA Response:\n{0}'.format(output))
            cache_obj.set_last_coa_aaa_id(uid, self, session_id)
            cache_obj.increase_coa_counter()
            return True
        else:
            logger.log(log_level, u'CoA request failed:\n{0}'.format(output))
            cache_obj.increase_coa_counter(success=False)
            return False


class CoaQueue(models.Model):
    coa = models.ForeignKey('CoaCommand')
    user_id = models.CharField(max_length=255)

    class Meta:
        ordering = ('id',)

    def run(self):
        self.coa.run(self.user_id)
        self.delete()

    def save(self, *args, **kwargs):
        if self.id:
            new_record = True
        else:
            new_record = False
        result = super(CoaQueue, self).save(*args, **kwargs)
        if new_record:
            log(self).info(u'Pending CoA #{0} ({1}->{2} created.'.format(self.id, self.coa.name, self.user_id))
        return result
