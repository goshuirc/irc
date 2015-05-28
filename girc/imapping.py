#!/usr/bin/env python3
# Written by Daniel Oaks <daniel@danieloaks.net>
# Released under the ISC license
import collections


class IDict(collections.MutableMapping):
    """Case-insensitive IRC dict, based on IRC casemapping standards."""
    def __init__(self, std='ascii', *args, **kwargs):
        self.store = dict()
        self.set_std(std)
        self.update(dict(*args, **kwargs))  # use the free update to set keys

    def set_std(self, std):
        """Set the standard we'll be using (isupport CASEMAPPING)."""
        # translation based on std
        self._lower_chars = None
        self._upper_chars = None

        self._lower_trans = None
        self._upper_trans = None

        self._std = std.lower()

        if self._std == 'ascii':
            pass
        elif self._std == 'rfc1459':
            self._lower_chars = ''.join(chr(i) for i in range(91, 95))
            self._upper_chars = ''.join(chr(i) for i in range(123, 127))

        elif self._std == 'rfc1459-strict':
            self._lower_chars = ''.join(chr(i) for i in range(91, 94))
            self._upper_chars = ''.join(chr(i) for i in range(123, 126))

        if self._lower_chars:
            self._lower_trans = str.maketrans(self._lower_chars, self._upper_chars)
        if self._upper_chars:
            self._upper_trans = str.maketrans(self._upper_chars, self._lower_chars)

    def __json__(self):
        return self.store

    def __getitem__(self, key):
        return self.store[self.__keytransform__(key)]

    def __setitem__(self, key, value):
        self.store[self.__keytransform__(key)] = value

    def __delitem__(self, key):
        del self.store[self.__keytransform__(key)]

    def __iter__(self):
        return iter(self.store)

    def __len__(self):
        return len(self.store)

    def __keytransform__(self, key):
        if self._lower_trans is not None:
            key = key.translate(self._lower_trans)
        return key.lower()

    def copy(self):
        """Return a copy of ourself."""
        new_dict = IDict(std=self._std)
        new_dict.update(self.store)
        return new_dict


class IString(str):
    """Case-insensitive IRC string (for channel/usernames), based on IRC casemapping standards."""
    # setting info
    def set_std(self, std):
        """Set the standard we'll be using (isupport CASEMAPPING)."""
        # translation based on std
        self._lower_chars = None
        self._upper_chars = None

        self._lower_trans = None
        self._upper_trans = None

        self._std = std.lower()

        if self._std == 'ascii':
            pass
        elif self._std == 'rfc1459':
            self._lower_chars = ''.join(chr(i) for i in range(91, 95))
            self._upper_chars = ''.join(chr(i) for i in range(123, 127))

        elif self._std == 'rfc1459-strict':
            self._lower_chars = ''.join(chr(i) for i in range(91, 94))
            self._upper_chars = ''.join(chr(i) for i in range(123, 126))

        if self._lower_chars:
            self._lower_trans = str.maketrans(self._lower_chars, self._upper_chars)
        if self._upper_chars:
            self._upper_trans = str.maketrans(self._upper_chars, self._lower_chars)

    # upperlower
    def lower(self):
        new_string = IString(self._irc_lower(self))
        new_string.set_std(self._std)
        return new_string

    def upper(self):
        new_string = IString(self._irc_upper(self))
        new_string.set_std(self._std)
        return new_string

    def _irc_lower(self, in_string):
        """Convert us to our lower-case equivalent, given our std."""
        conv_string = in_string
        if self._lower_trans is not None:
            conv_string = conv_string.translate(self._lower_trans)
        return str.lower(conv_string)

    def _irc_upper(self, in_string):
        """Convert us to our upper-case equivalent, given our std."""
        conv_string = in_string
        if self._upper_trans is not None:
            conv_string = in_string.translate(self._upper_trans)
        return str.upper(conv_string)

    # magic
    def __contains__(self, item):
        me = str(self.lower())
        item = str(self._irc_lower(item))
        return item in me

    def __eq__(self, other):
        # use str's built-in equality operator
        me = str(self.lower())
        other = str(self._irc_lower(other))
        return me == other

    def __lt__(self, other):
        for i in range(0, min(len(self), len(other))):
            if ord(self[i]) < ord(self[i]):
                return True
        return len(self) < len(other)

    def __le__(self, other):
        return self.__lt__(other) or len(self) < len(other)

    def __ne__(self, other):
        return not self.__eq__(other)

    def __gt__(self, other):
        return not self.__le__(other)

    def __ge__(self, other):
        return not self.__lt__(other)

    def __hash__(self):
        return hash(str(self._irc_lower(self)))

    # str methods
    # this is so we can just do normal .title() / .split() / .etc calls as though IString were a str class
    def __getattribute__(self, name):
        f = str.__getattribute__(self, name)

        if not callable(f):
            return f

        this_dict = object.__getattribute__(self, '__dict__')
        if '_std' in this_dict:
            this_std = object.__getattribute__(self, '_std')

        def callback(*args, **kwargs):
            r = f(*args, **kwargs)
            if isinstance(r, str):
                new_string = IString(r)
                if '_std' in this_dict:
                    new_string.set_std(this_std)
                return new_string
            return r

        return partial(callback)
