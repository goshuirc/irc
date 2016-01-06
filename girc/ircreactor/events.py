# events.py
# Purpose: Subscription, broadcast and mutation of events
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

import logging

logger = logging.getLogger(__name__)

class EventObject(object):
    """An object for managing a specific event type.  Handles dispatch to interested subscribers.
       Call EventObject.dispatch() with the event message dictionary to actually do the dispatch.
       However, this is normally done using an EventManager."""
    def __init__(self, event, manager=None):
        if manager:
            manager.events[event] = self
        self.subscribers = list()

    def attach(self, receiver):
        nlist = self.subscribers + [receiver]
        self.subscribers = sorted(nlist, key=lambda x: x.priority)

    def detach(self, receiver):
        self.subscribers.remove(receiver)

    def dispatch(self, ev_msg):
        [sub.callable(ev_msg) for sub in self.subscribers]

class EventReceiver(object):
    """An internal object which tracks event subscriptions, acting as a handle for the event system.
       To unsubscribe an event, simply delete the handle, using del."""
    def __init__(self, event, callable, manager=None, priority=10):
        self.event = event
        self.callable = callable
        self.priority = priority
        if manager:
            self.eo = manager.events.get(event, None)
            if not self.eo:
                self.eo = EventObject(event, manager)
            self.eo.attach(self)

    def __del__(self):
        if self.eo:
            self.eo.detach(self)

class EventManager(object):
    """A manager of events.  Manages EventObjects and EventReceivers.
       Call dispatch() with an event name and a message argument to dispatch.
       Call register() with an event name and a callable to subscribe."""
    def __init__(self):
        self.events = dict()

    def dispatch(self, event, ev_msg):
        """Dispatch an event.
               event: name of the event (str)
               ev_msg: non-optional arguments dictionary.
           Side effects:
               If an EventObject is not already registered with the EventManager,
               a new EventObject will be created and registered."""
        logger.debug('dispatching: ' + event + ': ' + repr(ev_msg))
        eo = self.events.get(event, None)
        if eo:
            eo.dispatch(ev_msg)

    def register(self, event, callable, priority=10):
        """Register interest in an event.
               event: name of the event (str)
               callable: the callable to be used as a callback function
           Returns an EventReceiver object.  To unregister interest, simply
           delete the object."""
        logger.debug('registered: ' + event + ': ' + repr(callable) + ' [' + repr(self) + ']')
        return EventReceiver(event, callable, manager=self, priority=priority)
