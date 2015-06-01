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
    def start(self):
        loop.run_forever()

    def close(self):
        loop.close()

    # servers
    def connect_to_server(self, server_name, *args, **kwargs):
        self._connect_info[server_name] = {}

        connection = loop.create_connection(functools.partial(ServerConnection, name=server_name, reactor=self), *args, **kwargs)
        t = asyncio.Task(connection)

    def _append_server(self, server):
        self.servers[server.name] = server

        # register cached events
        for verb, infos in self._event_handlers.items():
            for info in infos:
                server.register_event(verb, info['direction'], info['handler'], priority=info['priority'])

        # setting connect info
        info = self._connect_info[server.name]

        if 'user_info' in info:
            args, kwargs = info['user_info']
            self.set_user_info(server.name, *args, **kwargs)

        if 'autojoin_channels' in info:
            chans = info['autojoin_channels']
            self.join_channels(server.name, *chans)

    # setting connection info
    def set_user_info(self, server_name, *args, **kwargs):
        if server_name in self.servers:
            self.servers[server_name].set_user_info(*args, **kwargs)
        else:
            # server will pickup list when they exist
            self._connect_info[server_name]['user_info'] = [args, kwargs]

    def join_channels(self, server_name, *chans):
        if server_name in self.servers:
            self.servers[server_name].join_channels(*chans)
        else:
            # server will pickup list when they exist
            self._connect_info[server_name]['autojoin_channels'] = chans

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
