import logging
import subprocess

import xlwt
import calendar
import re
from django.contrib.auth import logout
from django.db.models import Sum
from django.http import JsonResponse, HttpResponse
from django.shortcuts import redirect, render
from django.template.loader import render_to_string
from django.urls import reverse_lazy
from django.utils import timezone
from django_countries import countries
from django.utils.safestring import mark_safe
from django.utils.timezone import now
from core.forms import *
from core.helpers import *
from datetime import datetime, timedelta, time
_logger = logging.getLogger('default')


def get_month_day_range(date):
    """
    For a date 'date' returns the start and end date for the month of 'date'.

    Month with 31 days:
    >>> date = datetime.date(2011, 7, 27)
    >>> get_month_day_range(date)
    (datetime.date(2011, 7, 1), datetime.date(2011, 7, 31))

    Month with 28 days:
    >>> date = datetime.date(2011, 2, 15)
    >>> get_month_day_range(date)
    (datetime.date(2011, 2, 1), datetime.date(2011, 2, 28))
    """
    first_day = date.replace(day=1)
    last_day = date.replace(day=calendar.monthrange(date.year, date.month)[1])
    return first_day, last_day


def log_out(request):
    logout(request)
    return redirect(reverse_lazy('core:login'))


def get_money(money):
    return round(money.get('offer_click_rate__sum'), 2) if money.get('offer_click_rate__sum') is not None else 0


def index(request):
    if not request.user.is_authenticated:
        return redirect(reverse_lazy('core:login'))

    today_date = timezone.now().date()
    yesterday_date = today_date - timedelta(days=1)
    some_day_last_week = today_date - timedelta(days=7)
    monday_of_last_week = some_day_last_week - timedelta(days=(some_day_last_week.isocalendar()[2] - 1))
    start_of_this_week = monday_of_last_week + timedelta(days=7)
    end_of_this_week = start_of_this_week + timedelta(days=7)
    start_of_month, end_of_month = get_month_day_range(today_date)

    leads = Statistic.objects

    if not request.user.is_superuser:
        networks = Network.objects.filter(user=request.user)
        leads = leads.filter(offer_network_id__in=[x.id for x in networks])

    total_money = leads.aggregate(Sum('offer_click_rate'))
    today_money = leads.filter(created_at__date=today_date).aggregate(Sum('offer_click_rate'))

    month_money = leads.filter(Q(created_at__gte=start_of_month) & Q(created_at__lte=end_of_month)).aggregate(Sum('offer_click_rate'))

    today_leads = leads.filter(created_at__date=today_date)
    yesterday_leads = leads.filter(Q(created_at__gte=yesterday_date) & Q(created_at__lte=today_date))
    week_leads = leads.filter(Q(created_at__gte=start_of_this_week) & Q(created_at__lte=end_of_this_week))
    month_leads = leads.filter(Q(created_at__gte=start_of_month) & Q(created_at__lte=start_of_month))

    today_statistic_by_users = today_leads.values('click_user_name') \
        .annotate(sum_money=Sum('offer_click_rate')) \
        .order_by('-sum_money')

    today_statistic_by_networks = today_leads.values('offer_network_name') \
        .annotate(sum_money=Sum('offer_click_rate')) \
        .order_by('-sum_money')

    today_offers = {}
    week_offers = {}
    yesterday_offers = {}

    for lead in yesterday_leads:
        if lead.offer_id not in yesterday_offers:
            yesterday_offers[lead.offer_id] = {
                "name": "",
                "total_leads": 0,
                "total_money": 0,
                "price": 0,
            }
        yesterday_offers[lead.offer_id]["name"] = lead.offer_name
        yesterday_offers[lead.offer_id]["price"] = lead.offer_click_rate
        yesterday_offers[lead.offer_id]["total_leads"] += 1
        yesterday_offers[lead.offer_id]["total_money"] += lead.offer_click_rate

    for k, v in yesterday_offers.items():
        yesterday_offers[k]["total_clicks"] = Click.objects.filter(offer__id=k).filter(Q(created_at__gte=yesterday_date) & Q(created_at__lte=today_date)).count()
        if yesterday_offers[k]["total_clicks"] > 0:
            yesterday_offers[k]["site_cr"] = str(round((yesterday_offers[k]["total_leads"] / yesterday_offers[k]["total_clicks"]) * 100, 2)) + '%'
        else:
            yesterday_offers[k]["site_cr"] = "Not Available"

        yesterday_offers[k]["total_money"] = round(yesterday_offers[k]["total_money"], 2)

    for lead in week_leads:
        if lead.offer_id not in week_offers:
            week_offers[lead.offer_id] = {
                "name": "",
                "total_leads": 0,
                "total_money": 0,
                "price": 0,
            }
        week_offers[lead.offer_id]["name"] = lead.offer_name
        week_offers[lead.offer_id]["price"] = lead.offer_click_rate
        week_offers[lead.offer_id]["total_leads"] += 1
        week_offers[lead.offer_id]["total_money"] += lead.offer_click_rate

    for k, v in week_offers.items():
        week_offers[k]["total_clicks"] = Click.objects.filter(offer__id=k).filter(
            Q(created_at__gte=start_of_this_week) & Q(created_at__lte=end_of_this_week)).count()
        if week_offers[k]["total_clicks"] > 0:
            week_offers[k]["site_cr"] = str(
                round((week_offers[k]["total_leads"] / week_offers[k]["total_clicks"]) * 100, 2)) + '%'
        else:
            week_offers[k]["site_cr"] = "Not Available"

        week_offers[k]["total_money"] = round(week_offers[k]["total_money"], 2)

    for lead in today_leads:
        if lead.offer_id not in today_offers:
            today_offers[lead.offer_id] = {
                "name": "",
                "total_leads": 0,
                "total_money": 0,
                "price": 0,
            }
        today_offers[lead.offer_id]["name"] = lead.offer_name
        today_offers[lead.offer_id]["price"] = lead.offer_click_rate

        today_offers[lead.offer_id]["total_leads"] += 1
        today_offers[lead.offer_id]["total_money"] += lead.offer_click_rate

    for k, v in today_offers.items():
        today_offers[k]["total_clicks"] = Click.objects.filter(offer__id=k).filter(created_at__date=today_date).count()
        if today_offers[k]["total_clicks"] > 0:
            today_offers[k]["site_cr"] = str(
                round((today_offers[k]["total_leads"] / today_offers[k]["total_clicks"]) * 100, 2)) + '%'
        else:
            today_offers[k]["site_cr"] = "Not Available"

        today_offers[k]["total_money"] = round(today_offers[k]["total_money"], 2)

    return render(request, 'core/index.html', {
        'total_money': get_money(total_money),
        'today_money': get_money(today_money),
        'month_money': get_money(month_money),
        'today_leads': today_leads,
        'week_leads': week_leads,
        'month_leads': month_leads,
        'today_statistic_by_users': today_statistic_by_users,
        'today_offers': today_offers,
        'week_offers': week_offers,
        'yesterday_offers': yesterday_offers,
        'today_statistic_by_networks': today_statistic_by_networks,
    })


def list_offer(request):
    if not request.user.is_authenticated:
        return redirect(reverse_lazy('core:login'))
    return render(request, 'core/offers/index.html')


def list_network(request):
    if not request.user.is_authenticated:
        return redirect(reverse_lazy('core:login'))
    return render(request, 'core/networks/index.html')


def list_lead(request):
    if not request.user.is_authenticated:
        return redirect(reverse_lazy('core:login'))
    return render(request, 'core/leads/index.html')


def recent_lead(request):

    if not request.user.is_superuser:
        networks = Network.objects.filter(user=request.user)
        recent_leads = Statistic.objects.filter(offer_network_id__in=[x.id for x in networks]).order_by('-updated_at')[:10]

    else:
        recent_leads = Statistic.objects.order_by('-updated_at')[:10]

    html = render_to_string('core/recent.html', {'recent_leads': recent_leads})

    return JsonResponse({'html': html})


def notify_lead(request):

    not_notify = 0

    if request.user:
        not_notify = Statistic.objects.filter(click_user_id=request.user.id).filter(is_sound_play=False).count()
        if not_notify > 0:
            Statistic.objects.filter(click_user_id=request.user.id).filter(is_sound_play=False).update(is_sound_play=True)

    return JsonResponse({'count': not_notify})

def create_offer(request):
    if not request.user.is_authenticated:
        return redirect(reverse_lazy('core:login'))
    if request.method == 'POST':
        form = OfferForm(request.POST)
        if form.is_valid():
            form.save()
            return redirect(reverse_lazy('core:offer_list'))
    else:
        form = OfferForm()
    return render(request, 'core/offers/edit.html', {'form': form})


def edit_offer(request, item_id):
    if not request.user.is_authenticated:
        return redirect(reverse_lazy('core:login'))
    offer = Offer.objects.get(pk=item_id)

    if request.method == 'POST':
        form = OfferForm(request.POST, instance=offer)
        if form.is_valid():
            form.save()
            return redirect(reverse_lazy('core:offer_list'))
    else:
        form = OfferForm(instance=offer)
    return render(request, 'core/offers/edit.html', {'form': form})


def edit_network(request, item_id):
    if not request.user.is_authenticated:
        return redirect(reverse_lazy('core:login'))
    content = Network.objects.get(pk=item_id)

    if request.method == 'POST':
        form = NetworkForm(request.POST, instance=content)
        if form.is_valid():
            form.save()
            return redirect(reverse_lazy('core:network_list'))
    else:
        form = NetworkForm(instance=content)
    return render(request, 'core/networks/edit.html', {'form': form})


def clear_offer(request, item_id):
    if not request.user.is_authenticated:
        return redirect(reverse_lazy('core:login'))
    offer = Offer.objects.get(pk=item_id)
    Click.objects.filter(offer=offer).update(click_ip="10.0.2.2")
    return redirect(reverse_lazy('core:offer_list'))


def inactive_offer(request, item_id):
    if not request.user.is_authenticated:
        return redirect(reverse_lazy('core:login'))
    offer = Offer.objects.get(pk=item_id)
    offer.active = False
    offer.save()

    return redirect(reverse_lazy('core:offer_list'))


def ajax_cron(request, item_id, routing):
    subprocess.call(
        ["/root/Env/cpamaster/bin/python", "/var/www/html/cpamaster/manage.py", "cron",
         "--network_id=%s" % item_id, "--routing=%s" % routing])

    return HttpResponse('{"msg": "OK"}', content_type='application/json')


def cron_network(request, item_id):
    if not request.user.is_authenticated:
        return redirect(reverse_lazy('core:login'))
    enable_debug = request.GET.get('debug', None)
    sever_ip = settings.SERVER_IP
    routing = 'con_for_network_%s_%s' % (item_id, now().strftime('%Y%m%d%H%M%S'))
    return render(request, 'core/rabbit.html', {
        'routing': routing,
        'network_id': item_id,
        'debug': enable_debug,
        'sever_ip': sever_ip,
    })


def accept_offer(request, item_id):
    if not request.user.is_authenticated:
        return redirect(reverse_lazy('core:login'))
    offer = Offer.objects.get(pk=item_id)
    offer.reject = False
    offer.save()
    return JsonResponse({'status': True})


def reject_offer(request, item_id):
    if not request.user.is_authenticated:
        return redirect(reverse_lazy('core:login'))
    offer = Offer.objects.get(pk=item_id)
    offer.reject = True
    offer.save()
    return JsonResponse({'status': True})


def delete_offer(request, item_id):
    if not request.user.is_authenticated:
        return redirect(reverse_lazy('core:login'))
    offer = Offer.objects.get(pk=item_id)
    offer.delete()
    return JsonResponse({'status': True})


def delete_network(request, item_id):
    if not request.user.is_authenticated:
        return redirect(reverse_lazy('core:login'))
    content = Network.objects.get(pk=item_id)
    content.delete()
    return JsonResponse({'status': True})


def check(request):
    offer_id = request.GET.get('offer_id', None)
    user_id = request.GET.get('user_id', None)
    try:
        if offer_id is None:
            raise ValueError('No offer Id')
        if user_id is None:
            raise ValueError('No User Id')

        offer = Offer.objects.get(pk=offer_id)

        if not offer or offer.active is False or not offer.redirect_link:
            raise ValueError('Offer is inactive or not found redirect link')

        user = User.objects.get(pk=user_id)

        if not user or user.is_active is False:
            raise ValueError('User is inactive or not found user')

        if offer.network.active is False:
            raise ValueError('Network is not Active')

        if not check_device_offer(offer, request):
            raise ValueError('Device not allow')

        status, location, ip = get_ip_and_location(offer, request)

        if status is False:
            raise ValueError('Location not allow {0} {1}'.format(location, ip))

        redirect_link = offer.redirect_link.replace('#subId', '')
        redirect_link = redirect_link.replace('#subid', '')

        return redirect(redirect_link)
    except Exception as e:
        return JsonResponse({'error': str(e)})


def camp(request):
    offer_id = request.GET.get('offer_id', None)
    user_id = request.GET.get('user_id', None)
    try:
        if offer_id is None:
            raise ValueError('No offer Id')
        if user_id is None:
            raise ValueError('No User Id')

        offer = Offer.objects.get(pk=offer_id)

        if not offer or offer.active is False or not offer.redirect_link:
            raise ValueError('Offer is inactive or not found redirect link')

        user = User.objects.get(pk=user_id)

        if not user or user.is_active is False:
            raise ValueError('User is inactive or not found user')

        if offer.network.active is False:
            raise ValueError('Network is not Active')

        if not check_device_offer(offer, request):
            raise ValueError('Device not allow')

        status, location, ip = get_ip_and_location(offer, request)

        if status is False:
            raise ValueError('Location not allow {0} {1}'.format(location, ip))

        if offer.check_click_in_network is True:
            count_click = Lead.objects.filter(click__offer=offer).filter(request_ip=ip).count()
        else:
            count_click = Click.objects.filter(offer=offer).filter(click_ip=ip).count()

        if count_click > 0 and not offer.allow_multi_lead:
            raise ValueError('Multi click is not allow for offer')

        click = Click.objects.create(offer=offer, click_ip=ip, who_lead=user)

        redirect_link = offer.redirect_link.replace('#subId', str(click.id))
        redirect_link = redirect_link.replace('#subid', str(click.id))

        if offer.number_when_click > 0:
            for i in range(0, offer.number_when_click):
                replace = "{0}-{1}".format(now(), i)
                true_link = offer.redirect_link.replace('#subId', replace)
                true_link = true_link.replace('#subid', replace)
                Virtual.objects.create(link=true_link, allow=offer.allow_devices, country=location)
        return redirect(redirect_link)
    except Exception as e:
        return JsonResponse({'error': str(e)})


def postback(request):
    try:
        sub_id = request.GET.get('sub_id', None)

        if not sub_id:
            sub_id = request.GET.get('subid', None)

        if not sub_id:
            raise ValueError('Sub Id required!')

        sub_id = int(sub_id)

        check_existed_lead = Lead.objects.filter(click=sub_id).count()

        if check_existed_lead:
            raise ValueError('Lead for clickId={0} existed!'.format(sub_id))

        click = Click.objects.get(pk=sub_id)

        if not click:
            raise ValueError('Can not find click for sub_id={0}'.format(sub_id))

        active = True
        status = request.GET.get('status', None)
        amount = request.GET.get('amount', None)

        if status is None:
            status = request.POST.get('status', None)

        if amount is None:
            amount = request.POST.get('amount', None)

        if status and int(status) == -1:
            active = False
        # request_ip = get_client_ip(request)
        log = json.dumps(request.GET)
        lead = Lead.objects.create(click=click, amount=amount, status=active, request_ip=click.click_ip, request_log=log)

        if click.offer.number_when_lead > 0:
            for i in range(0, click.offer.number_when_lead):
                replace = "{0}-{1}".format(now(), i)
                true_link = click.offer.redirect_link.replace('#subId', replace)
                true_link = true_link.replace('#subid', replace)
                country = click.offer.geo_locations[0].code if click.offer.geo_locations else 'US'
                Virtual.objects.create(link=true_link, allow=click.offer.allow_devices, country=country)

        # Store in statistic table.
        create_statistic_on_lead(lead)

        return JsonResponse({'success': lead.id})
    except Exception as e:
        return JsonResponse({'error': str(e)})


def export_offer(request):
    qs = Offer.objects
    if not request.user.is_superuser:
        qs = qs.filter(network__user=request.user)
    qs = filter_offer(qs, request)

    response = HttpResponse(content_type='application/ms-excel')
    response['Content-Disposition'] = 'attachment; filename="offers'+now().strftime('%Y-%m-%d-%H-%M')+'.xls"'

    wb = xlwt.Workbook(encoding='utf-8')
    ws = wb.add_sheet('Offers')

    # Sheet header, first row
    row_num = 0

    font_style = xlwt.XFStyle()
    font_style.font.bold = True

    headers = ['STT', 'Name', 'Price Per Click', 'Geo Locations', 'Allow Devices', 'Redirect Link', 'Net Offer ID', 'Network']

    for col_num in range(len(headers)):
        ws.write(row_num, col_num, headers[col_num], font_style)

    # Sheet body, remaining rows
    font_style = xlwt.XFStyle()

    columns = ['name', 'click_rate', 'geo_locations', 'allow_devices', 'redirect_link', 'net_offer_id', 'network']

    for row in qs.all():
        row_num += 1
        col_num = 0
        for col_name in columns:
            col_num += 1
            value = getattr(row, col_name)
            if col_name == 'geo_locations':
                value = ', '.join([str(x) for x in value])

            if col_name == 'network':
                value = value.name

            if col_name == 'allow_devices':
                value = get_display_devices(value)

            ws.write(row_num, col_num, value, font_style)

    wb.save(response)
    return response


def export_lead(request):
    qs = Statistic.objects

    qs = filter_statistic(qs, request)

    response = HttpResponse(content_type='application/ms-excel')
    response['Content-Disposition'] = 'attachment; filename="leads'+now().strftime('%Y-%m-%d-%H-%M')+'.xls"'

    wb = xlwt.Workbook(encoding='utf-8')
    ws = wb.add_sheet('Leads')

    # Sheet header, first row
    row_num = 0

    font_style = xlwt.XFStyle()
    font_style.font.bold = True

    headers = ['STT', 'ClickIp', 'LeadUser', 'SubID', 'OfferName', 'NetOfferId', 'LeadAmount', 'LeadTime']

    for col_num in range(len(headers)):
        ws.write(row_num, col_num, headers[col_num], font_style)

    # Sheet body, remaining rows
    font_style = xlwt.XFStyle()

    columns = ['click_ip', 'click_user_name', 'click_id', 'offer_name', 'offer_net_id', 'offer_click_rate', 'lead_time']

    for row in qs.all():
        row_num += 1
        col_num = 0
        for col_name in columns:
            col_num += 1
            value = getattr(row, col_name)

            if col_name == "lead_time":
                value = value.strftime('%Y-%m-%d %H:%M')

            ws.write(row_num, col_num, value, font_style)

    wb.save(response)
    return response

def api_offer(request):
    ids = request.GET.get('ids', None)
    user_id = request.GET.get('user_id', None)
    response = []

    offers = []

    if ids:
        offer_ids = ids.split(',')
        offers = Offer.objects.filter(id__in=offer_ids).filter(network__user__in=[user_id])
    else:
        country = request.GET.get('country', None)
        country = re.sub(r"\s+", "", country)
        country = country.lower()
        country_code = None
        for code, name in list(countries):
            temp_name = re.sub(r"\s+", "", name)
            temp_name = temp_name.lower()
            if country in temp_name or temp_name in country:
                country_code = code

        if country_code:
            offers = Offer.objects.filter(geo_locations__in=[country_code]).filter(allow_devices=5).filter(network__user__in=[user_id])[:5]


    for offer in offers:
        response.append({
            "id": offer.id,
            "name": offer.name,
            "geo_locations": offer.geo_locations[0].name.upper()
        })

    return JsonResponse(response, safe=False)

def api_user(request):
    response = []
    users = User.objects.filter(is_active=True)
    for user in users:
        response.append({
            "id": user.id,
            "username": user.username
        })

    return JsonResponse(response, safe=False)


