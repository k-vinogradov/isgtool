# -*- coding: utf-8 -*-

from django.contrib import admin
from equipment.models import Bras, CoaCommand, BrasSession


@admin.register(Bras)
class BrasAdmin(admin.ModelAdmin):
    pass


@admin.register(BrasSession)
class BrasSessionAdmin(admin.ModelAdmin):
    list_display = ('bras', 'user_id', 'ip_address', 'session_id', 'session_id_hex')
    list_display_links = None
    list_filter = ('bras',)
    search_fields = ('user_id', 'ip_address', 'session_id')


@admin.register(CoaCommand)
class CoaCommandAdmin(admin.ModelAdmin):
    pass
