:class:`girc.client.ServerConnection` --- Single Server Connection
==================================================================

.. class:: girc.client.ServerConnection

This class handles a connection to a single IRC server. It's created by your :class:`girc.Reactor` using :meth:`girc.Reactor.create_server`, and usually accessed from events.

Connection
----------

These functions let you set connection information and actually connect to a network!

.. automethod:: girc.client.ServerConnection.set_user_info

.. automethod:: girc.client.ServerConnection.set_connect_password

.. automethod:: girc.client.ServerConnection.sasl_plain

.. automethod:: girc.client.ServerConnection.join_channels

    This example joins the channels ``#example`` and ``#cool``:

    .. code-block:: python

        server.join_channels('#example', '#cool')

.. automethod:: girc.client.ServerConnection.connect

    This method should be called once the necessary user info is set using
    :meth:`girc.client.ServerConnection.set_user_info`

IRC casemapping
---------------

One of the important features of :class:`girc.client.ServerConnection` objects is the ability to easily create strings, lists, and dictionaries that follow the IRC server's casemapping. This is done using the following functions:

.. automethod:: girc.client.ServerConnection.istring

.. automethod:: girc.client.ServerConnection.ilist

.. automethod:: girc.client.ServerConnection.idict

Sending Messages
----------------

These are the main ways you'll interact with the server directly. It lets you send IRC messages directly to the server using a general sending function, as well as convenience methods for specific messages:

.. automethod:: girc.client.ServerConnection.send

.. automethod:: girc.client.ServerConnection.msg

.. automethod:: girc.client.ServerConnection.notice

.. automethod:: girc.client.ServerConnection.ctcp

.. automethod:: girc.client.ServerConnection.ctcp_reply

.. automethod:: girc.client.ServerConnection.mode

.. automethod:: girc.client.ServerConnection.join_channel
