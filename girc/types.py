#!/usr/bin/env python3
# Written by Daniel Oaks <daniel@danieloaks.net>
# Released under the ISC license
from .formatting import unescape
from .utils import NickMask


class ServerConnected:
    """Something that's connected to an IRC server."""
    def __init__(self, server_connection):
        self.s = server_connection


class User(ServerConnected):
    """An IRC user."""
    def __init__(self, server_connection, nickmask):
        super().__init__(server_connection)

        user = NickMask(nickmask)
        self.nick = user.nick
        self.user = user.user
        self.host = user.host

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

    # commands
    def msg(self, message, formatted=True, tags=None):
        self.s.msg(self.nick, message, formatted=formatted, tags=tags)

    def me(self, message, formatted=True):
        if formatted:
            message = unescape(message)

        self.ctcp('ACTION ' + message)

    def ctcp(self, message):
        self.s.ctcp(self.nick, message)

    def ctcp_reply(self, message):
        self.s.ctcp_reply(self.nick, message)
    

class Channel(ServerConnected):
    """An IRC channel."""
    def __init__(self, server_connection, name):
        super().__init__(server_connection)

        self.name = name
        self.joined = False  # whether we are joined to this channel

        self.users = {}

    @property
    def users(self):
        userlist = {}

        for nick in self._users:
            userlist[nick] = self.s.users[nick]

        return userlist

    @users.setter
    def users(self, userlist):
        self._users = self.s.idict()

    # commands
    def msg(self, message, formatted=True, tags=None):
        self.s.msg(self.name, message, formatted=formatted, tags=tags)

    def me(self, message, formatted=True):
        if formatted:
            message = unescape(message)

        self.ctcp('ACTION ' + message)

    def ctcp(self, message):
        self.s.ctcp(self.name, message)

    def ctcp_reply(self, message):
        self.s.ctcp_reply(self.name, message)

    def get_modes(self):
        self.s.mode(self.name)


class Server(ServerConnected):
    def __init__(self, server_connection,name):
        super().__init__(server_connection)

        self.name = name
