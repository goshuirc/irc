#!/usr/bin/env python3
# Written by Daniel Oaks <daniel@danieloaks.net>
# Released under the ISC license
"""girc - A modern Python IRC library for Python 3.4, based on asyncio.

This is not even in alpha right now. If you use this, anything can change
without any notice whatsoever, everything can be overhauled, and development
may even stop entirely without any warning.

Usage:
    test.py connect [options] [<channel>...]
    test.py (-h | --help)

Options:
    --nick=<nick>   Nick to connect with [default: girc].
    --host=<host>   Host for the bot to connect to [default: localhost].
    --port=<port>   Port for the bot to connect to [default: 6667].
    --ssl           Connect via SSL.
    --ipv4          Connect via IPv4.
    --ipv6          Connect via IPv6.
"""
import socket

from docopt import docopt

import girc
from girc.formatting import escape

reactor = girc.Reactor()


@reactor.handler('in', 'raw', priority=1)
def handle_raw_in(event):
    print(event['server'].name, ' ->', escape(event['data']))


@reactor.handler('out', 'raw', priority=1)
def handle_raw_out(event):
    print(event['server'].name, '<- ', escape(event['data']))


@reactor.handler('in', 'pubmsg')
@reactor.handler('in', 'privmsg')
def handle_hi(event):
    if event['message'].lower().startswith('hi'):
        event['source'].msg("Hi! I'm a $c[red,blue]TEST$r bot")


@reactor.handler('in', 'ctcp')
def handle_ctcp(event):
    if event['ctcp_verb'] == 'version':
        event['source'].ctcp_reply('VERSION', 'girc test bot:git:python')
    elif event['ctcp_verb'] == 'source':
        event['source'].ctcp_reply('SOURCE', 'https://github.com/DanielOaks/girc')
    elif event['ctcp_verb'] == 'clientinfo':
        event['source'].ctcp_reply('CLIENTINFO', 'ACTION CLIENTINFO SOURCE VERSION')


if __name__ == '__main__':
    arguments = docopt(__doc__)

    if arguments['connect']:
        nick = arguments['--nick']
        channels = arguments['<channel>']
        host = arguments['--host']
        port = int(arguments['--port'])
        use_ssl = arguments['--ssl']
        use_ipv4 = arguments['--ipv4']
        use_ipv6 = arguments['--ipv6']

        print('Connecting to {h}:{p}'.format(h=host, p=port))

        if arguments['--ipv6']:
            family = socket.AF_INET6
        elif arguments['--ipv4']:
            family = socket.AF_INET
        else:
            family = 0

        reactor.create_server('local', host, port, ssl=use_ssl, family=family)
        reactor.set_user_info('local', nick, user=nick)
        reactor.join_channels('local', *channels)
        reactor.connect_to('local')

        try:
            reactor.run_forever()
        except KeyboardInterrupt:
            pass

        reactor.close()
