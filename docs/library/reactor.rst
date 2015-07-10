:class:`girc.Reactor` --- Managing IRC Connections
==================================================

.. class:: girc.Reactor

This class is the way you create and manage IRC connections. It lets you create new server connections, set user info, channel autoconnection info, and then connect to the server.

.. automethod:: girc.Reactor.run_forever

.. automethod:: girc.Reactor.close


Making connections
------------------

These functions let you make and manage connections to IRC servers.

.. automethod:: girc.Reactor.create_server

.. automethod:: girc.Reactor.set_user_info

.. automethod:: girc.Reactor.connect_to

    This method should be called once the necessary user info is set using
    :meth:`girc.Reactor.set_user_info`

.. automethod:: girc.Reactor.join_channels

    This example joins the channels ``#example`` and ``#cool`` on the ``testnet`` server:

    .. code-block:: python

        reactor.join_channels('testnet', '#example', '#cool')
