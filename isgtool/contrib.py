# -*- coding: utf-8 -*-

from logging import getLogger


def log(obj):
    """

    :rtype: logging.Logger
    """
    name = '{0}.{1}'.format(obj.__module__.split('.')[-1], obj.__class__.__name__)
    return getLogger(name)
