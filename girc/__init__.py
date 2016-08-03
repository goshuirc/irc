#!/usr/bin/env python3
# Written by Daniel Oaks <daniel@danieloaks.net>
# Released under the ISC license
"""girc is a modern IRC client library based on the asyncio framework.

This library is in alpha and is not yet stable. This means that it
may change at any time and it is not recommended to use this unless
you are willing to tolerate and report some bugs and inconsistent
behaviour.

This library is in development, so these features may be in various
levels of completion right now:

    * Incoming and outgoing events.
    * Info and state tracking.
    * Server-based IRC mapping for dicts, lists, and strings.
    * IRCv3 capability support.
    * Escaping and unescaping IRC formatting for ease-of-use (bold,
      colours, etc).

For more information please see these links:

    * Github Repo: https://github.com/DanielOaks/girc
    * Hosted Documentation: http://girc.readthedocs.org/en/latest/

Written by Daniel Oaks <daniel@danieloaks.net>, and released under
the ISC license.
"""
import asyncio
import functools

from .client import ServerConnection
from .utils import CaseInsensitiveDict

__version__ = '0.3.1'

loop = asyncio.get_event_loop()


class Reactor:
    """Manages IRC connections."""

    def __init__(self, auto_close=True):
        self.servers = CaseInsensitiveDict()
        self.auto_close = auto_close
        self._event_handlers = {}

    # start and stop
    def run_forever(self):
        """Start running the reactor. This should run forever."""
        loop.run_forever()

    def shutdown(self, message=None):
        """Disconnect all servers with a message.

        Args:
            message (str): Quit message to use on each connection.
        """
        for name, server in self.servers.items():
            server.quit(message)

    # setting connection info
    def create_server(self, server_name, *args, **kwargs):
        """Create an IRC server connection slot.

        The server will actually be connected to when
        :meth:`girc.client.ServerConnection.connect` is called later.

        Args:
            server_name (str): Name of the server, to be used for functions and accessing the
                server later through the reactor.

        Returns:
            server (girc.client.ServerConnection): A not-yet-connected server.
        """
        server = ServerConnection(name=server_name, reactor=self)

        if args or kwargs:
            server.set_connect_info(*args, **kwargs)

        # register cached events
        for verb, infos in self._event_handlers.items():
            for info in infos:
                server.register_event(info['direction'], verb, info['handler'],
                                      priority=info['priority'])

        self.servers[server_name] = server

        return server

    def _destroy_server(self, server_name):
        """Destroys the given server, called internally."""
        try:
            del self.servers[server_name]
        except KeyError:
            pass

        if self.auto_close and not self.servers:
            loop.stop()

    # events
    def handler(self, direction, verb, priority=10):
        """Register this function as an event handler.

        Args:
            direction (str): ``in``, ``out``, ``both``, ``raw``.
            verb (str): Event name.
            priority (int): Handler priority (lower priority executes first).

        Example:
            These handlers print out a pretty raw log::

                reactor = girc.Reactor()

                @reactor.handler('in', 'raw', priority=1)
                def handle_raw_in(event):
                    print(event['server'].name, ' ->', escape(event['data']))


                @reactor.handler('out', 'raw', priority=1)
                def handle_raw_out(event):
                    print(event['server'].name, '<- ', escape(event['data']))
        """
        def parent_fn(func):
            @functools.wraps(func)
            def child_fn(msg):
                func(msg)
            self.register_event(direction, verb, child_fn, priority=priority)
            return child_fn
        return parent_fn

    def register_event(self, direction, verb, child_fn, priority=10):
        """Register an event with all servers.

        Args:
            direction (str): `in`, `out`, `both`, `raw`.
            verb (str): Event name.
            child_fn (function): Handler function.
            priority (int): Handler priority (lower priority executes first).
        """
        if verb not in self._event_handlers:
            self._event_handlers[verb] = []

        self._event_handlers[verb].append({
            'handler': child_fn,
            'direction': direction,
            'priority': priority,
        })

        for name, server in self.servers.items():
            server.register_event(direction, verb, child_fn, priority=priority)
