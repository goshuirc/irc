#!/usr/bin/env python3
# Written by Daniel Oaks <daniel@danieloaks.net>
# Released under the ISC license
from .utils import CaseInsensitiveDict, CaseInsensitiveList

cap_modifiers = {
    '-': 'disabled',
    '~': 'sticky',  # deprecated
    '=': 'ack-required',  # deprecated
}


def cap_list(caps):
    """Given a cap string, return a list of cap, value."""
    out = []
    caps = caps.split()

    for cap in caps:
        # turn modifier chars into named modifiers
        mods = []

        while len(cap) > 0 and cap[0] in cap_modifiers:
            attr = cap[0]
            cap = cap[1:]

            mods.append(cap_modifiers[attr])

        # either give string value or None if not specified
        if '=' in cap:
            cap, value = cap.rsplit('=', 1)
            if value and cap.casefold() in ['sasl']:
                value = CaseInsensitiveList(value.split(','))
        else:
            value = None

        out.append([cap, value, mods])

    return out


class Capabilities:
    """Ingests sets of client capabilities and provides access to them."""

    def __init__(self, wanted=[]):
        self.available = CaseInsensitiveDict()
        self.wanted = CaseInsensitiveList(wanted)
        self.enabled = CaseInsensitiveList()

    def ingest(self, cmd, parameters):
        cmd = cmd.casefold()

        if cmd == 'ls':
            if parameters[0] == '*':
                caps = parameters[1]
            else:
                caps = parameters[0]

            for cap, value, mods in cap_list(caps):
                self.available[cap] = {
                    'value': value,
                    'modifiers': mods,
                }
                if cap == 'cap-notify' and cap not in self.enabled:
                    self.enabled.append(cap)

        elif cmd == 'ack':
            for cap, value, mods in cap_list(parameters[0]):
                if cap not in self.enabled:
                    self.enabled.append(cap)

        elif cmd == 'nak':
            for cap, value, mods in cap_list(parameters[0]):
                if cap in self.enabled:
                    self.enabled.remove(cap)

    @property
    def to_enable(self):
        l = []

        for cap in self.wanted:
            if cap in self.available and cap not in self.enabled:
                l.append(cap)

        return l

    def get(self, key, default=None):
        return self._dict.get(key, default)
