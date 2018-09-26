from django.contrib.auth import login, REDIRECT_FIELD_NAME
from django.db.models import Sum, Count
from django.shortcuts import redirect
from django.urls import reverse, reverse_lazy
from django.utils.decorators import method_decorator
from django.utils.http import is_safe_url
from django.utils.safestring import mark_safe
from django.views.decorators.cache import never_cache
from django.views.decorators.csrf import csrf_protect
from django.views.decorators.debug import sensitive_post_parameters
from django.views.generic import View, FormView, TemplateView
from django_datatables_view.base_datatable_view import BaseDatatableView

from core.forms import *
from core.helpers import *
from core.models import *
from cpamaster.settings import API_KEY


class ListJson(BaseDatatableView):
    # set max limit of records returned, this is used to protect our site if someone tries to attack our site
    # and make it return huge amount of data
    max_display_length = 500


class OfferAPIJson(ListJson):
    model = Offer

    # define the columns that will be returned
    order_columns = [
        'updated_at',
    ]

    def filter_queryset(self, qs):
        return filter_offer(qs, self.request)

    def prepare_results(self, qs):
        # prepare list with output column data
        # queryset is already paginated here
        json_data = []
        if self.request.GET.get('key') and self.request.GET.get('key') == API_KEY:
            for item in qs:
                json_data.append({
                    "id": item.id,
                    "name": item.name,
                    "tracking_net": item.redirect_link,
                    "tracking_site": mark_safe(
                        self.request.build_absolute_uri(reverse('core:offer_camp') + '?user_id=1&offer_id=' + str(item.id))),
                    "countries": ', '.join([x.code for x in item.geo_locations]),
                    "os": get_display_devices(item.allow_devices),
                    "payout": item.click_rate
                })
        return json_data


class OfferListJson(ListJson):
    model = Offer

    # define the columns that will be returned
    order_columns = [
        'name',
        'updated_at',
        'net_offer_id',
        'network'
    ]

    def filter_queryset(self, qs):
        if not self.request.user.is_superuser:
            qs = qs.filter(network__user=self.request.user)
        return filter_offer(qs, self.request)

    def prepare_results(self, qs):
        # prepare list with output column data
        # queryset is already paginated here
        json_data = []
        for item in qs:
            action = '<a class="table-action-btn" title="Clear Click IP" href="' + reverse(
                'core:offer_clear', kwargs={'item_id': item.id}) + '"><i class="fa fa-commenting text-warning"></i></a> '

            if self.request.user.is_staff is True or self.request.user.is_superuser is True:
                action += '<a class="table-action-btn" title="Chỉnh sửa offer" href="' + reverse('core:offer_edit', kwargs={
                    'item_id': item.id}) + '"><i class="fa fa-pencil text-success"></i></a>'

            if item.active is True:
                action += '<a class="table-action-btn" title="InActive this Offer" href="' + reverse(
                    'core:offer_inactive', kwargs={'item_id': item.id}) + '"><i class="fa fa-save text-warning"></i></a> '

            if item.reject is True:
                action += '<a class="table-action-btn" id="btn-accept-' + str(item.id) + '" data-url="' + reverse(
                    'core:offer_accept', kwargs={
                        'item_id': item.id}) + '"  title="Accept Offer" href="javascript:;"><i class="fa fa-unlock text-danger"></i></a>'
            else:
                action += '<a class="table-action-btn" id="btn-reject-' + str(item.id) + '" data-url="' + reverse(
                    'core:offer_reject', kwargs={
                        'item_id': item.id}) + '"  title="Reject Offer" href="javascript:;"><i class="fa fa-lock text-danger"></i></a>'

            json_data.append({
                "name": (item.name[:50] + '..') if len(item.name) > 50 else item.name,
                "click_rate": item.click_rate,
                "geo_locations": ', '.join([x.code for x in item.geo_locations]),
                "allow_devices": get_display_devices(item.allow_devices),
                "redirect_link": mark_safe(
                    self.request.build_absolute_uri(reverse('core:offer_camp') + '?user_id=' + str(self.request.user.id) + '&offer_id=' + str(item.id))),
                "check_link": mark_safe(
                    self.request.build_absolute_uri(
                        reverse('core:offer_check') + '?user_id=' + str(self.request.user.id) + '&offer_id=' + str(
                            item.id))),

                "active": '<i class="ion ion-checkmark-circled text-success"></i>' if item.active is True else '<i class="ion ion-close-circled text-danger"></i>',
                "updated_at": item.updated_at.strftime('%Y-%m-%d %H:%M:%S'),
                "net_offer_id": item.net_offer_id,
                "network_name": item.network.name,
                "action": mark_safe(action)
            })
        return json_data


class NetworkAPIJson(ListJson):
    model = Network

    # define the columns that will be returned
    order_columns = [
        'name',
        'updated_at',
    ]

    def filter_queryset(self, qs):
        return filter_network(qs, self.request)

    def prepare_results(self, qs):
        # prepare list with output column data
        # queryset is already paginated here
        json_data = []

        if self.request.GET.get('key') and self.request.GET.get('key') == API_KEY:
            for item in qs:

                json_data.append({
                    "id": item.id,
                    "name": item.name,
                    "cron_url": item.cron_url
                })
        return json_data


class NetworkListJson(ListJson):
    model = Network

    # define the columns that will be returned
    order_columns = [
        'name',
        'updated_at',
    ]

    def filter_queryset(self, qs):
        if not self.request.user.is_superuser:
            qs = qs.filter(user=self.request.user)
        return filter_network(qs, self.request)

    def prepare_results(self, qs):
        # prepare list with output column data
        # queryset is already paginated here
        json_data = []
        for item in qs:
            action = '<a class="table-action-btn" ' \
                     'title="Chỉnh sửa Network" ' \
                     'href="' + reverse('core:network_edit', kwargs={'item_id': item.id}) + '">' \
                      '<i class="fa fa-pencil text-success"></i>' \
                     '</a> ' \
                     '<a class="table-action-btn" ' \
                     'title="Run Cron" target="_blank" ' \
                     'href="' + reverse('core:network_cron', kwargs={'item_id': item.id}) + '">' \
                     '<i class="fa fa-tasks text-success"></i>' \
                     '</a>'

            json_data.append({
                "name": item.name,
                "cron_url": item.cron_url,
                "count_offer": Offer.objects.filter(network=item).count(),
                "active": '<i class="ion ion-checkmark-circled text-success">'
                          '</i>' if item.active is True else '<i class="ion ion-close-circled text-danger"></i>',
                "updated_at": item.updated_at.strftime('%Y-%m-%d %H:%M:%S'),
                "last_cron_at": item.last_cron_at.strftime('%Y-%m-%d %H:%M:%S') + "("+ago(item.last_cron_at)+")" if item.last_cron_at else '',
                "action": mark_safe(action)
            })
        return json_data


class LeadListJson(ListJson):
    model = Statistic

    # define the columns that will be returned
    order_columns = [
        'updated_at',
        'click_id',
    ]

    def filter_queryset(self, qs):
        return filter_statistic(qs, self.request)

    def prepare_results(self, qs):
        # prepare list with output column data
        # queryset is already paginated here
        json_data = []

        total_qs = Statistic.objects
        total_qs = filter_statistic(total_qs, self.request)
        total = total_qs.aggregate(Sum('offer_click_rate'))
        total_leads = total_qs.count()

        for item in qs:
            json_data.append({
                "click_ip": item.click_ip,
                "sub_id": item.click_id,
                "offer_name": item.offer_name,
                "lead_user": item.click_user_name,
                "net_offer_id": item.offer_net_id,
                "amount": item.offer_click_rate,
                "lead_time": item.lead_time.strftime('%Y-%m-%d %H:%M:%S'),
                "total_money": round(total['offer_click_rate__sum'], 2),
                "total_leads": total_leads,
            })
        return json_data


class GuestOnlyView(View):
    def dispatch(self, request, *args, **kwargs):
        # Redirect to the index page if the user already authenticated
        if request.user.is_authenticated:
            return redirect(settings.LOGIN_REDIRECT_URL)

        return super().dispatch(request, *args, **kwargs)


class LoginOnlyView(View):
    def dispatch(self, request, *args, **kwargs):
        # Redirect to the index page if the user already authenticated
        if not request.user.is_authenticated:
            return redirect(reverse_lazy('core:login'))

        return super().dispatch(request, *args, **kwargs)


class LogInView(GuestOnlyView, FormView):
    template_name = 'core/login.html'

    @staticmethod
    def get_form_class(**kwargs):
        return SignInViaUsernameForm

    @method_decorator(sensitive_post_parameters('password'))
    @method_decorator(csrf_protect)
    @method_decorator(never_cache)
    def dispatch(self, request, *args, **kwargs):
        # Sets a test cookie to make sure the user has cookies enabled
        request.session.set_test_cookie()

        return super().dispatch(request, *args, **kwargs)

    def form_valid(self, form):
        request = self.request

        # If the test cookie worked, go ahead and delete it since its no longer needed
        if request.session.test_cookie_worked():
            request.session.delete_test_cookie()

        # The default Django's "remember me" lifetime is 2 weeks and can be changed by modifying
        # the SESSION_COOKIE_AGE settings' option.
        if settings.USE_REMEMBER_ME:
            if not form.cleaned_data['remember_me']:
                request.session.set_expiry(0)

        login(request, form.user_cache)

        redirect_to = request.POST.get(REDIRECT_FIELD_NAME, request.GET.get(REDIRECT_FIELD_NAME))
        url_is_safe = is_safe_url(redirect_to, allowed_hosts=request.get_host(), require_https=request.is_secure())

        if url_is_safe:
            return redirect(redirect_to)

        return redirect(settings.LOGIN_REDIRECT_URL)


class IndexPageView(LoginOnlyView, TemplateView):
    template_name = 'core/index.html'
