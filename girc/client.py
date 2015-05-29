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


class NickMask:
    def __init__(self, mask):
        self.nick = ''
        self.user = ''
        self.host = ''

        if '!' in mask:
            self.nick, rest = mask.split('!', 1)
            if '@' in rest:
                self.user, self.host = rest.split('@', 1)
        else:
            self.nick = mask

    @property
    def userhost(self):
        return '{}@{}'.format(self.user, self.host)

    @property
    def nickmask(self):
        return '{}!{}@{}'.format(self.nick, self.user, self.host)


def message_to_event(message):
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
    return 'girc ' + verb, info



class ServerConnection(asyncio.Protocol):
    def __init__(self, name=None, manifold=None, nick=None, user=None, real='*'):
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

        # generated info
        self.clients = IDict()
        self.channels = IDict()
        self.capabilities = Capabilities(wanted=['multi-prefix'])
        self.features = Features(self)

        # events
        self.register_event('cap', self.rpl_cap)
        self.register_event('features', self.rpl_features)
        self.register_event('endofmotd', self.rpl_endofmotd)

        self.manifold = manifold
        self.manifold._append_server(self)

    def set_casemapping(self, casemap):
        casemap = casemap.casefold()

        self.clients.set_std(casemap)
        self.channels.set_std(casemap)

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
            m = RFC1459Message.from_message(data)
            m.server = self
            self.events.dispatch(*message_to_event(m))
            self.events.dispatch('girc all', message_to_event(m)[1])

            m = RFC1459Message.from_data('raw in')
            m.server = self
            m.data = data
            self.events.dispatch(*message_to_event(m))

    def register_event(self, verb, child_fn, priority=10):
        self.events.register('girc ' + verb, child_fn, priority=priority)

    def send(self, verb, params=None, source=None, tags=None):
        m = RFC1459Message.from_data(verb, params=params, source=source, tags=tags)
        self._send_message(m)

    def _send_message(self, message):
        m = RFC1459Message.from_data('raw out')
        m.server = self
        m.data = message.to_message()
        self.events.dispatch(*message_to_event(m))

        self.transport.write(bytes(message.to_message() + '\r\n', 'UTF-8'))
