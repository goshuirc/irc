State Tracking
==============
This is a 'dev note', or a document I've written up while developing gIRC to keep track of why I've made certain decisions. This probably won't be useful to you unless you plan to hack on gIRC.

There are two main ways we can track state and pass users/channels through our event dispatching system.

1. User / Channel objects, info gotten like: ``event['source'].host``
2. Everything stored as dicts, and requested as ``event['server'].info.get_user('nick').get('host')`` at runtime

----

Upsides of objects
------------------
Simplifies rerieving information, since the User/Channel object is right there in the request, and instantly contains up-to-date information. Because it is an instance of a class rather than a string or dict, it will simply be automagically updated with the newest information if something like the ``Info`` subsystem gets a ``CHGHOST`` happens.

Simplifies actions. Because we are able to have ``User.msg()`` and ``Channel.mode()`` functions right there on the objects returned in the event dispatch, performing IRC actions on them is dirt simple.

Downsides of objects
--------------------
Because it's a class instance passed through with the event dispatching, do we need to keep around ``Channel`` objects after the channel has been parted, since removing it could mess up the functions handling the ``part`` event?

This problem could be pushed aside by calling the ``update_info`` function before we dispatch events. However, the ``update_info`` function requires an event, so if we wanted to be 100% perfect we would need to create the event, throw it to ``update_info``, and then create new events for everything else. Maybe.

That 100% perfect option throws out the fact that on ``part`` events, it makes more sense to give them all the information we knew about that channel at the time of the part, rather than removing the channel from our ``Info`` list and then giving them a ``None`` or whatever since the channel no longer exists for the second event creation.

----

Upsides of dicts / strings
--------------------------
Dicts and strings are simple to write on the library side. You store them in the ``Info`` subsystem, and they're requested with functions like ``Info.get_user()`` and ``Info.get_channel``. There's no need to worry about the special cases like above, since every function will do

Downsides of dicts / strings
----------------------------
Information gets out of date. If we went with dicts / strings, we would want to include the user / channel information dicts in our dispatched events, to lessen the overhead of the required ``Info.get_*`` calls above (since most handlers need that info).

Specifically, we would end up creating events for ``update_info``, and then after calling ``update_info`` we would need to recreate those events.

Taking the ``CHGHOST`` example above, if we create the events, then call ``update_info``, the user's host would change. With objects, this would be updated in the object and we can dispatch like normal. With dicts and strings, we need to recreate those events so we have the new hostname in the user dictionary. (For that event, old and new hostname variables would of course be included, but the base user information would need to get updated).

We could do it this way, but it feels like a compromise that I don't want to make.

----

The best path here would probably be to use objects. That way, we can create the events, call ``update_info`` specially before we enter the event dispatching queue, and then dispatch that event in the normal way.

Taking the ``part`` example, the ``update_info`` can remove channels from our ``Info`` subsystem and set ``Channel.joined = False`` because they technically no longer exist. We can then pass the existing, 'historic' ``Channel`` object to the rest of the event queue.

That way, even functions like ``Channel.join()`` would continue to work without issue in the event handlers, because the channel object they're using still exists. And will have all the information we knew about the channel at the time of the ``part`` event.

Taking the ``CHGHOST`` example, on the ``update_info`` call, the user object would be updated to having the latest hostname, and all the event handlers downstream would get the correct info without us having to worry about it.
