#!/usr/bin/env python3
# Written by Daniel Oaks <daniel@danieloaks.net>
# Released under the ISC license
from collections import OrderedDict

from .utils import CaseInsensitiveDict

_limits = [
    'nicklen',
    'channellen',
    'topiclen',
    'userlen',
    'linelen',
]


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
        self.s = server_connection

        # RFC1459 basics, plus LINELEN
        self.ingest('PREFIX=(ov)@+', 'CHANTYPES=#', 'LINELEN=512')

        self.ingest('CHANMODES=,,,')  # this just creates empty list for us

        # casemapping is a special case
        # we want to avoid calling set_casemapping below

        # default to ascii because ascii will not munge things if we end up with
        #   rfc1459 instead. if we defauled to rfc1459 and ended up with ascii,
        #   names could already be munged without us being able to revert them
        # ditto for ascii vs rfc3454
        self.available['casemapping'] = 'ascii'

    def _simplify_feature_value(self, name, value):
        """Return simplified and more pythonic feature values."""
        if name == 'prefix':
            channel_modes, channel_chars = value.split(')')
            channel_modes = channel_modes[1:]

            # [::-1] to reverse order and go from lowest to highest privs
            value = OrderedDict(list(zip(channel_modes, channel_chars))[::-1])

            return value

        elif name == 'chanmodes':
            value = value.split(',')
            return value

        elif name == 'targmax':
            max_available = {}
            for sort in value.split(','):
                command, limit = sort.split(':')
                command = command.casefold()
                max_available[command] = limit_to_number(limit)

            return max_available

        elif name == 'chanlimit':
            limit_available = {}
            for sort in value.split(','):
                chan_types, limit = sort.split(':')
                for prefix in chan_types:
                    limit_available[prefix] = limit_to_number(limit)

            return limit_available

        elif name in _limits:
            value = limit_to_number(value)
            return value

        else:
            return value

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

                value = self._simplify_feature_value(feature, value)

                if isinstance(value, str) and value.isdigit():
                    value = int(value)

                self.available[feature] = value

                # because server sets casemapping
                if feature == 'casemapping':
                    self.s.set_casemapping(value)

    def get(self, key, default=None):
        return self.available.get(key, default)

    def has(self, key):
        return key in self.available
