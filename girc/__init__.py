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

    def close(self):
        """Close the reactor, to be called after :meth:`girc.Reactor.run_forever` returns."""
        loop.close()

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

        return server

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
