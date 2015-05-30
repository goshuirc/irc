#!/usr/bin/env python3
# Written by Daniel Oaks <daniel@danieloaks.net>
# Released under the ISC license
from .utils import CaseInsensitiveDict


def limit_to_number(limit):
    if limit.startswith('-') or limit.startswith('+'):
        if limit[1:].isdigit():
            return int(limit)
        return None
    if limit.isdigit():
        return int(limit)
    return None


class Features:
    """Ingests sets of ISUPPORT features and provides access to them."""
    def __init__(self, server_connection):
        self.available = CaseInsensitiveDict()
        self.server_connection = server_connection

        # RFC1459 basics
        self.ingest('PREFIX=(ov)@+', 'CHANTYPES=#', 'CASEMAPPING=rfc1459')

    def ingest(self, *parameters):
        for feature in parameters:
            if feature.startswith('-'):
                feature = feature[1:].casefold()
                if feature in self.available:
                    try:
                        del self.available[feature]
                    except KeyError:
                        pass
            else:
                if '=' in feature:
                    feature, value = feature.split('=', 1)
                else:
                    value = True

                feature = feature.casefold()

                # special processing for certain features
                if feature == 'prefix':
                    channel_modes, channel_chars = value.split(')')
                    channel_modes = channel_modes[1:]

                    value = dict(zip(channel_modes, channel_chars))
                
                elif feature == 'chanmodes':
                    value = value.split(',')

                elif feature == 'targmax':
                    maxavailable = {}
                    for sort in value.split(','):
                        command, limit = sort.split(':')
                        command = command.casefold()
                        maxavailable[command] = limit_to_number(limit)

                elif feature == 'chanlimit':
                    limitavailable = {}
                    for sort in value.split(','):
                        chan_types, limit = sort.split(':')
                        for prefix in chan_types:
                            limitavailable[prefix] = limit_to_number(limit)
                    value = limitavailable

                if isinstance(value, str) and value.isdigit():
                    value = int(value)

                self.available[feature] = value

                # because server sets casemapping
                if feature == 'casemapping':
                    self.server_connection.set_casemapping(value)

    def get(self, key, default=None):
        return self.available.get(key, default)

    def has(self, key):
        return key in self.available
