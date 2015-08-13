#!/usr/bin/env python3
# Written by Daniel Oaks <daniel@danieloaks.net>
# Released under the ISC license
from functools import partial
import collections
import encodings.idna
import string


class IMap:
    """Base object for supporting IRC casemapping."""

    def __init__(self):
        self._std = None

        self._lower_chars = None
        self._upper_chars = None

        self._lower_trans = None
        self._upper_trans = None

    def _set_transmaps(self):
        """Set translation maps for our standard."""
        if self._std == 'ascii':
            self._lower_chars = string.ascii_lowercase
            self._upper_chars = string.ascii_upper

        elif self._std == 'rfc1459':
            self._lower_chars = (string.ascii_lowercase +
                                 ''.join(chr(i) for i in range(91, 95)))
            self._upper_chars = (string.ascii_upper +
                                 ''.join(chr(i) for i in range(123, 127)))

        elif self._std == 'rfc1459-strict':
            self._lower_chars = (string.ascii_lowercase +
                                 ''.join(chr(i) for i in range(91, 94)))
            self._upper_chars = (string.ascii_upper +
                                 ''.join(chr(i) for i in range(123, 126)))

        # rfc3454 handled by nameprep function

    def set_std(self, std):
        """Set the standard we'll be using (isupport CASEMAPPING)."""
        if not hasattr(self, '_std'):
            IMap.__init__(self)

        # translation based on std
        self._std = std.lower()

        # set casemapping maps
        self._set_transmaps()

        # create translations
        if self._lower_chars:
            self._lower_trans = str.maketrans(self._lower_chars, self._upper_chars)
        if self._upper_chars:
            self._upper_trans = str.maketrans(self._upper_chars, self._lower_chars)

    def _translate(self, value):
        if self._std == 'rfc3454':
            return encodings.idna.nameprep(value)

        if self._lower_trans is not None:
            return value.translate(self._lower_trans)


class IDict(collections.MutableMapping, IMap):
    """Case-insensitive IRC dict, based on IRC casemapping standards."""

    def __init__(self, data={}, *args, **kwargs):
        self.store = dict()
        IMap.__init__(self)
        self.update(data)
        self.update(dict(*args, **kwargs))  # use the free update to set keys

    @property
    def json(self):
        return self.store

    def __repr__(self):
        return str(self.store)

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
        if isinstance(key, str):
            key = self._translate(key)
        return key.lower()

    def copy(self):
        """Return a copy of ourself."""
        new_dict = IDict(std=self._std)
        new_dict.update(self.store)
        return new_dict


class IList(collections.MutableSequence, IMap):
    """Case-insensitive IRC list, based on IRC casemapping standards."""

    def __init__(self, data=[], *args):
        self.store = list()
        IMap.__init__(self)
        self.extend(data)
        self.extend(dict(*args))

    @property
    def json(self):
        return self.store

    def __repr__(self):
        return str(self.store)

    def __valuetransform__(self, value):
        # XXX - could also simply make them IStrings
        #   or do some more complex processing on them below...
        if isinstance(value, str):
            value = self._translate(value)
        return value

    def __getitem__(self, index):
        return self.store[index]

    def __setitem__(self, index, value):
        value = self.__valuetransform__(value)
        self.store[index] = value

    def __delitem__(self, index):
        del self.store[index]

    def __len__(self):
        return len(self.store)

    def append(self, value):
        value = self.__valuetransform__(value)
        self.store.append(value)

    def clear(self):
        del self.store
        self.store = []

    def extend(self, values):
        if isinstance(values, (list, tuple)):
            for value in values:
                value = self.__valuetransform__(value)
                self.store.append(value)
        else:
            self.store += self.__valuetransform__(values)

    def insert(self, index, value):
        value = self.__valuetransform__(value)
        self.store.insert(index, value)

    def pop(self, index=-1):
        return self.store.pop(index)

    def remove(self, value):
        value = self.__valuetransform__(value)
        self.store.remove(value)

    def reverse(self):
        self.store.reverse()


class IString(str, IMap):
    """Case-insensitive IRC string (for channel/usernames), based on IRC casemapping."""

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
        conv_string = self._translate(in_string)
        if self._lower_trans is not None:
            conv_string = conv_string.translate(self._lower_trans)
        return str.lower(conv_string)

    def _irc_upper(self, in_string):
        """Convert us to our upper-case equivalent, given our std."""
        conv_string = self._translate(in_string)
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
    # this is so we can just do normal .title() / .split() / .etc calls
    #   as though IString were a normal str class
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
