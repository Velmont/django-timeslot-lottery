Django Timeslot Lottery
=======================

Let people bid for weekly timeslots and pick worthy winners.

The app is good for booking a limited resource, and not letting the
same people 'win' all the time.  Bidders who has the least amount of
wins will be tried to be given a slot first.


Trying out / development
------------------------

You can try out the example app quite simply:

    virtualenv env
    python setup.py develop
    python example/manage.py migrate
    python example/manage.py runserver
