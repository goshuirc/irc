#!/usr/bin/env python3
# Written by Daniel Oaks <daniel@danieloaks.net>
# Released under the ISC license
import girc

reactor = girc.Reactor()

reactor.connect_to_server('local', '127.0.0.1', 6667, nick='goshu', user='n')
reactor.join_channels('local', '#services', '#a', '#testchan')

@reactor.handler('raw in', priority=1)
def handle_raw_in(info):
    print(info['server'].name, ' ->', info['data'])

@reactor.handler('raw out', priority=1)
def handle_raw_out(info):
    print(info['server'].name, '<- ', info['data'])

print('Connecting')
try:
    reactor.start()
except KeyboardInterrupt:
    pass

reactor.close()
