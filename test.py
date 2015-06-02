#!/usr/bin/env python3
# Written by Daniel Oaks <daniel@danieloaks.net>
# Released under the ISC license
import girc

reactor = girc.Reactor()

reactor.connect_to_server('local', '127.0.0.1', 6667)
reactor.set_user_info('local', 'goshu', user='n')
reactor.join_channels('local', '#services', '#a', '#testchan')

@reactor.handler('in', 'raw', priority=1)
def handle_raw_in(event):
    print(event['server'].name, ' ->', event['data'])

@reactor.handler('out', 'raw', priority=1)
def handle_raw_out(event):
    print(event['server'].name, '<- ', event['data'])

@reactor.handler('in', 'pubmsg')
@reactor.handler('in', 'privmsg')
def handle_hi(event):
    if event['message'].lower().startswith('hi'):
        event['source'].msg('Hi!')

print('Connecting')
try:
    reactor.start()
except KeyboardInterrupt:
    pass

reactor.close()
