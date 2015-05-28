#!/usr/bin/env python3
# Written by Daniel Oaks <daniel@danieloaks.net>
# Released under the ISC license
import asyncio
import functools

from .client import ServerConnection

loop = asyncio.get_event_loop()


class Reactor:
    """Manages IRC connections."""
    def __init__(self):
        self.servers = {}
        self._event_handlers = {}

    def connect_to_server(self, name, *args, nick=None, user='', **kwargs):
        if nick is None:
            raise Exception('nick must be passed to connect_to_server')

        connection = loop.create_connection(functools.partial(ServerConnection, name=name, manifold=self, nick=nick, user=user), *args, **kwargs)
        t = asyncio.Task(connection)

    def _append_server(self, server):
        self.servers[server.name] = server

        for verb, infos in self._event_handlers.items():
            for info in infos:
                server.register_event(verb, info['handler'], priority=info['priority'])

    def handler(self, verb, priority=10):
        def parent_fn(func):
            @functools.wraps(func)
            def child_fn(msg):
                func(msg)
            self.register_event(verb, child_fn, priority=priority)
            return child_fn
        return parent_fn

    def register_event(self, verb, child_fn, priority=10):
        if verb not in self._event_handlers:
            self._event_handlers[verb] = []

        self._event_handlers[verb].append({
            'handler': child_fn,
            'priority': priority,
        })

        for name, server in self.servers.items():
            server.register_event(verb, child_fn, priority=priority)

    def start(self):
        loop.run_forever()

    def close(self):
        loop.close()
