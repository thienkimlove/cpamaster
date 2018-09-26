from django.contrib import admin

# Register your models here.
from core.models import *


class NetworkAdmin(admin.ModelAdmin):
    menu_title = "Networks"
    menu_group = "Networks"
    list_display = ('name', 'cron_url', 'rate_offer', 'virtual_click', 'virtual_lead', 'active', 'get_users')
    list_filter = ('user',)

    def get_users(self, obj):
        return "\n".join([p.username for p in obj.user.all()])

    get_users.short_description = 'Users'


class OfferAdmin(admin.ModelAdmin):
    menu_title = "Offers"
    menu_group = "Offers"


class ClickAdmin(admin.ModelAdmin):
    menu_title = "Clicks"
    menu_group = "Clicks"


class LeadAdmin(admin.ModelAdmin):
    menu_title = "Leads"
    menu_group = "Leads"


admin.site.register(Network, NetworkAdmin)
admin.site.register(Click, ClickAdmin)
admin.site.register(Offer, OfferAdmin)
admin.site.register(Lead, LeadAdmin)
