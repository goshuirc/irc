#!/usr/bin/env python3
# Written by Daniel Oaks <daniel@danieloaks.net>
# Released under the ISC license
from .utils import NickMask


class Info:
    """Stores state information for a server connection."""
    def __init__(self, server_connection):
        self.s = server_connection

        # information stores
        self.users = self.s.idict()
        self.channels = self.s.idict()

        # event handlers
        self.s.register_event('all', 'in', self.update_info)

    def update_info(self, info):
        if info['verb'] == 'join':
            user = NickMask(info['source'])
            channels = info['params'][0].split(',')

            self.create_user(info['source'])
            self.create_channels(*channels)

            for chan in channels:
                if chan not in self.users[user.nick]['channels']:
                    self.users[user.nick]['channels'].append(chan)

                if user.nick not in self.channels[chan]['users']:
                    self.channels[chan]['users'][user.nick] = {}

        # debug info dumping
        if info['verb'] in ['privmsg', 'pubmsg']:
            if info['message'].startswith('info'):
                from pprint import pprint
                pprint(self.json)

    def create_user(self, userhost):
        user = NickMask(userhost)

        if user.nick not in self.users:
            self.users[user.nick] = {
                'channels': self.s.ilist(),
                'modes': {},
            }

        # XXX - rewriting these every time...
        #   do we wanna check if they're the same before we do the writes?
        self.users[user.nick]['nick'] = user.nick
        if user.user:
            self.users[user.nick]['user'] = user.user
        if user.host:
            self.users[user.nick]['host'] = user.host

    def create_channels(self, *channels):
        for channel in channels:
            if channel not in self.channels:
                self.channels[channel] = {
                    'users': self.s.idict(),
                }

    @property
    def json(self):
        return {
            'users': self.users.json,
            'channels': self.channels.json,
        }
