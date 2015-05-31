#!/usr/bin/env python3
# Written by Daniel Oaks <daniel@danieloaks.net>
# Released under the ISC license
import asyncio

from ircreactor.events import EventManager
from ircreactor.envelope import RFC1459Message

from .capabilities import Capabilities
from .features import Features
from .info import Info
from .imapping import IDict, IList, IString
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
        if message.server.is_channel(message.params[0]):
            verb = 'pubmsg'

    # this is the same as ircreactor does
    info = message.__dict__
    info['direction'] = direction
    info['verb'] = verb

    # custom message attributes
    if verb in ['privmsg', 'pubmsg']:
        info['target'] = info['params'][0]
        info['message'] = info['params'][1]

    return 'girc ' + verb, info



class ServerConnection(asyncio.Protocol):
    def __init__(self, name=None, reactor=None, nick=None, user=None, real='*'):
        self.connected = False
        self.ready = False
        self._events_in = EventManager()
        self._events_out = EventManager()
        self._new_data = ''

        # we keep a list of imappable entities for us to set the casemap on
        #   when ISUPPORT rolls 'round. we assume the server will keep the same
        #   casemap, so once we've received one we stop keeping track
        self._casemap_set = False
        self._imaps = []

        # name used for this server, eg: rizon
        self.name = name

        # client info
        self.nick = nick
        self.user = user
        self.real = real
        self.autojoin_channels = []

        # generated and state info
        self.features = Features(self)  # must be done before info
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

        self.info = Info(self)

        # events
        self.register_event('cap', 'both', self.rpl_cap)
        self.register_event('features', 'both', self.rpl_features)
        self.register_event('endofmotd', 'both', self.rpl_endofmotd)
        self.register_event('nomotd', 'both', self.rpl_endofmotd)
        self.register_event('ping', 'both', self.rpl_ping)

        self.reactor = reactor
        self.reactor._append_server(self)

    # event handling
    def register_event(self, verb, direction, child_fn, priority=10):
        event_managers = []
        if direction in ('in', 'both'):
            event_managers.append(self._events_in)
        if direction in ('out', 'both'):
            event_managers.append(self._events_out)

        for event_manager in event_managers:
            event_manager.register('girc ' + verb, child_fn, priority=priority)

    # casemapping and casemapped objects
    def set_casemapping(self, casemap):
        if not self._casemap_set:
            self._casemap_set = True

            casemap = casemap.casefold()

            for obj in self._imaps:
                obj.set_std(casemap)

    def istring(self, in_string=''):
        new_string = IString(in_string)
        new_string.set_std(self.features.get('casemapping'))
        if not self._casemap_set:
            self._imaps.append(new_string)
        return new_string

    def ilist(self, in_list=[]):
        new_list = IList(in_list)
        new_list.set_std(self.features.get('casemapping'))
        if not self._casemap_set:
            self._imaps.append(new_list)
        return new_list

    def idict(self, in_dict={}):
        new_dict = IDict(in_dict)
        new_dict.set_std(self.features.get('casemapping'))
        if not self._casemap_set:
            self._imaps.append(new_dict)
        return new_dict

    # protocol connect / disconnect
    def connection_made(self, transport):
        peername, port = transport.get_extra_info('peername')
        print('Connected to {}'.format(peername))
        self.transport = transport
        self.connected = True

        self.send('CAP LS', params=['302'])

    def connection_lost(self, exc):
        if not self.connected:
            return
        self.connected = False
        if exc:
            print('Connection error: {}'.format(exc))
            return
        print('Connection closed')

    # protocol send / receive
    def send(self, verb, params=None, source=None, tags=None):
        m = RFC1459Message.from_data(verb, params=params, source=source, tags=tags)
        self._send_message(m)

    def _send_message(self, message):
        final_message = message.to_message() + '\r\n'

        m = RFC1459Message.from_data('raw')
        m.server = self
        m.data = message.to_message()
        self._events_out.dispatch(*message_to_event('out', m))

        m = message
        m.server = self
        name, event = message_to_event('out', m)
        self._events_out.dispatch(name, event)
        self._events_out.dispatch('girc all', event)

        self.transport.write(bytes(final_message, 'UTF-8'))

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
            self._events_in.dispatch(*message_to_event('in', m))

            m = RFC1459Message.from_message(data)
            m.server = self
            name, event = message_to_event('in', m)
            self._events_in.dispatch(name, event)
            self._events_in.dispatch('girc all', event)

    # default events
    def rpl_cap(self, info):
        if info['direction'] == 'in':
            clientname = info['params'].pop(0)
        subcmd = info['params'].pop(0).casefold()

        self.capabilities.ingest(subcmd, info['params'])

        if self.ready:
            return

        if subcmd == 'ls':
            caps_to_enable = self.capabilities.to_enable
            self.send('CAP', params=['REQ', ' '.join(caps_to_enable)])
        elif subcmd == 'ack':
            self.send('CAP', params=['END'])
            self.send_welcome()

    def send_welcome(self):
        self.send('NICK', params=[self.nick])
        self.send('USER', params=[self.user, '*', '*', self.real])

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

    # convenience
    def is_channel(self, name):
        if name[0] in self.features.get('chantypes'):
            return True
        return False

    # commands
    def join_channels(self, *channels):
        # we schedule joining for later
        if not self.ready:
            self.autojoin_channels = channels
            return True

        for channel in channels:
            params = []

            if ' ' in channel:
                channel, key = channel.split(' ')
            else:
                key = None

            params.append(channel)
            if key:
                params.append(key)

            self.send('JOIN', params=[channel, key])
