import datetime
import json
import random
import re
from itertools import islice
from urllib.parse import unquote, urlparse, parse_qs
from urllib.request import urlopen

import pika
from django.utils.timesince import timesince
from django.utils.timezone import now
from geolite2 import geolite2
import pycountry
import requests
import urllib3
from django.db.models import Q
from django.utils.dateparse import parse_datetime
from gevent.pool import Pool
from requests.compat import basestring
from urllib3.exceptions import InsecureRequestWarning

from core.models import *
from cpamaster import settings
from cpamaster.settings import LOG_FILE, IP_STACK_API_KEY, GEO_IP_PATH


def debug(msg):
    with open(LOG_FILE, 'r') as original: data = original.read()
    with open(LOG_FILE, 'w') as modified: modified.write(data + str(repr(msg)) + "\n")


def country_list():
    cc = {}
    t = list(pycountry.countries)

    for country in t:
        cc[country.alpha_2] = country.name
    return cc


def get_device_from_string(value):
    new_str = '   ' + value

    new_str = new_str.replace(',', '  ')
    new_str = new_str.replace('``', '  ')
    new_str = new_str.replace('-', '  ')
    new_str = new_str.replace('_', '  ')

    temp = ' '.split(new_str)
    return ','.join(temp)


def get_country_codes_from_string(value):
    new_str = value.replace(',', '  ')
    new_str = new_str.replace('``', '  ')
    new_str = new_str.replace('-', '  ')
    new_str = new_str.replace('_', '  ')
    new_str = '   ' + new_str + '   '

    regex = r"\s*\[?([A-Z]{2})\]?\s*"

    get_list = []
    result = re.findall(regex, new_str, re.IGNORECASE)
    countries = country_list()
    if result:
        for find in result:
            if (find in countries.keys() or find == 'UK') and find not in get_list:
                get_list.append(find)
            else:
                debug(find)

    if get_list:
        return ','.join(get_list)
    else:
        debug(new_str)
        # debug(countries.keys())
    return None


def get_url(url):
    urllib3.disable_warnings()
    requests.packages.urllib3.disable_warnings(InsecureRequestWarning)
    session = requests.session()
    session.max_redirects = 10
    session.verify = False
    session.timeout = (20, 20)

    url = unquote(url)
    o = urlparse(url)
    query = parse_qs(o.query, True)
    url_short = o._replace(query=None).geturl()
    query['limit'] = 10000
    if 'user' in query and 'pass' in query:
        g = session.get(url_short, params=query, auth=(query['user'][0], query['pass'][0]))
    else:
        g = session.get(url_short, params=query)

    try:
        response_json = g.content.decode('utf-8').replace('\0', '')
        return json.loads(response_json)
    except Exception as e:
        return json.loads('{"Error": %s}' % e)


def process(response, network, routing):
    rabbit_send('Start with process response!', routing)
    if 'offers' in response:
        raw_content = response.get('offers')
    elif 'response' in response:
        raw_content = response.get('response').get('data')
    elif 'data' in response and 'rowset' in response.get('data'):
        raw_content = response.get('data').get('rowset')
    else:
        raw_content = response

    if raw_content:
        if isinstance(raw_content, dict):
            raw_content = raw_content.values()

        offer_pool = Pool(500)
        for content in raw_content:
            if isinstance(content, dict):
                if 'Offer' in content:
                    offer_pool.spawn(parse_offer, content.get('Offer'), network, routing)
                else:
                    # rabbit_send('View content %s' % repr(content), routing)
                    offer_pool.spawn(parse_offer, content, network, routing)
            else:
                #rabbit_send('Raw content is not dictionary!', routing)
                rabbit_send('Raw content is not dictionary %s' % repr(content), routing)

        offer_pool.join()
    else:
        debug('Not have Raw Content')


def get_device(content):
    if 'devices' in content:
        return content.get('devices')

    if 'Platforms' in content:
        return content.get('Platforms')

    if 'platform' in content:
        return content.get('platform')

    if 'offer_platform' in content and 'target' in content.get('offer_platform'):
        return content.get('offer_platform').get('target')

    if 'payments' in content:
        payments = content.get('payments')
        if isinstance(payments, list):
            for payment in payments:
                if 'os' in payment and payment.get('os'):
                    return payment.get('os')

    if 'payments' in content:
        payments = content.get('payments')
        if isinstance(payments, list):
            for payment in payments:
                if 'devices' in payment and payment.get('devices'):
                    return payment.get('devices')

    if 'categories' in content:
        categories = content.get('categories')
        if isinstance(categories, list):
            return ', '.join([str(x) for x in categories])
    if 'Goals' in content:
        temp_devices = content.get('Goals')
        for temp_device in temp_devices:
            if 'Platforms' in temp_device:
                return temp_device.get('Platforms')



def get_payout(content):
    if isinstance(content, int) or isinstance(content, basestring):
        return None

    if 'payout' in content:
        return content.get('payout')

    if 'cost' in content:
        return content.get('cost')

    if 'price' in content:
        return content.get('price')

    if 'offer' in content and 'payout' in content.get('offer'):
        return content.get('offer').get('payout')

    if 'default_payout' in content:
        return content.get('default_payout')

    if 'rate' in content:
        return content.get('rate')

    if 'payments' in content:
        payments = content.get('payments')
        if isinstance(payments, list):
            for payment in payments:
                if 'revenue' in payment:
                    return payment.get('revenue')
        if isinstance(payments, dict):
            if 'revenue' in payments:
                return payments.get('revenue')

    if 'Payout' in content:
        return content.get('Payout')
    if 'Goals' in content:
        temp_payouts = content.get('Goals')
        for temp_payout in temp_payouts:
            if 'Payout' in temp_payout:
                return temp_payout.get('Payout')

    return None


def get_redirect_link(content):
    if isinstance(content, int) or isinstance(content, basestring):
        return None

    if 'tracking_link' in content:
        return content.get('tracking_link')

    if 'click_url' in content:
        return content.get('click_url')

    if 'tracklink' in content:
        return content.get('tracklink')

    if 'offer' in content and 'tracking_link' in content.get('offer'):
        return content.get('offer').get('tracking_link')

    if 'tracking_url' in content:
        return content.get('tracking_url')

    if 'Tracking_url' in content:
        return content.get('Tracking_url')

    if 'offer_url' in content:
        return content.get('offer_url')

    if 'link' in content:
        return content.get('link')


def get_geo_locations(content):
    if isinstance(content, int) or isinstance(content, basestring):
        return None

    if 'countries' in content:
        temp_country = content.get('countries')
        geo_string = []
        if isinstance(temp_country, basestring):
            geo_string.append(temp_country)
        else:
            for country in temp_country:
                if 'code' in country:
                    geo_string.append(country.get('code'))
                else:
                    geo_string.append(country)
        return ','.join(geo_string)

    if 'offer_geo' in content and 'target' in content.get('offer_geo'):
        geo_string = []
        for country in content.get('offer_geo').get('target'):
            if 'country_code' in country:
                geo_string.append(country.get('country_code'))
        return ','.join(geo_string)

    if 'geos' in content:
        return ','.join(content.get('geos'))
    if 'Countries' in content:
        return content.get('Countries')

    if 'geo' in content:
        return content.get('geo')

    if 'payments' in content:
        payments = content.get('payments')
        if isinstance(payments, list):
            for payment in payments:
                if 'countries' in payment:
                    countries = payment.get('countries')
                    if not countries:
                        return ','.join(['US', 'GB'])
                    return ','.join(countries)


def get_net_offer_id(content):
    if isinstance(content, int) or isinstance(content, basestring):
        return None

    if 'ID' in content:
        return content.get('ID')

    if 'id' in content:
        return content.get('id')

    if 'offer_id' in content:
        return content.get('offer_id')

    if 'offer' in content and 'id' in content.get('offer'):
        return content.get('offer').get('id')

    if 'offerid' in content:
        return content.get('offerid')

    if 'camp_id' in content:
        return content.get('camp_id')

    return None


def get_offer_name(content):
    if isinstance(content, int) or isinstance(content, basestring):
        return None

    if 'name' in content:
        return content.get('name')

    if 'Name' in content:
        return content.get('Name')

    if 'offer_name' in content:
        return content.get('offer_name')

    if 'app_name' in content:
        return content.get('app_name')

    if 'title' in content:
        return content.get('title')

    if 'offer' in content and 'name' in content.get('offer'):
        return content.get('offer').get('name')

    return None


def parse_offer(content, network, routing):
    # rabbit_send('Start with process each offer!', routing)
    # rabbit_send('Start with process each offer %s' % repr(content), routing)
    offer_name = get_offer_name(content)
    if offer_name:
        offer_name = str(offer_name)[:191]
    else:
        rabbit_send('Error when get offer Name %s' % repr(content), routing)

    payout = get_payout(content)

    if payout:
        payout = str(payout).replace('$', '')
        if network.rate_offer > 0:
            payout = round(float(payout) / int(network.rate_offer), 2)
        else:
            payout = round(float(payout), 2)
    else:
        rabbit_send('Error when get offer payout %s' % repr(content), routing)

    net_offer_id = get_net_offer_id(content)

    if net_offer_id:
        net_offer_id = int(net_offer_id)
    else:
        rabbit_send('Error when get offer net_offer_id %s' % repr(content), routing)


    geo_locations = get_geo_locations(content)

    if not geo_locations and offer_name:
        geo_locations = get_country_codes_from_string(offer_name)

    if geo_locations:
        geo_locations = geo_locations.upper().replace('|', ',')
    else:
        rabbit_send('Error when get offer geo_locations %s' % repr(content), routing)

    devices = get_device(content)

    android = False
    ios = False
    real_device = 1

    if not devices and offer_name:
        devices = get_device_from_string(offer_name)

    if devices:
        if isinstance(devices, basestring):
            devices = devices.split(',')

        if isinstance(devices, dict):
            devices = devices.values()

        for device in devices:
            if isinstance(device, dict) and 'device_type' in device:
                temp_device = str(device.get('device_type')).lower()
            else:
                temp_device = str(device).lower()

            if 'ios' in temp_device or 'ipad' in temp_device or 'iphone' in temp_device:
                ios = True

            if 'droid' in temp_device:
                android = True

        if ios and android:
            real_device = 2
        elif android:
            real_device = 4
        elif ios:
            real_device = 5
    else:
        rabbit_send('Error when get offer devices %s' % repr(content), routing)

    redirect_link = get_redirect_link(content)

    if not redirect_link:
        if net_offer_id and 'adwool' in network.cron:
            api_key = None
            try:
                parse = urlparse(network.cron, allow_fragments=False)
                api_key = parse_qs(parse.query)['api_key'][0]

            except Exception as e:
                pass
            if api_key is not None:
                get_link_through_api = 'https://adwool.api.hasoffers.com/Apiv3/json?api_key=' + api_key + '&Target=Affiliate_Offer&Method=generateTrackingLink&offer_id=' + str(
                    net_offer_id)
                link_response = None
                try:
                    link_response = get_url(get_link_through_api)
                except Exception as e:
                    pass
                if link_response is not None:
                    if 'response' in link_response and 'data' in link_response.get(
                            'response') and 'click_url' in link_response.get('response').get('data'):
                        redirect_link = link_response.get('response').get('data').get('click_url')

    if redirect_link:
        if redirect_link and '&clickid={clickid}&gaid={gaid}' in redirect_link:
            redirect_link = redirect_link.replace(
                '&clickid={clickid}&gaid={gaid}&android={android}&idfa={idfa}&subid={subid}', '')
            redirect_link += '&subid=#subId'
        else:
            redirect_link += '&aff_sub=#subId'

    else:
        rabbit_send('Error when get offer redirect_link %s' % repr(content), routing)

    if redirect_link and net_offer_id and geo_locations and payout and offer_name:

        datetime_str = datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')

        try:

            Offer.objects.update_or_create(
                net_offer_id=net_offer_id, network=network,
                defaults={
                    'name': offer_name,
                    'click_rate': payout,
                    'redirect_link': redirect_link,
                    'geo_locations': geo_locations,
                    'allow_devices': real_device,
                    'number_when_click': network.virtual_click,
                    'number_when_lead': network.virtual_lead,
                    'check_click_in_network': True,
                    'auto': True,
                    'updated_at': datetime_str,
                    'created_at': datetime_str,
                },
            )
            rabbit_send('Done with offer_net_id=%s' % str(net_offer_id), routing)
        except Exception as e:
            # debug('Exception while create offer %s' % repr(e))
            rabbit_send('Exception while create offer %s' % repr(e), routing)

    else:
        # debug('Some values is missing %s' % repr(content))
        rabbit_send('Some values is missing %s' % repr(content), routing)

    return None


def logistic(url, network, routing):
    response_data = get_url(url)
    process(response_data, network, routing)


def get_request_field(request, field_name, include_filter_field=True):

    res = request.GET.get(field_name, None)

    if res is None and include_filter_field is True:
        return request.GET.get("filter_" + field_name, None)

    return res


def filter_offer(qs, request):
    # simple example:
    search_name = get_request_field(request, "name")
    if search_name:
        qs = qs.filter(name__icontains=search_name)

    # more advanced example
    filter_country = get_request_field(request, "country")

    if filter_country:
        qs = qs.filter(geo_locations__icontains=filter_country)

    filter_device = get_request_field(request, "device")
    if filter_device:
        filter_device = int(filter_device)
        qs = qs.filter(allow_devices__in=[5, 6, 7]) if filter_device == 5 else qs.filter(allow_devices=filter_device)

    filter_network_id = get_request_field(request, "network_id")
    if filter_network_id:
        filter_network_id = int(filter_network_id)
        qs = qs.filter(network=filter_network_id)

    filter_uid = get_request_field(request, "uid")

    if filter_uid:
        filter_uid = int(filter_uid)
        qs = qs.filter(Q(id=filter_uid) | Q(net_offer_id=filter_uid))

    filter_auto = get_request_field(request, "auto")
    if filter_auto:
        filter_auto = True if filter_auto == '1' else False
        qs = qs.filter(auto=filter_auto)

    filter_active = get_request_field(request, "active")
    if filter_active:
        filter_active = True if filter_active == '1' else False
        qs = qs.filter(active=filter_active)

    filter_reject = get_request_field(request, "reject")
    if filter_reject:
        filter_reject = True if filter_reject == '1' else False
        qs = qs.filter(reject=filter_reject)

    return qs


def filter_statistic(qs, request):

    if not request.user.is_superuser:
        networks = Network.objects.filter(user=request.user)
        qs = qs.filter(offer_network_id__in=[x.id for x in networks])

    # simple example:
    search_name = get_request_field(request, "name")
    if search_name:
        qs = qs.filter(offer_name__icontains=search_name)

    # more advanced example
    filter_country = get_request_field(request, "country")

    if filter_country:
        qs = qs.filter(offer_geos__icontains=filter_country)

    filter_date = get_request_field(request, "date")

    if filter_date:
        temp_date = filter_date.split(" - ")
        start_date = datetime.datetime.strptime(temp_date[0] + " 00:00:00", "%d/%m/%Y %H:%M:%S")
        end_date = datetime.datetime.strptime(temp_date[1] + " 23:59:59", "%d/%m/%Y %H:%M:%S")
        qs = qs.filter(lead_time__gte=start_date).filter(lead_time__lte=end_date)

    filter_device = get_request_field(request, "device")
    if filter_device:
        filter_device = int(filter_device)
        qs = qs.filter(offer_device__in=[5, 6, 7]) if filter_device == 5 else qs.filter(
            offer_device=filter_device)

    filter_network_id = get_request_field(request, "network_id")
    if filter_network_id:
        filter_network_id = int(filter_network_id)
        qs = qs.filter(offer_network_id=filter_network_id)

    filter_user_id = get_request_field(request, "user_id")
    if filter_user_id:
        filter_user_id = int(filter_user_id)
        qs = qs.filter(click_user_id=filter_user_id)

    filter_uid = get_request_field(request, "uid")

    if filter_uid:
        filter_uid = int(filter_uid)
        qs = qs.filter(Q(offer_id=filter_uid) | Q(offer_net_id=filter_uid))

    return qs


def filter_network(qs, request):
    # simple example:
    search_name = request.GET.get(u'name', None)
    if search_name:
        qs = qs.filter(name__icontains=search_name)

    filter_active = request.GET.get('active', None)
    if filter_active:
        filter_active = True if filter_active == '1' else False
        qs = qs.filter(active=filter_active)

    return qs


def check_device_offer(offer, request):

    user_agent_str = str(request.user_agent).lower()

    if offer.allow_devices == 1:
        return True

    if offer.allow_devices == 2 and request.user_agent.is_mobile is False:
        return False

    if offer.allow_devices == 3 and request.user_agent.is_pc is False:
        return False

    if offer.allow_devices == 4 and (request.user_agent.is_mobile is False or 'droid' not in user_agent_str):
        return False

    if offer.allow_devices == 5 and ('ios' not in user_agent_str and 'iphone' not in user_agent_str and 'ipad' not in user_agent_str):

        return False

    return True


def get_client_ip(request):
    x_forwarded_for = request.META.get('HTTP_X_FORWARDED_FOR')
    if x_forwarded_for:
        ip = x_forwarded_for.split(',')[-1].strip()
    else:
        ip = request.META.get('REMOTE_ADDR')
    return ip


def get_country_code_by_ip(ip):
    try:
        reader = geolite2.reader()
        match = reader.get(ip)

        if 'country' in match:
            return match['country']['iso_code']

        url = 'http://api.ipstack.com/{0}?access_key={1}&format=1'.format(ip, IP_STACK_API_KEY)

        response = urlopen(url)
        data = json.load(response)
        if 'country_code' in data:
            return data['country_code']

    except Exception as e:
        pass

    return


def get_ip_and_location(offer, request):
    status = True
    ip = get_client_ip(request)
    location = get_country_code_by_ip(ip)
    geo_location_str = [str(x.code) for x in offer.geo_locations]
    if 'GB' in geo_location_str:
        geo_location_str += ', UK'
    if 'UK' in geo_location_str:
        geo_location_str += ', GB'

    if geo_location_str and location not in geo_location_str:
        status = False

    if ip in ['127.0.0.1', '10.0.2.2']:
        status = True
        if location is None:
            location = 'VN'

    return status, location, ip


def get_display_devices(device):
    devices = {1: "All", 2: "Mobile", 3: "Desktop", 4: "Only Android Mobiles (Phone && Tablet)",
               5: "Only iOS Mobiles (Phone && Tablet)"}

    return devices[device]


def create_statistic_on_lead(lead):
    # Store in statistic table.

    try:
        Statistic.objects.create(
            lead_id=lead.id,
            lead_json=lead.request_log,
            lead_time=lead.updated_at,

            click_id=lead.click.id,
            click_user_id=lead.click.who_lead.id,
            click_user_name=lead.click.who_lead.username,
            click_ip=lead.click.click_ip,
            click_time=lead.click.updated_at,

            offer_id=lead.click.offer.id,
            offer_name=lead.click.offer.name,
            offer_net_id=lead.click.offer.net_offer_id,
            offer_click_rate=lead.click.offer.click_rate,
            offer_network_id=lead.click.offer.network.id,
            offer_network_name=lead.click.offer.network.name,
            offer_device=lead.click.offer.allow_devices,
            offer_geos=', '.join([x.code for x in lead.click.offer.geo_locations]),
            offer_redirect_link=lead.click.offer.redirect_link,

        )
    except Exception as e:
        debug(str(e))


def ago(value):
    try:
        difference = now() - value
    except:
        return value

    if difference <= datetime.timedelta(minutes=1):
        return 'just now'
    return '%(time)s ago' % {'time': timesince(value).split(', ')[0]}


def chunk(it, size):
    it = iter(it)
    return iter(lambda: tuple(islice(it, size)), ())


def cron_network(item_id, routing):
    try:
        network = Network.objects.get(pk=item_id)
        if not network.cron_url:
            raise ValueError('No cron url')
        Offer.objects.filter(network=network).filter(net_offer_id__isnull=True).delete()

        if 'mobilebull' in network.cron_url or 'impany.afftrack.com' in network.cron_url:
            response = get_url(network.cron_url + '&only_pids=1')
        else:
            response = get_url(network.cron_url)
        if not response:
            raise ValueError('None Response')
        list_extra_url = []
        total_page = None
        total_limit = None




        rabbit_send('Done get response from url %s' % network.cron_url, routing)

        if 'response' in response:
            response = response.get('response')

        if 'ads' in response:
            response = response.get('ads')

        if 'data' in response and 'data' in response.get('data'):
            response = response.get('data').get('data')

        if 'data' in response and 'totalPages' in response.get('data'):
            total_page = response.get('data').get('totalPages')
            total_limit = response.get('data').get('limit')

        if total_page is not None and total_limit is not None:
            for item in list(range(total_page)):
                url_extra = network.cron + '&limit=' + str(total_limit) + '&offset=' + str(item * total_limit)
                list_extra_url.append(url_extra)

        if 'mobilebull' in network.cron_url or 'impany.afftrack.com' in network.cron_url and 'offers' in response:
            for ids in chunk(response.get('offers'), 50):
                url_extra = network.cron_url + '&pids_list=' + ','.join(x for x in ids)
                list_extra_url.append(url_extra)

        if 'api.iwoop.com' in network.cron_url:
            for item in list(range(10)):
                url_extra = network.cron_url + '&page=' + str(item)
                list_extra_url.append(url_extra)

        if list_extra_url:
            rabbit_send('Cron total url %s' % str(len(list_extra_url)), routing)
            process_pool = Pool(10)
            for url in list_extra_url:
                process_pool.spawn(logistic, url, network, routing)
            process_pool.join()
        else:
            process(response, network, routing)

        network.last_cron_at = now()
        network.save()

    except Exception as e:
        rabbit_send("Exception=%s while running cron for networkID=%s" % (str(e), item_id), routing)


def rabbit_send(message, routing):
    if routing != 'cron':
        connection = pika.BlockingConnection(pika.ConnectionParameters(host='localhost'))
        channel = connection.channel()
        # send a message
        channel.basic_publish(exchange='', routing_key=routing, body=message)
        connection.close()
    else:
        print(message)


def random_line():
    lines = open(settings.AGENT_PATH + "ios11.txt").read().splitlines()
    return random.choice(lines)