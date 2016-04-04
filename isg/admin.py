from django.contrib import admin
from isg.models import Bras, CoaCommand, CoaQueue


@admin.register(Bras)
class BrasAdmin(admin.ModelAdmin):
    pass


@admin.register(CoaCommand)
class CoaCommandAdmin(admin.ModelAdmin):
    pass

@admin.register(CoaQueue)
class CoaQueueAdmin(admin.ModelAdmin):
    pass