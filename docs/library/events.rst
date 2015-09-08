:mod:`girc.events` --- Event Handling
=====================================

.. module:: girc.events

This module handles event handling within girc, though users usually only interact with it via the :class:`girc.Reactor` and :class:`girc.client.ServerConnection` classes.

Registering events
------------------

There are several different ways to register for events in girc. You can register through the :class:`girc.Reactor`, which automatically registers it on every existing and new server, or through the :class:`girc.client.ServerConnection` for just that specific server.

Event registration for a :class:`girc.Reactor`:

.. automethod:: girc.Reactor.handler

.. automethod:: girc.Reactor.register_event

Event registration for a :class:`girc.client.ServerConnection`:

.. automethod:: girc.client.ServerConnection.register_event

Event directions
----------------

When registering events, you need to specify a direction to handle. These are girc's event directions:

=============   ===========
  Direction       Purpose
=============   ===========
  ``in``          Handle only events we receive from the server
  ``out``         Handle only events we send to the server
  ``both``        Handle both of the above
=============   ===========

Raw events
----------

In addition to the numerics below, the ``raw`` event details the exact bytes we send to and from the server. The attributes of a ``raw`` event are detailed below:

=================   ==========
    Attribute         Detail
=================   ==========
  ``server``          :class:`girc.client.ServerConnection` object
  ``direction``       ``in``, ``out``
  ``data``            The bytes we are sending or receiving
=================   ==========

Numerics
--------

This is our default numeric-to-event-name mapping. Most of these originate from `alien's numeric list <https://www.alien.net.au/irc/irc2numerics.html>`_, which is quite out of date, so there may be insane numerics in here. This list is constantly adapting, and we prefer `IRCv3 <http://ircv3.net>`_ numerics over old ones.

.. exec::
    from girc.events import numerics

    print("""
    ===========   ========
      Numeric       Name
    ===========   ========""")
    for numeric, name in sorted(numerics.items()):
        print('    ``{}``     ``{}``'.format(numeric, name))

    print("""===========   ========""")
