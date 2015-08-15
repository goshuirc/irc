#!/usr/bin/env python3
# Written by Daniel Oaks <daniel@danieloaks.net>
# Released under the ISC license
escape_character = '$'
format_dict = {
    'b': '\x02',  # bold
    'c': '\x03',  # colour
    'i': '\x1d',  # italic
    'u': '\x1f',  # underline
    'r': '\x0f',  # reset
}

colour_code_to_name = {
    0: 'white',
    1: 'black',
    2: 'blue',
    3: 'green',
    4: 'red',
    5: 'brown',
    6: 'magenta',
    7: 'orange',
    8: 'yellow',
    9: 'light green',
    10: 'cyan',
    11: 'light cyan',
    12: 'light blue',
    13: 'pink',
    14: 'grey',
    15: 'light grey',
}

colour_name_to_code = {v: k for k, v in colour_code_to_name.items()}

# need to use our own digits list because we can only accept
#   ascii digits in IRC colour codes
digits = '0123456789'


def _ctos(colour_code):
    code = int(colour_code)
    if code in colour_code_to_name:
        return colour_code_to_name[code]
    else:
        return 'unknown:' + code


def _extract_irc_colour_code(msg):
    colour_code = ''
    for i in range(2):
        if len(msg) and msg[0] in digits:
            char = msg[0]
            colour_code += msg[0]
            msg = msg[1:]
            if char in '23456789' or (len(msg) and msg[0] in '6789'):
                break
    return colour_code, msg


def extract_irc_colours(msg):
    """Extract the IRC colours from the start of the string.

    Extracts the colours from the start, and returns the colour code in our
    format, and then the rest of the message.
    """
    # first colour
    fore, msg = _extract_irc_colour_code(msg)

    if not fore:
        return '[]', msg
    if not len(msg) or msg[0] != ',':
        return '[{}]'.format(_ctos(fore)), msg

    msg = msg[1:]  # strip comma

    # second colour
    back, msg = _extract_irc_colour_code(msg)

    if back:
        return '[{},{}]'.format(_ctos(fore), _ctos(back)), msg
    else:
        return '[{}]'.format(_ctos(fore)), ',' + msg


def extract_girc_colours(msg, fill_last):
    """Extract the girc-formatted colours from the start of the string.

    Extracts the colours from the start, and returns the colour code in IRC
    format, and then the rest of the message.

    If `fill_last`, last number must be zero-padded.
    """
    colours, msg = msg.split(']', 1)
    colours = colours.lstrip('[')

    if ',' in colours:
        fore, back = colours.split(',')
        fore = colour_name_to_code[fore]
        back = colour_name_to_code[back]
        return '{},{}'.format(fore, back.zfill(2) if fill_last else back), msg
    else:
        fore = colour_name_to_code[colours]
        return '{}'.format(fore.zfill(2) if fill_last else fore), msg


def escape(msg):
    """Takes a raw IRC message and returns a girc-escaped message."""
    msg = msg.replace(escape_character, 'girc-escaped-character')
    for escape_key, irc_char in format_dict.items():
        msg = msg.replace(irc_char, escape_character + escape_key)

    # convert colour codes
    new_msg = ''
    while len(msg):
        if msg.startswith(escape_character + 'c'):
            new_msg += msg[:2]
            msg = msg[2:]

            if not len(msg):
                new_msg += '[]'
                continue

            colours, msg = extract_irc_colours(msg)
            new_msg += colours
        else:
            new_msg += msg[0]
            msg = msg[1:]

    new_msg = new_msg.replace('girc-escaped-character', escape_character + escape_character)
    return new_msg


def unescape(msg):
    """Takes a girc-escaped message and returns a raw IRC message"""
    new_msg = ''

    while len(msg):
        char = msg[0]
        msg = msg[1:]
        if char == escape_character:
            escape_key = msg[0]
            msg = msg[1:]
            # we handle this character separately, otherwise we mess up and
            #   double escape characters while escaping and unescaping
            if escape_key == escape_character:
                new_msg += escape_character
            else:
                new_msg += format_dict[escape_key]

            if escape_key == 'c':
                fill_last = len(msg) and msg[0] in digits
                colours, msg = extract_girc_colours(msg, fill_last)
                new_msg += colours
        else:
            new_msg += char

    return new_msg
