#!/usr/bin/env python3
# Written by Daniel Oaks <daniel@danieloaks.net>
# Released under the ISC license
from .formatting import unescape
from .utils import NickMask


class SourceableUserChan:
    """Provides events that can originate from a user or a channel."""
    def msg(self, message, formatted=True, tags=None):
        self.s.msg(self._source, message, formatted=formatted, tags=tags)

    def me(self, message, formatted=True):
        if formatted:
            message = unescape(message)

        self.ctcp('ACTION', message)

    def ctcp(self, ctcp_verb, argument=None):
        self.s.ctcp(self._source, ctcp_verb, argument=argument)

    def ctcp_reply(self, ctcp_verb, argument=None):
        self.s.ctcp_reply(self._source, ctcp_verb, argument=argument)

    def get_modes(self):
        self.s.mode(self._source)


class ServerConnected:
    """Something that's connected to an IRC server."""
    def __init__(self, server_connection):
        self.s = server_connection


class User(ServerConnected, SourceableUserChan):
    """An IRC user."""
    def __init__(self, server_connection, nickmask):
        super().__init__(server_connection)

        user = NickMask(nickmask)
        self.nick = user.nick
        self.user = user.user
        self.host = user.host

        self._source = self.nick

        self.channel_names = self.s.ilist()

    # properties
    @property
    def channels(self):
        chanlist = []

        for channel in self.channel_names:
            chanlist.append(self.s.info.channels[channel])

        return chanlist

    @channels.setter
    def channels(self, chanlist):
        self.channel_names = self.s.ilist(chanlist)

    @property
    def userhost(self):
        return '{}@{}'.format(self.user, self.host)

    @property
    def nickmask(self):
        return '{}!{}@{}'.format(self.nick, self.user, self.host)
    

class Channel(ServerConnected, SourceableUserChan):
    """An IRC channel."""
    def __init__(self, server_connection, name):
        super().__init__(server_connection)

        self.name = name
        self.joined = False  # whether we are joined to this channel

        self._source = self.name

        self._user_nicks = []
        self.prefixes = {}

        self._init_modes()

    def _init_modes(self):
        self.modes = {}

        a, b, c, d = self.s.features.available['chanmodes']

        for char in a:
            self.modes[char] = []

    @property
    def users(self):
        userlist = {}

        for nick in self._user_nicks:
            userlist[nick] = self.s.info.users[nick]

        return userlist


class Server(ServerConnected):
    def __init__(self, server_connection,name):
        super().__init__(server_connection)

        self.name = name
