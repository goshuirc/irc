#!/usr/bin/env python3
# Written by Daniel Oaks <daniel@danieloaks.net>
# Released under the ISC license
escape_character = '$'
format_dict = {
    'b': '\x02',  # bold
    'c': '\x03',  # color
    'i': '\x1d',  # italic
    'u': '\x1f',  # underline
    'r': '\x0f',  # reset
}


def escape(msg):
    """Return an escaped message."""
    msg = msg.replace(escape_character, 'girc-escaped-character')
    for escape_key, irc_char in format_dict.items():
        msg = msg.replace(irc_char, escape_character + escape_key)
    msg = msg.replace('girc-escaped-character', escape_character + escape_character)
    return msg

def unescape(msg):
    """Take an escaped message and return an unescaped result."""
    new_msg = ''

    while len(msg):
        char = msg[0]
        msg = msg[1:]
        if char == escape_character:
            escape_key = msg[0]
            msg = msg[1:]
            new_msg += format_dict[escape_key]
        else:
            new_msg += char

    return new_msg
