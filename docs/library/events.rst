:mod:`girc.events` --- Event Handling
=====================================

.. module:: girc.events

This module handles event handling within girc, though users usually only interact with it via the :class:`girc.Reactor` and :class:`girc.client.ServerConnection` classes.

Registering events
------------------

There are several different ways to register for events in girc. You can register through the :class:`girc.Reactor`, which automatically registers it on every existing and new server, or through the :class:`girc.client.ServerConnection` for just that specific server.

:class:`girc.Reactor` event registration
****************************************

.. automethod:: girc.Reactor.handler

.. automethod:: girc.Reactor.register_event

:class:`girc.client.ServerConnection` event registration
********************************************************

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

Events
------

There are several standard attributes that all events share. These are:

=================   ==========
    Attribute         Detail
=================   ==========
  ``server``          :class:`girc.client.ServerConnection` object
  ``direction``       ``in``, ``out``
  ``source``\*        :class:`girc.types.User`, :class:`girc.types.Channel`, :class:`girc.types.Server`, or :class:`girc.client.ServerConnection` object
  ``target``\*        :class:`girc.types.User`, :class:`girc.types.Channel`, :class:`girc.types.Server`, or :class:`girc.client.ServerConnection` object
=================   ==========

``*`` represents an optional attribute.

Which class ``source`` and ``target`` are depends on what we get back from the server. For some events, ``source`` and ``target`` can be a channel, a user, the server we are connected to or a different server. If ``source`` or ``target`` is us (the user we are), a :class:`girc.client.ServerConnection` object will be returned instead of one of the standard types.

Raw events
----------

In addition to the numerics below, the ``raw`` event details the exact bytes we send to and from the server. The attributes of a ``raw`` event are:

=================   ==========
    Attribute         Detail
=================   ==========
  ``server``          :class:`girc.client.ServerConnection` object
  ``direction``       ``in``, ``out``
  ``data``            The bytes we are sending or receiving
=================   ==========

Special event attributes
------------------------

Events can also have special attributes. Events that have special attributes are listed here.

.. exec::

    from girc.events import _verb_param_map

    attribute_descriptions = {
        'channel': ':class:`girc.types.Channel` object',
        'channels': 'List of :class:`girc.types.Channel` objects',
        'message': 'Message text',
        'names': 'List of nicks',
        'new_nick': 'New nickname',
        'nick': 'Nickname',
        'reason': 'Reason text',
        'target': 'The target user/channel/server object',
        'timestamp': 'Unix timestamp',
        'topic': 'Channel topic',
        'user': ':class:`girc.types.User` object',
    }

    event_attributes = {}
    for attribute_name, info in _verb_param_map.items():
        if attribute_name.startswith('escaped_'):
            attribute_name = attribute_name[8:]
        for i, event_names in info.items():
            for name in event_names:
                if name not in event_attributes:
                    event_attributes[name] = []
                event_attributes[name].append(attribute_name)

    for event_name, attributes in sorted(event_attributes.items()):
        print('``{}``'.format(event_name))
        print('*' * (len(event_name) + 4))
        print('')
        print('=================   ==========')
        print('    Attribute         Detail  ')
        print('=================   ==========')
        for attribute in attributes:
            print('  ``{}``            {}'.format(attribute, attribute_descriptions[attribute]))
        print('=================   ==========')
        print('\n\n')

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
