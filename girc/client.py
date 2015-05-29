#!/usr/bin/env python3
# Written by Daniel Oaks <daniel@danieloaks.net>
# Released under the ISC license
import asyncio

from ircreactor.events import EventManager
from ircreactor.envelope import RFC1459Message

from .capabilities import Capabilities
from .features import Features
from .imapping import IDict, IString
from .events import numerics

loop = asyncio.get_event_loop()


def message_to_event(direction, message):
    """Prepare an ``RFC1459Message`` for event dispatch.

    We do this because we have to handle special things as well.
    """
    # change numerics into nice names
    if message.verb in numerics:
        message.verb = numerics[message.verb]

    # differentiate between private and public messages
    verb = message.verb.lower()
    if verb == 'privmsg':
        if message.server.is_channel(message.arguments[0]):
            verb = 'pubmsg'

    # this is the same as ircreactor does
    info = message.__dict__
    info['direction'] = direction
    return 'girc ' + verb + ' ' + direction, info



class ServerConnection(asyncio.Protocol):
    def __init__(self, name=None, reactor=None, nick=None, user=None, real='*'):
        self.connected = False
        self.ready = False
        self.events = EventManager()
        self._new_data = ''

        # name used for this server, eg: rizon
        self.name = name

        # client info
        self.nick = nick
        self.user = user
        self.real = real
        self.autojoin_channels = []

        # generated info
        self.clients = IDict()
        self.channels = IDict()
        self.capabilities = Capabilities(wanted=[
            'account-notify',
            'account-tag',
            'away-notify',
            'cap-notify',
            'chghost',
            'extended-join',
            'invite-notify',
            'metadata',
            'monitor',
            'multi-prefix',
            'sasl',
            'server-time',
            'userhost-in-names',
        ])
        self.features = Features(self)

        # events
        self.register_event('cap', self.rpl_cap)
        self.register_event('features', self.rpl_features)
        self.register_event('endofmotd', self.rpl_endofmotd)
        self.register_event('nomotd', self.rpl_endofmotd)
        self.register_event('ping', self.rpl_ping)

        self.reactor = reactor
        self.reactor._append_server(self)

    def set_casemapping(self, casemap):
        casemap = casemap.casefold()

        self.clients.set_std(casemap)
        self.channels.set_std(casemap)

    def istring(self, in_string=''):
        new_string = IString(in_string)
        new_string.set_std(features.get('casemapping'))
        return new_string

    def idict(self, in_dict={}):
        new_dict = IDict(in_dict)
        new_dict.set_std(features.get('casemapping'))
        return new_dict

    def is_channel(self, name):
        if name[0] in self.features.get('chantypes'):
            return True
        return False

    def connection_made(self, transport):
        peername, port = transport.get_extra_info('peername')
        print('Connected to {}'.format(peername))
        self.transport = transport
        self.connected = True

        self.send('CAP LS', params=['302'])

    def send_welcome(self):
        self.send('NICK', params=[self.nick])
        self.send('USER', params=[self.user, '*', '*', self.real])

    def join_channels(self, *channels):
        if self.ready:
            for channel in channels:
                if ' ' in channel:
                    channel, key = channel.split(' ')
                else:
                    key = ''

                self.send('JOIN', params=[channel, key])
        else:
            self.autojoin_channels = channels

    def rpl_cap(self, info):
        clientname = info['params'].pop(0)
        subcmd = info['params'].pop(0).casefold()

        self.capabilities.ingest(subcmd, info['params'])

        if self.ready:
            return

        if subcmd == 'ls':
            caps_to_enable = self.capabilities.to_enable()
            self.send('CAP', params=['REQ', ' '.join(caps_to_enable)])
        elif subcmd == 'ack':
            self.send('CAP', params=['END'])
            self.send_welcome()

    def rpl_features(self, info):
        # last param is 'are supported by this server' text, so we ignore it
        self.features.ingest(*info['params'][:-1])

    def rpl_endofmotd(self, info):
        if not self.ready:
            self.ready = True

            if self.autojoin_channels:
                self.join_channels(*self.autojoin_channels)

    def rpl_ping(self, info):
        self.send('PONG', params=info['params'])

    def connection_lost(self, exc):
        if not self.connected:
            return
        self.connected = False
        if exc:
            print('Connection error: {}'.format(exc))
            return
        print('Connection closed')

    def data_received(self, data):
        # feed in new data from server
        self._new_data += data.decode('UTF-8', 'replace')
        messages = []
        message_buffer = ''

        for char in self._new_data:
            if char in ('\r', '\n'):
                if len(message_buffer):
                    messages.append(message_buffer)
                    message_buffer = ''
                continue

            message_buffer += char

        self._new_data = message_buffer

        # dispatch new messages
        for data in messages:
            m = RFC1459Message.from_data('raw')
            m.server = self
            m.data = data
            self.events.dispatch(*message_to_event('in', m))
            self.events.dispatch(*message_to_event('both', m))

            m = RFC1459Message.from_message(data)
            m.server = self
            name, event = message_to_event('in', m)
            self.events.dispatch(name, event)
            name, event = message_to_event('both', m)
            self.events.dispatch(name, event)
            self.events.dispatch('girc all in', event)
            self.events.dispatch('girc all both', event)

    def register_event(self, verb, child_fn, direction='in', priority=10):
        self.events.register('girc ' + verb + ' ' + direction, child_fn, priority=priority)

    def send(self, verb, params=None, source=None, tags=None):
        m = RFC1459Message.from_data(verb, params=params, source=source, tags=tags)
        self._send_message(m)

    def _send_message(self, message):
        m = RFC1459Message.from_data('raw')
        m.server = self
        m.data = message.to_message()
        self.events.dispatch(*message_to_event('out', m))
        self.events.dispatch(*message_to_event('both', m))

        m = message
        m.server = self
        name, event = message_to_event('out', m)
        self.events.dispatch(name, event)
        name, event = message_to_event('both', m)
        self.events.dispatch(name, event)
        self.events.dispatch('girc all out', event)
        self.events.dispatch('girc all both', event)

        self.transport.write(bytes(message.to_message() + '\r\n', 'UTF-8'))
