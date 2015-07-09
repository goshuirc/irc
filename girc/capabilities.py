#!/usr/bin/env python3
# Written by Daniel Oaks <daniel@danieloaks.net>
# Released under the ISC license
from .utils import CaseInsensitiveDict, CaseInsensitiveList


def cap_list(caps):
    """Given a cap string, return a list of cap, value."""
    out = []
    caps = caps.split()

    for cap in caps:
        # strip first initial =/~
        if cap.startswith('=') or cap.startswith('~'):
            cap = cap[1:]

        if '=' in cap:
            cap, value = cap.rsplit('=', 1)
        else:
            value = True

        out.append([cap, value])

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
            for cap, value in cap_list(parameters[0]):
                self.available[cap] = value

        elif cmd == 'ack':
            for cap, value in cap_list(parameters[0]):
                if cap not in self.enabled:
                    self.enabled.append(cap)

        elif cmd == 'nak':
            for cap, value in cap_list(parameters[0]):
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
