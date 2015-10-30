# -*- coding: utf-8 -*-

from logging import getLogger


def log(obj):
    #return getLogger('{0}.{1}'.format(obj.__module__, obj.__class__.__name__))
    name = '{0}.{1}'.format(obj.__module__.split('.')[-1], obj.__class__.__name__)
    return getLogger(name)
