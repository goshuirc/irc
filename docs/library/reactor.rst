:class:`girc.Reactor` --- Managing IRC Connections
==================================================

.. class:: girc.Reactor

This class is the way you create and manage IRC connections.

.. automethod:: girc.Reactor.run_forever

.. automethod:: girc.Reactor.shutdown

.. automethod:: girc.Reactor.close


Registering events
------------------

You can register events with the reactor to have them automagically registered with every server you connect to.

.. automethod:: girc.Reactor.register_event


Making connections
------------------

These functions let you make connections to IRC servers.

.. automethod:: girc.Reactor.create_server
