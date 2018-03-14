#!/usr/bin/env python 

import sys
import peewee
import random
import ConfigParser
import argparse
from numpy.random import choice
from apache_logs.page import Page
from apache_logs.log import Log
from netaddr import IPAddress, IPSet, IPNetwork
from datetime import date, time, datetime, timedelta

day_weights, hour_weights, referers = {}, {}, {}
site_pages, site_auxiliaries, user_agents = {}, {}, {}
return_on_404, follow_link, no_referer = None, None, None
domain, starting_proto, estimated_log_bytes, time_zone_offset = None, None, None, None
default_404_size, default_image_size, default_script_size, default_css_size = None, None, None, None

invalid_ips = IPSet()
for net in ('0.0.0.0/8', '10.0.0.0/8', '127.0.0.0/8', '172.16.0.0/12', '192.168.0.0/16', '224.0.0.0/4', '240.0.0.0/4'):
    invalid_ips.add(IPNetwork(net))

db_name = 'temp-logs.db'
db = peewee.SqliteDatabase(None)


class LogModel(peewee.Model):
    source_ip = peewee.TextField()
    address = peewee.TextField()
    status = peewee.IntegerField()
    size = peewee.IntegerField()
    user_agent = peewee.TextField()
    timestamp = peewee.DateTimeField()
    user = peewee.TextField()
    referer = peewee.TextField()

    class Meta:
        order_by = ('timestamp',)
        database = db


class VerboseParser(argparse.ArgumentParser):
    def error(self, message):
        self.print_help()
        sys.stderr.write('\n** Error: %s\n' % message)
        sys.exit(2)


def output_log(source_ip, address, status, size, user_agent, timestamp, user=None, referer=None):
    result = '%s - %s [%s %s]' % (source_ip, user, Log._convert_timestamp(timestamp), time_zone_offset)
    result += ' "GET %s HTTP/1.1" %s %s' % (address, status, size)
    result += ' "%s" "%s"' % (referer, user_agent)
    return result


def random_seconds():
    return random.randint(5, 300)


def random_minor_seconds():
    return choice([0, 1, 2], p=[.82, .16, (1-.82-.16)])


def random_ipaddr():
    # 2 ^ 32 = 4294967296, subtract one to get 4294967295
    addr = IPAddress(random.randint(1, 4294967295))
    while addr in invalid_ips:
        addr = IPAddress(random.randint(1, 4294967295))

    return addr


def prep_settings(config_file):
    global return_on_404, follow_link, no_referer, estimated_log_bytes
    global default_404_size, default_image_size, default_script_size, default_css_size
    global day_weights, hour_weights, starting_proto, time_zone_offset

    config = ConfigParser.ConfigParser()
    config.read(config_file)

    estimated_log_bytes = int(config.get('General', 'estimated_log_bytes'))
    default_404_size = config.get('General', 'default_404_size')
    default_image_size = config.get('General', 'default_image_size')
    default_script_size = config.get('General', 'default_script_size')
    default_css_size = config.get('General', 'default_css_size')
    starting_proto = config.get('General', 'starting_proto')
    time_zone_offset = config.get('General', 'time_zone_offset')

    # Read in behaviors
    return_on_404 = float(config.get('Behavior', 'return_on_404'))
    follow_link = float(config.get('Behavior', 'follow_link'))
    no_referer = float(config.get('Behavior', 'no_referer'))

    # Change behaviors into true/false percentage values
    return_on_404 = (return_on_404, 1 - return_on_404)
    follow_link = (follow_link, 1 - follow_link)
    no_referer = (no_referer, 1 - no_referer)

    # Load the user agents and their percentages
    temp_agents = config.get('User Agents', 'agents').strip().split('\n')
    for c in config.get('User Agents', 'chances').split(','):
        user_agents[temp_agents.pop(0)] = float(c.strip())

    # Load the referers and their percentages
    temp_referers = config.get('Referers', 'referers').strip().split('\n')
    for c in config.get('Referers', 'chances').split(','):
        referers[temp_referers.pop(0)] = float(c.strip())

    # This is a hack, due to floating point representation issues
    temp, _ = referers.popitem()
    referers[temp] = 1 - sum(referers.values())
    temp, _ = user_agents.popitem()
    user_agents[temp] = 1 - sum(user_agents.values())

    # Load start date, calculate end date
    year, month, day = config.get('General', 'start_date').split('-')
    start_date = date(int(year), int(month), int(day))
    year, month, day = config.get('General', 'end_date').split('-')
    end_date = date(int(year), int(month), int(day))

    # Calculate date probability weights
    day = start_date
    weight_sums = 0.0
    while day <= end_date:
        day_weights[day] = None
        if day.isoweekday() < 6:
            day_weights[day] = .176
        else:
            day_weights[day] = .06
        weight_sums += day_weights[day]
        day = day + timedelta(days=1)

    # Now we need to normalize the weights so they add to 1
    for day in day_weights:
        day_weights[day] = day_weights[day] / weight_sums

    # Load the weights for hours of the day
    for x in range(0, 22):
        hour_weights[x] = float(config.get('Hour Weights', str(x)))

    # Floating point catch all for 23:00
    hour_weights[23] = 1 - sum(hour_weights.values())


def prep_pages(config_file):
    global domain
    global_links, global_css, global_scripts, global_images = set(), set(), set(), set()

    config = ConfigParser.ConfigParser()
    config.read(config_file)

    # Read in the domain and any elements present on all pages
    global_section = 'Global'
    domain = config.get(global_section, 'domain')
    if config.has_option(global_section, 'links'):
        global_links = config.get(global_section, 'links').split(',')
        global_links = set([l.strip() for l in global_links])
    if config.has_option(global_section, 'css'):
        global_css = config.get(global_section, 'css').split(',')
        global_css = set([c.strip() for c in global_css])
    if config.has_option(global_section, 'scripts'):
        global_scripts = config.get(global_section, 'scripts').split(',')
        global_scripts = set([c.strip() for c in global_scripts])
    if config.has_option(global_section, 'images'):
        global_images = config.get(global_section, 'images').split(',')
        global_images = set([i.strip() for i in global_images])

    aux_section = 'Auxiliaries'
    if config.has_section(aux_section):
        for path in config.options(aux_section):
            size = config.get(aux_section, path)
            site_auxiliaries[path] = size

    for section in config.sections():
        # Ignore the global and auxiliary sections
        if section in (aux_section, global_section):
            continue
        if config.has_option(section, 'status') and config.get(section, 'status') == '404':
            size = config.get(section, 'size')
            if not size:
                size = default_404_size
            site_pages[section] = Page(starting_proto, domain, section, status=404, size=size)
        else:
            size = config.get(section, 'size')
            links = None

            if config.has_option(section, 'links'):
                links = config.get(section, 'links').split(',')
                links = list(set([l.strip() for l in links]).union(global_links))
            elif global_links:
                links = list(global_links)

            # Make sure we remove any links from this page to itself
            if section in links:
                links.remove(section)

            site_pages[section] = Page(starting_proto, domain, section, size=size, links=links)

            if config.has_option(section, 'css'):
                css = config.get(section, 'css').split(',')
                site_pages[section].css = list(set([c.strip() for c in css]).union(global_css))
            elif global_css:
                site_pages[section].css = list(global_css)
                
            if config.has_option(section, 'scripts'):
                scripts = config.get(section, 'scripts').split(',')
                site_pages[section].scripts = list(set([s.strip() for s in scripts]).union(global_scripts))
            elif global_scripts:
                site_pages[section].scripts = list(global_scripts)

            if config.has_option(section, 'images'):
                images = config.get(section, 'images').split(',')
                site_pages[section].images = list(set([i.strip() for i in images]).union(global_images))
            elif global_images:
                site_pages[section].images = list(global_images)


def random_agent():
    return choice(user_agents.keys(), p=user_agents.values())


def random_referer():
    return choice(referers.keys(), p=referers.values())


def random_page():
    return choice(site_pages.keys())


def random_datetime():
    day = choice(day_weights.keys(), p=day_weights.values())

    hour = choice(hour_weights.keys(), p=hour_weights.values())
    minute = choice(range(0,60))
    second = choice(range(0,60))
    timestamp = time(hour, minute, second)

    return datetime.combine(day, timestamp)


def check_continue():
    return choice([True, False], p=follow_link)


def check_404_continue():
    return choice([True, False], p=return_on_404)


def used_referer():
    # This is phrased as a negative in the settings, so have to flip the order.
    return choice([False, True], p=no_referer)


def browse():
    global site_pages

    extras_downloaded = []

    ip = random_ipaddr()
    agent = random_agent()
    random = random_page()
    page = site_pages[random]

    if used_referer():
        referer = random_referer()
    else:
        referer = '-'

    timestamp = random_datetime()

    if page.status == 404:
        # We assume the user won't continue after getting a bad link from a referrer
        # Images, links, etc. on 404 pages is not currently supported
        yield Log(ip, page.path, page.status, page.size, agent, timestamp, referer=referer)

    # The user is accessing a valid page, log the page and its associated content
    else:
        yield Log(ip, page.path, page.status, page.size, agent, timestamp, referer=referer)
        for c in page.css:
            if c not in extras_downloaded:
                extras_downloaded.append(c)
                timestamp += timedelta(seconds=random_minor_seconds())
                size = site_auxiliaries[c] if c in site_auxiliaries else default_css_size
                yield Log(ip, c, 200, size, agent, timestamp, referer=page.full_uri())
        for s in page.scripts:
            if s not in extras_downloaded:
                extras_downloaded.append(s)
                timestamp += timedelta(seconds=random_minor_seconds())
                size = site_auxiliaries[s] if s in site_auxiliaries else default_script_size
                yield Log(ip, s, 200, size, agent, timestamp, referer=page.full_uri())
        for i in page.images:
            if i not in extras_downloaded:
                extras_downloaded.append(i)
                timestamp += timedelta(seconds=random_minor_seconds())
                size = site_auxiliaries[i] if i in site_auxiliaries else default_image_size
                yield Log(ip, i, 200, size, agent, timestamp, referer=page.full_uri())

        # While the user continues to pass the check (they haven't finished navigating), try accessing another page
        while check_continue():
            # Assume they've stayed on the previous page some random amount of time
            timestamp = timestamp + timedelta(seconds=random_seconds())

            parent_page = page

            # If there are no links on this page to navigate to another page, user is done
            next_page_path = parent_page.random_link()
            if not next_page_path:
                break
            else:
                page = site_pages[next_page_path]

            # If it's a bad link, see if user continues or gives up
            while page.status == 404:
                yield Log(ip, page.path, page.status, page.size, agent, timestamp, referer=parent_page.full_uri())

                if check_404_continue():
                    # Assume it took about five seconds for them to go back
                    timestamp = timestamp + timedelta(seconds=5)

                    # Choose a different link from the parent page
                    link = parent_page.random_link()
                    while link == page.path:
                        link = parent_page.random_link()

                    page = site_pages[link]
                else:
                    # We failed the roll for continuing, user is done
                    return

            # User has chosen a valid page, log the page and its associated content
            yield Log(ip, page.path, page.status, page.size, agent, timestamp, referer=parent_page.full_uri())
            for c in page.css:
                if c not in extras_downloaded:
                    extras_downloaded.append(c)
                    timestamp += timedelta(seconds=random_minor_seconds())
                    size = site_auxiliaries[c] if c in site_auxiliaries else default_css_size
                    yield Log(ip, c, 200, size, agent, timestamp, referer=page.full_uri())
            for s in page.scripts:
                if s not in extras_downloaded:
                    extras_downloaded.append(s)
                    timestamp += timedelta(seconds=random_minor_seconds())
                    size = site_auxiliaries[s] if s in site_auxiliaries else default_script_size
                    yield Log(ip, s, 200, size, agent, timestamp, referer=page.full_uri())
            for i in page.images:
                if i not in extras_downloaded:
                    extras_downloaded.append(i)
                    timestamp += timedelta(seconds=random_minor_seconds())
                    size = site_auxiliaries[i] if i in site_auxiliaries else default_image_size
                    yield Log(ip, i, 200, size, agent, timestamp, referer=page.full_uri())


if __name__ == '__main__':

    parser = VerboseParser(description='Produces a simulation of real Apache logs, given a site structure.')
    arg_group = parser.add_mutually_exclusive_group()
    arg_group.add_argument('-n', '--num', help='approximate number of logs to generate (defaults to 100)', type=int,
                            default=100)
    arg_group.add_argument('-k', '--kb', type=int, help='estimated amount of disk to take up once files are written to'
                                                        ' disk, in kilobytes')
    arg_group.add_argument('-m', '--mb', type=int, help='estimated amount of disk to take up once files are written to'
                                                        ' disk, in megabytes', )
    parser.add_argument('-c', '--config', type=str, help='general configuration file (defaults to settings.conf)',
                           default='settings.conf')
    parser.add_argument('-p', '--pages', type=str, help='site pages configuration file (defaults to pages.conf)',
                           default='pages.conf')
    parser.add_argument('-s', '--sort', action='store_true', help='sort the output by timestamp (defaults to false)',
                        default=False)
    args = parser.parse_args()

    prep_settings(args.config)

    if args.kb:
        log_count = int(args.kb * 1024 / estimated_log_bytes)
    elif args.mb:
        log_count = int(args.mb * 1024 * 1024 / estimated_log_bytes)
    else:
        log_count = args.num

    prep_pages(args.pages)

    # If we're going to be sorting, initialize an SQLite database
    SORT = args.sort
    if SORT:
        db.init(db_name)
        db.connect()
        try:
            db.create_table(LogModel)
        except peewee.OperationalError:
            # TODO - I've run into an issue where I can't seem to actually close the database in order to remove it
            db.drop_table(LogModel)

    while log_count > 0:
        for x in browse():
            if not SORT:
                print output_log(x.source_ip, x.address, x.status, x.size, x.user_agent, x.timestamp, x.user,
                                 x.referer)
            else:
                with db.transaction():
                    LogModel.create(
                        source_ip=x.source_ip,
                        address=x.address,
                        status=x.status,
                        size=x.size,
                        user_agent=x.user_agent,
                        timestamp=x.timestamp,
                        user=x.user,
                        referer=x.referer
                    )
            log_count -= 1
            if log_count == 0:
                break

    print

    if SORT:
        query = LogModel.select(LogModel).order_by(LogModel.timestamp)
        for log in query:
            print output_log(log.source_ip, log.address, log.status, log.size, log.user_agent, log.timestamp, log.user,
                             log.referer)
        db.drop_table(LogModel)
        db.close()

