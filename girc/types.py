#!/usr/bin/env python3
# Written by Daniel Oaks <daniel@danieloaks.net>
# Released under the ISC license
from .formatting import unescape
from .utils import NickMask


class TargetableUserChan:
    """Provides events that can be sent to a user or a channel."""

    def msg(self, message, formatted=True, tags=None):
        self.s.msg(self._target, message, formatted=formatted, tags=tags)

    def me(self, message, formatted=True):
        if formatted:
            message = unescape(message)

        self.ctcp('ACTION', message)

    def ctcp(self, ctcp_verb, argument=None):
        self.s.ctcp(self._target, ctcp_verb, argument=argument)

    def ctcp_reply(self, ctcp_verb, argument=None):
        self.s.ctcp_reply(self._target, ctcp_verb, argument=argument)

    def get_topic(self):
        self.s.topic(self._target)

    def get_modes(self):
        self.s.mode(self._target)


class ServerConnected:
    """Something that's connected to an IRC server."""

    def __init__(self, server_connection):
        self.s = server_connection

        self.is_user = False
        self.is_channel = False
        self.is_server = False


class User(ServerConnected, TargetableUserChan):
    """An IRC user."""

    def __init__(self, server_connection, nickmask):
        super().__init__(server_connection)

        self.is_user = True

        user = NickMask(nickmask)
        self.nick = self.s.istring(user.nick)
        self.user = self.s.istring(user.user)
        self.host = self.s.istring(user.host)

        self._target = self.nick

        self.channel_names = self.s.ilist()

        # XXX - this may not work if we get any notices/etc before RPL_WELCOME
        self.is_me = server_connection.nick is None or (self.nick == server_connection.nick)

    # properties
    @property
    def name(self):
        return self.nick

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


class Channel(ServerConnected, TargetableUserChan):
    """An IRC channel."""

    def __init__(self, server_connection, name):
        super().__init__(server_connection)

        self.is_channel = True

        self.name = self.s.istring(name)
        self.joined = False  # whether we are joined to this channel

        self._target = self.name

        self._user_nicks = self.s.ilist()
        self.prefixes = self.s.idict()

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

    def has_privs(self, user, lowest_mode='o'):
        """Return True if user has the given mode or higher."""
        if isinstance(user, User):
            user = user.nick

        user_prefixes = self.prefixes.get(user, None)

        if not user_prefixes:
            return False

        mode_dict = self.s.features.available['prefix']

        caught = False

        for mode, prefix in mode_dict.items():
            if mode in lowest_mode and not caught:
                caught = True
            elif mode not in lowest_mode and not caught:
                continue

            if prefix in user_prefixes:
                return True

        return False

    def add_user(self, nick, prefixes=None):
        """Add a user to our internal list of nicks."""
        if nick not in self._user_nicks:
            self._user_nicks.append(nick)

        self.prefixes[nick] = prefixes


class Server(ServerConnected):
    """An IRC server."""

    def __init__(self, server_connection, name):
        super().__init__(server_connection)

        self.is_server = True

        self.name = self.s.istring(name)
