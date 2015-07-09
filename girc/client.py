#!/usr/bin/env python3
# Written by Daniel Oaks <daniel@danieloaks.net>
# Released under the ISC license
import asyncio

from ircreactor.events import EventManager
from ircreactor.envelope import RFC1459Message

from .capabilities import Capabilities
from .features import Features
from .formatting import unescape
from .info import Info
from .imapping import IDict, IList, IString
from .events import message_to_event
from .utils import validate_hostname

loop = asyncio.get_event_loop()


class ServerConnection(asyncio.Protocol):
    """Manages a connection to a single server."""

    def __init__(self, name=None, reactor=None):
        self.connected = False
        self.ready = False
        self._events_in = EventManager()
        self._events_out = EventManager()
        self._girc_events = EventManager()
        self._new_data = ''

        # we keep a list of imappable entities for us to set the casemap on
        #   when ISUPPORT rolls 'round. we assume the server will keep the same
        #   casemap, so once we've received one we stop keeping track
        self._casemap_set = False
        self._imaps = []

        # name used for this server, eg: rizon
        self.name = name

        # client info
        self.nick = None
        self.user = None
        self.real = None
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
        self.register_event('both', 'cap', self.rpl_cap)
        self.register_event('both', 'features', self.rpl_features)
        self.register_event('both', 'endofmotd', self.rpl_endofmotd)
        self.register_event('both', 'nomotd', self.rpl_endofmotd)
        self.register_event('both', 'ping', self.rpl_ping)

        self.reactor = reactor
        self.reactor._append_server(self)

    def set_user_info(self, nick, user='*', real='*'):
        self.nick = nick
        self.user = user
        self.real = real

    # event handling
    def register_event(self, direction, verb, child_fn, priority=10):
        event_managers = []
        if direction in ('in', 'both'):
            event_managers.append(self._events_in)
        if direction in ('out', 'both'):
            event_managers.append(self._events_out)
        if direction == 'girc':
            event_managers.append(self._girc_events)

        for event_manager in event_managers:
            event_manager.register(verb, child_fn, priority=priority)

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
        if not self.nick:
            raise Exception('Nick not found. User info must be set with set_user_info()'
                            'before connecting')
            self.exit()
            return

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
        for name, event in message_to_event('out', m):
            self._events_out.dispatch(name, event)

        m = message
        m.server = self
        for name, event in message_to_event('out', m):
            self.info.handle_event_out(event)
            self._events_out.dispatch(name, event)
            self._events_out.dispatch('all', event)

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
            for name, event in message_to_event('in', m):
                self._events_in.dispatch(name, event)

            m = RFC1459Message.from_message(data)
            m.server = self
            for name, event in message_to_event('in', m):
                self.info.handle_event_in(event)
                self._events_in.dispatch(name, event)
                self._events_in.dispatch('all', event)

    # commands
    def msg(self, target, message, formatted=True, tags=None):
        """Message the given target."""
        if formatted:
            message = unescape(message)

        self.send('PRIVMSG', params=[target, message], source=self.nick, tags=tags)

    def notice(self, target, message, formatted=True, tags=None):
        """Send a notice to the given target."""
        if formatted:
            message = unescape(message)

        self.send('NOTICE', params=[target, message], source=self.nick, tags=tags)

    def ctcp(self, target, ctcp_verb, argument=None):
        """Send a CTCP to the given target."""
        # we don't support complex ctcp encapsulation because we're somewhat sane
        atoms = [ctcp_verb]
        if argument is not None:
            atoms.append(argument)
        X_DELIM = '\x01'
        self.msg(target, X_DELIM + ' '.join(atoms) + X_DELIM, formatted=False)

    def ctcp_reply(self, target, ctcp_verb, argument=None):
        """Send a CTCP reply to the given target."""
        # we don't support complex ctcp encapsulation because we're somewhat sane
        atoms = [ctcp_verb]
        if argument is not None:
            atoms.append(argument)
        X_DELIM = '\x01'
        self.notice(target, X_DELIM + ' '.join(atoms) + X_DELIM, formatted=False)

    def join_channel(self, channel, key=None):
        """Join the given channel."""
        params = [channel]
        if key:
            params.append(key)
        self.send('JOIN', params=params)

    def mode(self, target, mode_string=None, tags=None):
        """Modes the given target."""
        params = [target]
        if mode_string:
            params += mode_string
        self.send('MODE', params=params, source=self.nick, tags=tags)

    # default events
    def rpl_cap(self, event):
        if event['direction'] == 'in':
            clientname = event['params'].pop(0)
        subcmd = event['params'].pop(0).casefold()

        self.capabilities.ingest(subcmd, event['params'])

        if self.ready:
            return

        if subcmd == 'ls':
            caps_to_enable = self.capabilities.to_enable
            self.send('CAP', params=['REQ', ' '.join(caps_to_enable)])
        elif subcmd == 'ack':
            self.send('CAP', params=['END'])
            self.send_welcome()
        elif subcmd == 'nak':
            self.send('CAP', params=['END'])
            self.send_welcome()

    def send_welcome(self):
        self.send('NICK', params=[self.nick])
        self.send('USER', params=[self.user, '*', '*', self.real])

    def rpl_features(self, event):
        # last param is 'are supported by this server' text, so we ignore it
        self.features.ingest(*event['params'][:-1])

    def rpl_endofmotd(self, event):
        if not self.ready:
            self.ready = True

            if self.autojoin_channels:
                self.join_channels(*self.autojoin_channels)

    def rpl_ping(self, event):
        self.send('PONG', params=event['params'])

    # convenience
    def is_server(self, name):
        return validate_hostname(name)

    def is_channel(self, name):
        if name[0] in self.features.get('chantypes'):
            return True
        return False

    def is_nick(self, name):
        # XXX - lazy for now, to check ISUPPORT etc
        return not self.is_channel(name) and not self.is_server(name)

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

            self.join_channel(channel, key=key)
