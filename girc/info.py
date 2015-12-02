#!/usr/bin/env python3
# Written by Daniel Oaks <daniel@danieloaks.net>
# Released under the ISC license
from .types import User, Channel, Server
from .utils import NickMask, CaseInsensitiveDict


class Info:
    """Stores state information for a server connection.

    This is where we differ from most other libraries. We store information for
    clients, users, and servers as ``girc.types.*`` objects. We pass these
    objects around directly in the Event dictionaries as they are dispatched.
    The reasons we do this are detailed in the State Tracking devnote in our
    documentation.

    The ``channels`` dict should only contain channels we are joined to.
    We should not keep track of information for channels we have parted.

    The ``users`` dict should only contain users we share channels with, or
    have sent us messages / commands. If we do not share a channel with a user,
    they may be removed from here at any time.

    The ``servers`` dict will contain all the servers we have received
    communications from in the past. We don't store much info for each server,
    and networks generally don't have a million servers, so we shouldn't need
    to worry about deleting these.
    """

    def __init__(self, server_connection):
        self.s = server_connection

        # information stores
        self.users = self.s.idict()
        self.channels = self.s.idict()
        self.servers = CaseInsensitiveDict()

        # internal event handlers
        self._in_handlers = {
            'join': self.in_join_handler,
            'part': self.in_part_handler,
            'cmode': self.in_cmode_handler,
        }

    # base event handlers
    def handle_event_in(self, event):
        # pass to specific event handlers
        handler = self._in_handlers.get(event['verb'])

        if handler:
            handler(event)

        # XXX - debug info dumping
        if event['verb'] in ['privmsg', 'pubmsg']:
            if event['message'].startswith('info'):
                from pprint import pprint
                pprint(self.json)

    def handle_event_out(self, event):
        ...

    # specific event handlers
    def in_join_handler(self, event):
        user = event['source']
        channels = event['channels']

        for chan in channels:
            if chan.name not in user.channel_names:
                user.channel_names.append(chan.name)

            if user.nick not in chan.users:
                chan.users[user.nick] = {}

            if user.nick not in chan.prefixes:
                chan.prefixes[user.nick] = ''

            if user.nick == self.s.nick:
                chan.joined = True

            if user.is_me:
                chan.get_modes()

    def in_part_handler(self, event):
        user = event['source']
        channels = event['channels']

        for chan in channels:
            if user.nick in chan.users:
                del chan.users[user.nick]

            if chan.name in user.channel_names:
                user.channel_names.remove(chan.name)

            if user.nick == self.s.nick:
                chan.joined = False

    def in_cmode_handler(self, event):
        channel = event['channel']

        for unary, char, argument in event['modes']:
            if unary == '+':
                if argument:
                    if char in channel.modes and isinstance(channel.modes[char], list):
                        if argument not in channel.modes[char]:
                            channel.modes[char].append(argument)
                    else:
                        channel.modes[char] = argument
                else:
                    channel.modes[char] = True
            elif unary == '-':
                if argument:
                    if char in channel.modes and isinstance(channel.modes[char], list):
                        if argument in channel.modes[char]:
                            channel.modes[char].remove(argument)
                else:
                    if char in channel.modes:
                        del channel.modes[char]

    # utility functions
    def create_user(self, userhost):
        if userhost == '*':
            return

        user = NickMask(userhost)

        if user.nick not in self.users:
            new_user = User(self.s, userhost)
            self.users[user.nick] = new_user
            self.s._girc_events.dispatch('create user', {
                'server': self.s,
                'user': new_user,
            })

        # XXX - rewriting these every time...
        #   do we wanna check if they're the same before we do the writes?
        self.users[user.nick].nick = user.nick
        if user.user:
            self.users[user.nick].user = user.user
        if user.host:
            self.users[user.nick].host = user.host

    def create_channel(self, channel):
        self.create_channels(channel)

    def create_channels(self, *channels):
        for channel in channels:
            if isinstance(channel, Channel):
                continue
            if channel not in self.channels:
                new_channel = Channel(self.s, channel)
                self.channels[channel] = new_channel
                self.s._girc_events.dispatch('create channel', {
                    'server': self.s,
                    'channel': new_channel,
                })

    def create_server(self, name):
        if name not in self.servers:
            self.servers[name] = Server(self.s, name)

    @property
    def json(self):
        return {
            'users': self.users.json,
            'channels': self.channels.json,
            'servers': self.servers.json,
        }
