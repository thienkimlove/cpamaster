from django.contrib.auth.models import User
from django.db import models

# Create your models here.
from django_countries.fields import CountryField


DEVICES = (
    (1, "All"),
    (2, "Mobile"),
    (3, "Desktop"),
    (4, "Only Android Mobiles (Phone && Tablet)"),
    (5, "Only iOS Mobiles (Phone && Tablet)")
)


class TimeStampedModel(models.Model):
    """
    An abstract base class model that provides self-updating
    ``created`` and ``modified`` fields.
    """
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        abstract = True
        ordering = ["-updated_at"]

    def __str__(self):
        if hasattr(self, 'name'):
            return "{0}".format(self.name)


class Network(TimeStampedModel):
    name = models.CharField(max_length=255)
    cron_url = models.CharField(max_length=255, blank=True, null=True)
    rate_offer = models.SmallIntegerField(default=1)
    virtual_click = models.SmallIntegerField(default=0)
    virtual_lead = models.SmallIntegerField(default=0)
    user = models.ManyToManyField(User)
    active = models.BooleanField(default=True)
    last_cron_at = models.DateTimeField(null=True, blank=True)


class Offer(TimeStampedModel):
    name = models.CharField(max_length=255)
    redirect_link = models.CharField(max_length=255)
    click_rate = models.FloatField(default=0.0)
    geo_locations = CountryField(multiple=True)
    allow_devices = models.SmallIntegerField(default=1, choices=DEVICES)
    network = models.ForeignKey(Network, on_delete=models.CASCADE)
    net_offer_id = models.BigIntegerField(default=0)

    allow_multi_lead = models.BooleanField(default=False)
    check_click_in_network = models.BooleanField(default=False)
    number_when_click = models.SmallIntegerField(default=0)
    number_when_lead = models.SmallIntegerField(default=0)
    reject = models.BooleanField(default=False)
    auto = models.BooleanField(default=False)
    active = models.BooleanField(default=True)

    class Meta:
        ordering = ('-updated_at',)


class Click(TimeStampedModel):
    click_ip = models.CharField(max_length=100)
    offer = models.ForeignKey(Offer, on_delete=models.CASCADE)
    who_lead = models.ForeignKey(User, on_delete=models.CASCADE, null=True)

    def __str__(self):
        return "{0}-{1}".format(self.click_ip, self.offer.name)


class Lead(TimeStampedModel):
    click = models.ForeignKey(Click, on_delete=models.CASCADE)
    amount = models.FloatField(null=True, blank=True)
    status = models.BooleanField(default=True)
    request_log = models.TextField(null=True, blank=True)
    request_ip = models.CharField(max_length=200, null=True, blank=True)

    def __str__(self):
        return "{0}-{1}".format(self.click.click_ip, self.click.offer.name)


class Virtual(TimeStampedModel):
    link = models.CharField(max_length=255)
    process = models.CharField(max_length=255, null=True, blank=True)
    allow = models.SmallIntegerField(default=1)
    country = models.CharField(max_length=20)
    sent = models.NullBooleanField(null=True)
    log = models.TextField(null=True, blank=True)
    agent = models.TextField(null=True, blank=True)


class Statistic(TimeStampedModel):
    lead_id = models.IntegerField(null=True, blank=True)
    lead_json = models.TextField(null=True, blank=True)
    lead_time = models.DateTimeField(null=True, blank=True)

    click_id = models.IntegerField(null=True, blank=True)
    click_user_id = models.IntegerField(null=True, blank=True)
    click_user_name = models.CharField(max_length=255, null=True, blank=True)
    click_ip = models.CharField(max_length=20, null=True, blank=True)
    click_time = models.DateTimeField(null=True, blank=True)

    offer_id = models.IntegerField(null=True, blank=True)
    offer_name = models.CharField(max_length=255, null=True, blank=True)
    offer_net_id = models.BigIntegerField(null=True, blank=True)
    offer_click_rate = models.FloatField(null=True, blank=True)
    offer_network_id = models.IntegerField(null=True, blank=True)
    offer_network_name = models.CharField(max_length=255, null=True, blank=True)
    offer_device = models.SmallIntegerField(null=True, blank=True)
    offer_geos = models.CharField(max_length=255, null=True, blank=True)
    offer_redirect_link = models.CharField(max_length=255, null=True, blank=True)
    is_sound_play = models.BooleanField(default=False)

    class Meta:
        unique_together = ('lead_id', 'click_id')

