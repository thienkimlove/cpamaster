import re
import time

import requests
from django.db.models import Q
from requests.packages.urllib3.exceptions import InsecureRequestWarning
from gevent.pool import Pool
from bs4 import BeautifulSoup
from urllib.parse import urlparse, parse_qs, unquote
from django.utils.crypto import get_random_string

from django.core.management.base import BaseCommand
from django.db import connection

from core.helpers import random_line
from core.models import Virtual
from cpamaster.settings import LUMINATI_USER, LUMINATI_PASS


def regex_check(content):
    regex = [
        r"location\.replace\([\"\']?(https?\:\/\/[^\"\']+)",
        r"location\s*=\s*[\"\']?(https?\:\/\/[^\"\']+)",
        r"meta\s*http-equiv\s*=\s*[\"\']?refresh[\"\']?\s*content=[\"\']?\d+;(?:url\s*=)?\s*[\'\"]?(https?\:\/\/[^\"\']+)",
        r"meta\.content\s*=\s*[\"\']?\d+;\s*(?:url\s*=)?\s*[\'\"]?(https?:\/\/[^\"\']+)",
        r"meta\s*http-equiv\s*=\s*[\"\']?refresh[\"\']?\s*content=[\"\']?\d+;\s*(?:url\s*=)?\s*[\'\"]?(https?:\/\/[^\"\']+)",
        r"location\.href\s*=\s*[\"']?(https?\:\/\/[^\"']+)",
        r"\.src\s*=\s*[\"\']?(https?\:\/\/[^\"\']+)"
    ]
    find = None
    for reg in regex:
        result = re.findall(reg, content, re.IGNORECASE)
        if result:
            find = result[0].replace("'", '')
            break
    return find


def ok_check(content):
    regex = [
        r"(itms\-appss?\:\/\/[^\"\']+)",
        r"(itmss?\:\/\/[^\"\']+)",
        r"(https?\:\/\/itunes\.apple\.com[^\"\']+)",
    ]
    find = None
    for reg in regex:
        result = re.findall(reg, content, re.IGNORECASE)
        if result:
            find = result[0].replace("'", '')
            break
    return find


def get_html_content(content, kill_script=False):
    soup = BeautifulSoup(content, "html.parser")
    if kill_script:
        remove_elements = ["script", "style", 'image']
    else:
        remove_elements = ["style", 'image']
    # kill all script and style elements
    for script in soup(remove_elements):
        script.extract()  # rip it out

    # get text
    text = soup.get_text()

    # break into lines and remove leading and trailing space on each
    lines = (line.strip() for line in text.splitlines())
    # break multi-headlines into a line each
    chunks = (phrase.strip() for line in lines for phrase in line.split("  "))
    # drop blank lines
    return '\n'.join(chunk for chunk in chunks if chunk)


def proxy(url, country, agent, rand):

    result = None
    credentials = 'lum-{0}-country-{1}-session-{2}:{3}'.format(LUMINATI_USER, country.lower(), rand.lower(), LUMINATI_PASS)

    if credentials is not None:

        proxies = {
            "http": "http://" + credentials + "@zproxy.luminati.io:22225",
            "https": "https://" + credentials + "@zproxy.luminati.io:22225",
        }
        session = requests.session()
        session.max_redirects = 10
        session.verify = False
        session.timeout = (60, 30)
        session.headers.update({'User-Agent': agent})
        session.proxies.update(proxies)

        url = unquote(url)
        url = url.replace('&amp;', '&')

        if ok_check(url) is not None:
            result = 'OK! URL=' + url

        if result is None:
            try:
                o = urlparse(url)
                query = parse_qs(o.query, True)
                url_short = o._replace(query=None).geturl()
                g = session.get(url_short, params=query)
                result = get_html_content(g.content)
                result = result.replace('\/', '/')

            except requests.exceptions.Timeout as e:
                # Maybe set up for a retry, or continue in a retry loop
                result = "Timeout %s" % e
            except requests.exceptions.TooManyRedirects as e:
                # Tell the user their URL was bad and try a different one
                result = "TooManyRedirects %s" % e
            except requests.exceptions.ContentDecodingError as e:
                # Tell the user their URL was bad and try a different one
                result = "ContentDecodingError %s" % e
            except requests.exceptions.ProxyError as e:
                # Tell the user their URL was bad and try a different one
                result = "ProxyError %s" % e
            except requests.exceptions.InvalidURL as e:
                # Tell the user their URL was bad and try a different one
                result = "InvalidURL %s" % e
            except requests.exceptions.ConnectionError as e:
                # Tell the user their URL was bad and try a different one
                result = "ConnectionError %s" % e
            except UnicodeError as err:
                result = "{ 'error' : " + format(
                    err) + ", 'url' : " + url + ", 'agent' : " + agent + ", 'country' : " + country + ", 'rand' : " + rand + " }"
            except Exception as err:
                result = "Exception %s for %s" % (repr(err), url)

        if 'ogp.me/ns' in result:
            result = 'OK! URL=' + url
        if 'Connecting to the iTunes Store' in result:
            result = 'OK! URL=' + url
        check_in_content = ok_check(result)
        if check_in_content is not None:
            result = 'OK! URL=' + check_in_content
        if 'not available' in result:
            result = 'Error! Reason=' + get_html_content(result, True)
        if 'temporarily unavailable' in result:
            result = 'Error! Reason=' + get_html_content(result, True)
        if 'ProxyError' in result or 'ConnectionError' in result or 'TooManyRedirects' in result:
            result = 'Error! Reason=' + get_html_content(result, True)

    return result


def regex_without_scheme(content, url):
    special = [
        r"\s*content=[\"\']?\d+;(?:url\s*=)?\s*[\'\"]?([^\"\']+)"
    ]
    parse_url = urlparse(url)
    domain = '{uri.scheme}://{uri.netloc}'.format(uri=parse_url)
    find = None
    for reg in special:
        result = re.findall(reg, content, re.IGNORECASE)
        if result:
            find = result[0].replace("'", '')
            break
    if find is not None:
        find = domain + find
    return find


def virtual_curl(country, url, rand, agent, redirection=0):
    is_ok = True
    try:
        result = proxy(url, country, agent, rand)
        if not result:
            is_ok = False
    except Exception as err:
        result = "Error {}".format(err)
        is_ok = False
    # change from 6 to 3 for proxy traffic
    if redirection < 3 and is_ok:
        check = regex_check(result)
        if check is not None:
            redirection = redirection + 1
            return virtual_curl(country, check, rand, agent, redirection)
        else:
            special_check = regex_without_scheme(result, url)
            if special_check is not None:
                redirection = redirection + 1
                return virtual_curl(country, special_check, rand, agent, redirection)
    if isinstance(result, str) and len(result) > 2000 and is_ok:
        end_result = result[:2000]
    else:
        end_result = result

    return end_result


def fetch_item(log_id, country, allow, link):
    rand = get_random_string(length=8, allowed_chars='abcdefghijklmnopqrstuvwxyz123456789')

    agent_row = random_line() if allow > 4 else 'Mozilla/5.0 (Linux; Android 5.0.1; SAMSUNG SM-N920K Build/LRX22C) AppleWebKit/537.36 (KHTML, like Gecko) SamsungBrowser/3.4 Chrome/34.0.1847.118 Mobile Safari/537.36'

    user_country = country.lower().replace(' ', ',')
    if ',' in user_country:
        user_country = user_country.split(',')[0]
    response = virtual_curl(user_country, link, rand, agent_row)
    item = Virtual.objects.get(pk=log_id)

    try:
        item.agent = agent_row
        item.log = response
        item.sent = True
        item.process = None
        item.save()
    except Exception as e:
        item.agent = agent_row
        item.log = 'Error when insert response {}'.format(e)
        item.sent = True
        item.process = None
        item.save()


class Command(BaseCommand):
    help = 'Running virtual clicks'

    def handle(self, *args, **options):
        start_time = time.time()
        requests.packages.urllib3.disable_warnings(InsecureRequestWarning)
        # connection.allow_thread_sharing = True
        rand_process = get_random_string(length=16, allowed_chars='abcdefghijklmnopqrstuvwxyz123456789')
        Virtual.objects.filter(Q(sent=False) & Q(process=None)).update(process=rand_process)
        pool = Pool()
        logs = Virtual.objects.filter(Q(sent=False) & Q(process=rand_process))
        for log in logs:
            pool.spawn(fetch_item, log.id, log.country, log.allow, log.link)
        pool.join()
        end_time = time.time()
        self.stdout.write(self.style.SUCCESS('Successfully end clicks in "%s"' % (end_time - start_time)))
