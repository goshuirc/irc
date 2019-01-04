# envelope.py
# Purpose: Conversion of RFC1459 messages to/from native objects.
#
# Copyright (c) 2014, William Pitcock <nenolod@dereferenced.org>
#
# Permission to use, copy, modify, and/or distribute this software for any
# purpose with or without fee is hereby granted, provided that the above
# copyright notice and this permission notice appear in all copies.
#
# THE SOFTWARE IS PROVIDED "AS IS" AND THE AUTHOR DISCLAIMS ALL WARRANTIES
# WITH REGARD TO THIS SOFTWARE INCLUDING ALL IMPLIED WARRANTIES OF
# MERCHANTABILITY AND FITNESS. IN NO EVENT SHALL THE AUTHOR BE LIABLE FOR
# ANY SPECIAL, DIRECT, INDIRECT, OR CONSEQUENTIAL DAMAGES OR ANY DAMAGES
# WHATSOEVER RESULTING FROM LOSS OF USE, DATA OR PROFITS, WHETHER IN AN
# ACTION OF CONTRACT, NEGLIGENCE OR OTHER TORTIOUS ACTION, ARISING OUT OF
# OR IN CONNECTION WITH THE USE OR PERFORMANCE OF THIS SOFTWARE.

from pprint import pprint

_tag_unescapes = {
    '\\': '\\',
    ':': ';',
    's': ' ',
    'r': '\r',
    'n': '\n',
}
_tag_escapes = {v: k for k, v in _tag_unescapes.items()}


def tag_unescape(orig):
    value = ''
    while len(orig):
        char = orig[0]
        orig = orig[1:]
        if char == '\\':
            if not orig:
                break

            escape = orig[0]
            orig = orig[1:]
            value += _tag_unescapes.get(escape, escape)
        else:
            value += char

    return value


def tag_escape(orig):
    value = ''
    while len(orig):
        char = orig[0]
        orig = orig[1:]
        if char in _tag_escapes:
            value += '\\' + _tag_escapes[char]
        else:
            value += char

    return value


class RFC1459Message(object):
    @classmethod
    def from_data(cls, verb, params=None, source=None, tags=None):
        o = cls()
        o.verb = verb
        o.tags = dict()
        o.source = None
        o.params = list()

        if params:
            o.params = params

        if source:
            o.source = source

        if tags:
            o.tags.update(**tags)

        return o

    @classmethod
    def from_message(cls, message):
        if isinstance(message, bytes):
            message = message.decode('UTF-8', 'replace')

        s = message.split(' ')

        tags = None
        if s[0].startswith('@'):
            tag_str = s[0][1:].split(';')
            s = s[1:]
            tags = {}

            for tag in tag_str:
                if '=' in tag:
                    k, v = tag.split('=', 1)
                    tags[k] = tag_unescape(v)
                else:
                    tags[tag] = None

        source = None
        if s[0].startswith(':'):
            source = s[0][1:]
            s = s[1:]

        verb = s[0].upper()
        original_params = s[1:]
        params = []

        while len(original_params):
            # skip multiple spaces in middle of message, as per 1459
            if original_params[0] == '' and len(original_params) > 1:
                original_params.pop(0)
                continue
            elif original_params[0].startswith(':'):
                arg = ' '.join(original_params)[1:]
                params.append(arg)
                break
            elif len(original_params[0]):
                params.append(original_params.pop(0))
            else:
                original_params.pop(0)

        return cls.from_data(verb, params, source, tags)

    def args_to_message(self):
        base = []
        for arg in self.params:
            casted = str(arg)
            if casted and ' ' not in casted and casted[0] != ':':
                base.append(casted)
            else:
                base.append(':' + casted)
                break

        return ' '.join(base)

    def to_message(self):
        components = []

        if self.tags:
            components.append('@' + ';'.join(
                [k + '=' + tag_escape(v) if v is not None else k for k, v in self.tags.items()]
            ))

        if self.source:
            components.append(':' + self.source)

        if isinstance(self.verb, int):
            components.append(str(self.verb).zfill(3))
        else:
            components.append(self.verb)

        if self.params:
            components.append(self.args_to_message())

        return ' '.join(components)

    def to_event(self):
        return "rfc1459 message " + self.verb, self.__dict__

    def serialize(self):
        return self.__dict__

    def __str__(self):
        return 'RFC1459Message: "{0}"'.format(self.to_message())


def test_rfc1459message():
    print('====== PARSER TESTS ======')
    print(RFC1459Message.from_message('@foo=bar PRIVMSG kaniini :this is a test message!'))
    print(RFC1459Message.from_message('@foo=bar :irc.tortois.es 001 kaniini :Welcome to IRC, kaniini!'))
    print(RFC1459Message.from_message('PRIVMSG kaniini :this is a test message!'))
    print(RFC1459Message.from_message(':irc.tortois.es 001 kaniini :Welcome to IRC, kaniini!'))
    print(RFC1459Message.from_message('CAPAB '))

    print('====== STRUCTURE TESTS ======')
    m = RFC1459Message.from_message('@foo=bar;bar=baz :irc.tortois.es 001 kaniini :Welcome to IRC, kaniini!')
    pprint(m.serialize())

    print('====== BUILDER TESTS ======')
    data = {
        'verb': 'PRIVMSG',
        'params': ['kaniini', 'hello world!'],
        'source': 'kaniini!~kaniini@localhost',
        'tags': {'account-name': 'kaniini'},
    }
    m = RFC1459Message.from_data(**data)
    print(m.to_message())
    pprint(m.serialize())

    print('====== ALL TESTS: PASSED ======')

if __name__ == '__main__':
    test_rfc1459message()
