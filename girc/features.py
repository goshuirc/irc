#!/usr/bin/env python3
# Written by Daniel Oaks <daniel@danieloaks.net>
# Released under the ISC license

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
        self._dict = {}
        self.server_connection = server_connection

        # RFC1459 basics
        self.ingest('PREFIX=(ov)@+', 'CHANTYPES=#')

    def ingest(self, *parameters):
        for feature in parameters:
            if feature.startswith('-'):
                feature = feature[1:].casefold()
                if feature in self._dict:
                    try:
                        del self._dict[feature]
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
                    max_dict = {}
                    for sort in value.split(','):
                        command, limit = sort.split(':')
                        command = command.casefold()
                        max_dict[command] = limit_to_number(limit)

                elif feature == 'chanlimit':
                    limit_dict = {}
                    for sort in value.split(','):
                        chan_types, limit = sort.split(':')
                        for prefix in chan_types:
                            limit_dict[prefix] = limit_to_number(limit)
                    value = limit_dict

                if isinstance(value, str) and value.isdigit():
                    value = int(value)

                self._dict[feature] = value

                # because server sets casemapping
                if feature == 'casemapping':
                    self.server_connection.set_casemapping(value)

    def get(self, key, default=None):
        return self._dict.get(key, default)

    def has(self, key):
        return key in self._dict
