#!/usr/bin/env python3
# Written by Daniel Oaks <daniel@danieloaks.net>
# Released under the ISC license
import asyncio
import base64
import re

from .ircreactor.events import EventManager
from .ircreactor.envelope import RFC1459Message

from .capabilities import Capabilities
from .features import Features
from .formatting import unescape
from .info import Info
from .imapping import IDict, IList, IString
from .events import message_to_event
from .utils import validate_hostname, CaseInsensitiveDict

loop = asyncio.get_event_loop()


class ServerConnection(asyncio.Protocol):
    """Manages a connection to a single server."""

    def __init__(self, name=None, reactor=None):
        self.connected = False
        self.registered = False
        self.ready = False
        self.is_me = True
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

        # generated and state info
        self.features = Features(self)  # must be done before info
        self.capabilities = Capabilities(wanted=[
            'account-notify',
            'account-tag',
            'away-notify',
            'cap-notify',
            'chghost',
            'echo-message',
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
        self.connect_info = CaseInsensitiveDict(channels=[])

        # events
        self.register_event('in', 'welcome', self.rpl_welcome, priority=-9999)
        self.register_event('both', 'cap', self.rpl_cap)
        self.register_event('both', 'features', self.rpl_features)
        self.register_event('both', 'endofmotd', self.rpl_endofmotd)
        self.register_event('both', 'nomotd', self.rpl_endofmotd)
        self.register_event('both', 'ping', self.rpl_ping)

        # sasl stuff
        self.allow_sasl_fail = False
        self._sasl_info = {}
        self.register_event('in', 'authenticate', self.rpl_authenticate)
        self.register_event('in', 'saslsuccess', self.rpl_saslsuccess)
        self.register_event('in', 'saslfail', self.rpl_saslfail)

        self.reactor = reactor

    @property
    def channels(self):
        return self.info.channels

    @property
    def users(self):
        return self.info.users

    # event handling
    def register_event(self, direction, verb, child_fn, priority=10):
        """Register an event with all servers.

        Args:
            direction (str): `in`, `out`, `both`, or `girc`.
            verb (str): Event name, `all`, or `raw`.
            child_fn (function): Handler function.
            priority (int): Handler priority (lower priority executes first).

        Note: `all` will not match `raw` events. If you wish to receive both
        `raw` and all other events, you need to register these separately.
        """
        event_managers = []
        if direction in ('in', 'both'):
            event_managers.append(self._events_in)
        if direction in ('out', 'both'):
            event_managers.append(self._events_out)
        if direction == 'girc':
            event_managers.append(self._girc_events)

        for event_manager in event_managers:
            event_manager.register(verb, child_fn, priority=priority)

    # connect info
    def set_connect_password(self, password):
        """Sets connect password for this server, to be used before connection.

        Args:
            password (str): Password to connect with.
        """
        if self.connected:
            raise Exception("Can't set password now, we're already connected!")

        # server will pickup list when they exist
        self.connect_info['connect_password'] = password

    def set_user_info(self, nick, user='*', real='*'):
        """Sets user info for this server, to be used before connection.

        Args:
            nick (str): Nickname to use.
            user (str): Username to use.
            real (str): Realname to use.
        """
        if self.connected:
            raise Exception("Can't set user info now, we're already connected!")

        # server will pickup list when they exist
        if not self.connected:
            self.nick = nick

        self.connect_info['user'] = {
            'nick': nick,
            'user': user,
            'real': real,
        }

    # casemapping and casemapped objects
    def set_casemapping(self, casemap):
        if not self._casemap_set:
            self._casemap_set = True

            casemap = casemap.casefold()

            for obj in self._imaps:
                obj.set_std(casemap)

    def istring(self, in_string=''):
        """Return a string that uses this server's IRC casemapping.

        This string's equality with other strings, ``lower()``, and ``upper()`` takes this
        server's casemapping into account. This should be used for things such as nicks and
        channel names, where comparing strings using the correct casemapping can be very
        important.
        """
        new_string = IString(in_string)
        new_string.set_std(self.features.get('casemapping'))
        if not self._casemap_set:
            self._imaps.append(new_string)
        return new_string

    def ilist(self, in_list=[]):
        """Return a list that uses this server's IRC casemapping.

        All strings in this list are lowercased using the server's casemapping before inserting
        them into the list, and the ``in`` operator takes casemapping into account.
        """
        new_list = IList(in_list)
        new_list.set_std(self.features.get('casemapping'))
        if not self._casemap_set:
            self._imaps.append(new_list)
        return new_list

    def idict(self, in_dict={}):
        """Return a dict that uses this server's IRC casemapping.

        All keys in this dictionary are stored and compared using this server's casemapping.
        """
        new_dict = IDict(in_dict)
        new_dict.set_std(self.features.get('casemapping'))
        if not self._casemap_set:
            self._imaps.append(new_dict)
        return new_dict

    # protocol connect / disconnect
    def connect(self, *args, auto_reconnect=False, **kwargs):
        """Connects to the given server.

        Args:
            auto_reconnect (bool): Automatically reconnect on disconnection.

        Other arguments to this function are as usually supplied to
        :meth:`asyncio.BaseEventLoop.create_connection`.
        """
        connection_info = {
            'auto_reconnect': auto_reconnect,
            'args': args,
            'kwargs': kwargs,
        }
        self.connect_info['connection'] = connection_info

        # confirm we have user info set
        if 'user' not in self.connect_info:
            raise Exception('`set_user_info` must be called before connecting to server.')

        # create connection and run
        connection = loop.create_connection(lambda: self,
                                            *args, **kwargs)
        asyncio.Task(connection)

    def connection_made(self, transport):
        if 'user' not in self.connect_info:
            raise Exception('Nick not found. User info must be set with set_user_info()'
                            'before connecting')
            self.exit()
            return

        # we do this because IPv6 returns a 4-length tuple
        extra_info = transport.get_extra_info('peername')
        peername, port = extra_info[:2]

        self.transport = transport
        self.connected = True

        self.send('CAP', params=['LS', '302'])

    def quit(self, message=None):
        """Quit from the server."""
        if message is None:
            message = 'Quit'

        if self.connected:
            self.send('QUIT', params=[message])

    def connection_lost(self, exc):
        if not self.connected:
            return
        self.connected = False
        if exc:
            print('Connection error: {}'.format(exc))
            return
        print('Connection closed')
        self.reactor._destroy_server(self.name)

    # protocol send / receive
    def send(self, verb, params=None, source=None, tags=None):
        """Send a generic IRC message to the server.

        A message is created using the various parts of the message, then gets
        assembled and sent to the server.

        Args:
            verb (str): Verb, such as PRIVMSG.
            params (list of str): Message parameters, defaults to no params.
            source (str): Source of the message, defaults to no source.
            tags (dict): `Tags <http://ircv3.net/specs/core/message-tags-3.2.html>`_
                to send with the message.
        """
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
    def action(self, target, message, formatted=True, tags=None):
        """Send an action to the given target."""
        if formatted:
            message = unescape(message)

        self.ctcp(target, 'ACTION', message)

    def msg(self, target, message, formatted=True, tags=None):
        """Send a privmsg to the given target."""
        if formatted:
            message = unescape(message)

        self.send('PRIVMSG', params=[target, message], source=self.nick, tags=tags)

    def notice(self, target, message, formatted=True, tags=None):
        """Send a notice to the given target."""
        if formatted:
            message = unescape(message)

        self.send('NOTICE', params=[target, message], source=self.nick, tags=tags)

    def ctcp(self, target, ctcp_verb, argument=None):
        """Send a CTCP request to the given target."""
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

    def join_channel(self, channel, key=None, tags=None):
        """Join the given channel."""
        params = [channel]
        if key:
            params.append(key)
        self.send('JOIN', params=params, tags=tags)

    def part_channel(self, channel, reason=None, tags=None):
        """Part the given channel."""
        params = [channel]
        if reason:
            params.append(reason)
        self.send('PART', params=params, tags=tags)

    def mode(self, target, mode_string=None, tags=None):
        """Sends new modes to or requests existing modes from the given target."""
        params = [target]
        if mode_string:
            params += mode_string
        self.send('MODE', params=params, source=self.nick, tags=tags)

    def topic(self, channel, new_topic=None, tags=None):
        """Requests or sets the topic for the given channel."""
        params = [channel]
        if new_topic:
            params += new_topic
        self.send('TOPIC', params=params, source=self.nick, tags=tags)

    # default events
    def rpl_welcome(self, event):
        self.nick = event['nick']

    def rpl_cap(self, event):
        params = list(event['params'])
        if event['direction'] == 'in':
            params.pop(0)
        subcmd = params.pop(0).casefold()

        if event['direction'] == 'in':
            self.capabilities.ingest(subcmd, params)
        else:
            return

        # registration
        if subcmd in ['ack', 'nak'] and not self.registered:
            self.start()

        # enable caps we want
        if subcmd == 'ls' and params[0] != '*':  # * specifies continuation list
            caps_to_enable = self.capabilities.to_enable
            if caps_to_enable:
                self.send('CAP', params=['REQ', ' '.join(caps_to_enable)])
            else:
                self.start()

    def start(self):
        """Start our welcome!"""
        if ('sasl' in self.capabilities.enabled and self._sasl_info and
                (not self.capabilities.available['sasl']['value'] or
                    (self.capabilities.available['sasl']['value'] and
                        self._sasl_info['method'] in
                        self.capabilities.available['sasl']['value']))):
            self.start_sasl()
        else:
            self.send('CAP', params=['END'])
            self.send_welcome()

    def send_welcome(self):
        info = self.connect_info['user']
        password = self.connect_info.get('connect_password')
        if password:
            self.send('PASS', params=[password])
        self.send('NICK', params=[info['nick']])
        self.send('USER', params=[info['user'], '*', '*', info['real']])
        self.registered = True

    def rpl_authenticate(self, event):
        if self._sasl_info['method'].casefold() == 'plain':
            username = self._sasl_info['name']
            password = self._sasl_info['password']
            identity = self._sasl_info['identity']

            reply = base64.b64encode(bytes(identity, 'utf8') + b'\x00' +
                                     bytes(username, 'utf8') + b'\x00' +
                                     bytes(password, 'utf8'))
            reply = str(reply, 'utf8')
            replies = []
            while len(reply):
                replies.append(reply[:400])
                reply = reply[400:]

        for reply in replies:
            self.send('AUTHENTICATE', [reply])
        if len(replies[-1]) == 400:
            self.send('AUTHENTICATE', ['+'])

    def rpl_saslsuccess(self, event):
        if not self.registered:
            # finish registration
            self.send('CAP', params=['END'])
            self.send_welcome()

    def rpl_saslfail(self, event):
        if not self.registered:
            if self.allow_sasl_fail:
                self.rpl_saslsuccess(event)
            else:
                self.quit('SASL authentication failed')

    def rpl_features(self, event):
        # last param is 'are supported by this server' text, so we ignore it
        self.features.ingest(*event['params'][:-1])

    def rpl_endofmotd(self, event):
        if not self.ready:
            self.ready = True

            # identify if we have to
            nickserv_info = self.connect_info.get('nickserv', {})
            if nickserv_info:
                self.nickserv_identify(nickserv_info['password'],
                                       use_nick=nickserv_info['use_nick'])

            # join channels
            seconds = self.connect_info.get('channel_wait_seconds', 0)
            channels = self.connect_info.get('channels', [])

            if seconds:
                @asyncio.coroutine
                def channel_joiner(seconds_to_wait, channels):
                    yield from asyncio.sleep(seconds_to_wait)
                    self.join_channels(*channels)
                try:
                    asyncio.ensure_future(channel_joiner(seconds, channels))
                except AttributeError:
                    asyncio.async(channel_joiner(seconds, channels))
            else:
                self.join_channels(*channels)

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
        # we cannot assume how long nicknames can be for other users
        #   based on NICKLEN, spec forbids it
        nickmatch = r'^[a-z_\-\[\]\\^{}|`][a-z0-9_\-\[\]\\^{}|`]+$'
        return name in self.info.users or re.match(nickmatch, name)

    # commands
    def join_channels(self, *channels, wait_seconds=0):
        # we schedule joining for later
        if not self.ready:
            for channel in channels:
                self.connect_info['channels'].append(channel)
            if wait_seconds:
                self.connect_info['channel_wait_seconds'] = wait_seconds
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

    def nickserv_identify(self, password, use_nick=None):
        """Identify to NickServ (legacy)."""
        if self.ready:
            if use_nick:
                self.msg(use_nick, 'IDENTIFY {}'.format(password))
            else:
                self.send('NICKSERV', params=['IDENTIFY', password])
        else:
            self.connect_info['nickserv'] = {
                'password': password,
                'use_nick': use_nick,
            }

    def start_sasl(self):
        # only start if we have enabled SASL
        if 'sasl' not in self.capabilities.enabled:
            return False

        method = self._sasl_info['method']

        self.send('AUTHENTICATE', params=[method.upper()])
        return True

    def sasl(self, method, *args):
        self._sasl_info = {
            'method': method,
        }
        args = list(args)
        if method.casefold() == 'plain':
            name = args.pop(0)
            password = args.pop(0)
            if len(args):
                identity = args.pop(0)
            else:
                identity = name

            self._sasl_info['name'] = name
            self._sasl_info['password'] = password
            self._sasl_info['identity'] = identity

        if not self.ready:
            return True

        return self.start_sasl(method)

    def sasl_plain(self, name, password, identity=None):
        """Authenticate to a server using SASL plain, or does so on connection.

        Args:
            name (str): Name to auth with.
            password (str): Password to auth with.
            identity (str): Identity to auth with (defaults to name).
        """
        if identity is None:
            identity = name

        self.sasl('plain', name, password, identity)
