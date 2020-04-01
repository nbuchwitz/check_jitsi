#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# vim: ts=4:sw=4:et

# ------------------------------------------------------------------------------
# check_nextcloud.py - A check plugin for Jitsi.
# Copyright (C) 2018-2020  Nicolai Buchwitz <nb@tipi-net.de>
#
# Version: 1.0.0
#
# ------------------------------------------------------------------------------
# This program is free software; you can redistribute it and/or
# modify it under the terms of the GNU General Public License
# as published by the Free Software Foundation; either version 2
# of the License, or (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE. See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program; if not, write to the Free Software
# Foundation, Inc., 59 Temple Place - Suite 330, Boston, MA  02111-1307, USA.
# ------------------------------------------------------------------------------


import argparse
import re
import sys
from enum import Enum

import requests


class CheckState(Enum):
    OK = 0
    WARNING = 1
    CRITICAL = 2
    UNKNOWN = 3


# adapted from https://github.com/nlm/nagplug/blob/master/nagplug/__init__.py
class Threshold(object):

    def __init__(self, threshold):
        self._threshold = threshold
        self._min = 0
        self._max = 0
        self._inclusive = False
        self._parse(threshold)

    def _parse(self, threshold):
        match = re.search(r'^(@?)((~|\d*):)?(\d*)$', threshold)

        if not match:
            raise ValueError('Error parsing Threshold: {0}'.format(threshold))

        if match.group(1) == '@':
            self._inclusive = True

        if match.group(3) == '~':
            self._min = float('-inf')
        elif match.group(3):
            self._min = float(match.group(3))
        else:
            self._min = float(0)

        if match.group(4):
            self._max = float(match.group(4))
        else:
            self._max = float('inf')

        if self._max < self._min:
            raise ValueError('max must be superior to min')

    def check(self, value):
        if self._inclusive:
            return True if self._min <= value <= self._max else False
        else:
            return True if value > self._max or value < self._min else False

    def __repr__(self):
        return '{0}({1})'.format(self.__class__.__name__, self._threshold)

    def __str__(self):
        return self._threshold


class CheckJitsi:
    VERSION = '1.0.0'

    def __init__(self):
        self.args = {}
        self._statistics = None

        self._simple_modes = ['participants', 'conferences', 'audiochannels', 'videochannels', 'videostreams',
                              'total_conferences_completed', 'total_conferences_created', 'total_conferences_failed',
                              'total_partially_failed_conferences',
                              'jitter_aggregate', 'total_no_payload_channels', 'total_no_transport_channels']

        self.parse_args()
        self._baseurl = "http://{}:{}".format(self.args.hostname, self.args.port)

        self._state = CheckState.OK

        self._warning = Threshold(self.args.threshold_warning)
        self._criticial = Threshold(self.args.threshold_critical)

    def parse_args(self):
        p = argparse.ArgumentParser(description='Check command for JVB via API')

        p.add_argument("-H", "--hostname", required=False, help="JVB private api hostname", default='localhost')
        p.add_argument("-p", "--port", required=False, default=8080, help="JVB private api port")

        p.add_argument("-m", "--mode",
                       choices=['health'] + self._simple_modes,
                       required=True,
                       help="Check mode")
        p.add_argument('-w', '--warning', dest='threshold_warning', metavar='THRESHOLD',
                       help='Warning threshold for check value', default="")
        p.add_argument('-c', '--critical', dest='threshold_critical', metavar='THRESHOLD',
                       help='Critical threshold for check value', default="")
        p.add_argument("--all-metrics", action='store_true', required=False)
        p.add_argument("--ignore-metric", dest='metric_blacklist', metavar='METRIC', action='append', default=[],
                       required=False,
                       help='Ignore this metric in the performance data')
        p.add_argument("--append-metric", dest='metric_whitelist', metavar='METRIC', action='append', default=[],
                       required=False,
                       help='Append this metric in the performance data')

        self.args = p.parse_args()

    @property
    def statistics(self):
        if self._statistics is None:
            r = self._fetch('/colibri/stats')

            if r.status_code != 200:
                # TODO: handle?
                raise Exception("Could not fetch colibri stats")

            # see https://github.com/jitsi/jitsi-videobridge/blob/master/doc/statistics.md
            self._statistics = r.json()

        # TODO: more filter?
        for k in ['conference_sizes', 'current_timestamp'] + self.args.metric_blacklist:
            if k in self._statistics:
                del (self._statistics[k])

        return self._statistics

    def check_result(self, rc, message, metrics=None):
        prefix = rc.name
        message = '{} - {}'.format(prefix, message)
        perfdata = ""

        if metrics is not None and self.args.all_metrics:
            metrics.update(self.statistics)
        elif metrics is not None and self.args.metric_whitelist:
            for metric in self.args.metric_whitelist:
                if metric in self.statistics:
                    metrics[metric] = self.statistics[metric]

        if metrics:
            perfdata = '|'
            perfdata += ' '.join(
                ["{}={}".format(k, int(v)) if type(v) == bool else "{}={}".format(k, v) for k, v in metrics.items()])

        print(message, perfdata)
        sys.exit(rc.value)

    def _fetch(self, uri):
        try:
            response = requests.get(
                "{}{}".format(self._baseurl, uri),
            )
        except requests.exceptions.ConnectTimeout:
            self.check_result(CheckState.UNKNOWN, "Could not connect to JVB API: Connection timeout")
        except requests.exceptions.SSLError:
            self.check_result(CheckState.UNKNOWN, "Could not connect to JVB API: Certificate validation failed")
        except requests.exceptions.ConnectionError:
            self.check_result(CheckState.UNKNOWN,
                              "Could not connect to JVB API: Failed to resolve hostname or service is not listenings")

        return response

    def check_health(self):
        r = self._fetch('/about/health')
        healthy = r.status_code == 200
        msg = "Jitsi videobridge is healthy"

        if not healthy:
            msg = "Jitsi videobridge health check failed ({})".format(r.status_code)
            self._state = CheckState.CRITICAL

        self.check_result(self._state, msg, {})

    def _check_simple(self, name):
        value = self.statistics.get(name, 0)
        msg = "{} {}".format(value, name)

        if self._criticial.check(value):
            self._state = CheckState.CRITICAL
        elif self._warning.check(value):
            self._state = CheckState.WARNING

        self.check_result(self._state, msg,
                          {name: "{};;{};{}".format(value, self.args.threshold_warning, self.args.threshold_critical)})

    def check(self):
        if self.args.mode == 'health':
            self.check_health()
        elif self.args.mode in self._simple_modes:
            self._check_simple(self.args.mode)


nc = CheckJitsi()
nc.check()
