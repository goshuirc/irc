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
        """Shutdown with a message!"""
        for name, server in self.servers.items():
            server.quit(message)

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
