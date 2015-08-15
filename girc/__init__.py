#!/usr/bin/env python3
# Written by Daniel Oaks <daniel@danieloaks.net>
# Released under the ISC license
import asyncio
import functools

from .client import ServerConnection
from .utils import CaseInsensitiveDict

loop = asyncio.get_event_loop()


class Reactor:
    """Manages IRC connections."""

    def __init__(self):
        self.servers = CaseInsensitiveDict()
        self._connect_info = CaseInsensitiveDict()
        self._event_handlers = {}

    # start and stop
    def run_forever(self):
        """Start running the reactor. This should run forever."""
        loop.run_forever()

    def close(self):
        """Close the reactor, to be called after :meth:`girc.Reactor.run_forever` returns."""
        loop.close()

    # setting connection info
    def create_server(self, server_name, *args, **kwargs):
        """Create an IRC server connection slot.

        The server will actually be connected to when :meth:`girc.Reactor.connect_to` is called
        later.

        Args:
            server_name (str): Name of the server, to be used for functions and accessing the
                server later through the reactor.

        Other arguments to this function are to be supplied as for
        :meth:`asyncio.BaseEventLoop.create_connection`.
        """
        self._connect_info[server_name] = {
            'connection': {
                'args': args,
                'kwargs': kwargs,
            }
        }

    def set_user_info(self, server_name, nick, user='*', real='*'):
        """Sets user info for a server, before connection.

        Args:
            server_name (str): Name of the server to set user info on.
            nick (str): Nickname to use.
            user (str): Username to use.
            real (str): Realname to use.
        """
        if server_name in self.servers:
            raise Exception('Cannot set user info now, server already exists!')

        # assemble args and kwargs for connect_info later
        args = [nick]
        kwargs = {
            'user': user,
            'real': real,
        }

        # server will pickup list when they exist
        self._connect_info[server_name]['user_info'] = [args, kwargs]

    def sasl_plain(self, server_name, name, password, identity=None):
        """Authenticate to a server using SASL plain, or does so on connection.

        Args:
            server_name (str): Name of the server to set user info on.
            name (str): Name to auth with.
            password (str): Password to auth with.
            identity (str): Identity to auth with (defaults to name).
        """
        if identity is None:
            identity = name

        if server_name in self.servers:
            self.servers[server_name].sasl_plain(name, password, identity=identity)
        else:
            # server will authenticate when they exist
            self._connect_info[server_name]['sasl'] = ['plain', name, password, identity]

    def join_channels(self, server_name, *channels):
        """Joins the supplied channels, or queues them for when server connects.

        Args:
            server_name (str): Name of the server to set user info on.
            channels (strings): Channel names to join.
        """
        if server_name in self.servers:
            self.servers[server_name].join_channels(*channels)
        else:
            # server will pickup list when they exist
            self._connect_info[server_name]['autojoin_channels'] = channels

    # connecting
    def connect_to(self, server_name):
        """Connects to the given server, using details specified above.

        Args:
            server_name (str): Name of the server to connect to.
        """
        # confirm we have user info set
        if 'user_info' not in self._connect_info[server_name]:
            raise Exception('`set_user_info` must be called before connecting to server.')

        # get connection info
        connection_info = self._connect_info[server_name]['connection']

        args = connection_info['args']
        kwargs = connection_info['kwargs']

        # create connection and run
        connection = loop.create_connection(functools.partial(ServerConnection,
                                                              name=server_name,
                                                              reactor=self),
                                            *args, **kwargs)
        asyncio.Task(connection)

    def _append_server(self, server):
        self.servers[server.name] = server

        # register cached events
        for verb, infos in self._event_handlers.items():
            for info in infos:
                server.register_event(info['direction'], verb, info['handler'],
                                      priority=info['priority'])

        # setting connect info
        info = self._connect_info[server.name]

        if 'user_info' in info:
            args, kwargs = info['user_info']
            server.set_user_info(*args, **kwargs)

        if 'sasl' in info:
            args = info['sasl']
            method = args.pop(0)

            server.sasl(method, *args)

        if 'autojoin_channels' in info:
            chans = info['autojoin_channels']
            self.join_channels(server.name, *chans)

    # events
    def handler(self, direction, verb, priority=10):
        def parent_fn(func):
            @functools.wraps(func)
            def child_fn(msg):
                func(msg)
            self.register_event(direction, verb, child_fn, priority=priority)
            return child_fn
        return parent_fn

    def register_event(self, direction, verb, child_fn, priority=10):
        if verb not in self._event_handlers:
            self._event_handlers[verb] = []

        self._event_handlers[verb].append({
            'handler': child_fn,
            'direction': direction,
            'priority': priority,
        })

        for name, server in self.servers.items():
            server.register_event(direction, verb, child_fn, priority=priority)
