from django import template
from django.conf import settings
from django.contrib.auth.models import User

from core.models import Network

register = template.Library()


# settings value
@register.simple_tag
def settings_value(name):
    return getattr(settings, name, "")


@register.simple_tag
def get_devices():
    return {1: "All", 2: "Mobile", 3: "Desktop", 4: "Only Android Mobiles (Phone && Tablet)",
            5: "Only iOS Mobiles (Phone && Tablet)"}.items()


@register.simple_tag
def get_networks(user):
    if user.is_superuser is True:
        return Network.objects.filter(active=True)
    return Network.objects.filter(active=True).filter(user=user)


@register.simple_tag
def get_users(user):
    if user.is_superuser is True:
        return User.objects.all()
    networks = Network.objects.filter(active=True).filter(user=user)
    ids = []
    for network in networks:
        for net_user in network.user.all():
            ids.append(net_user.id)

    return User.objects.filter(id__in=ids)