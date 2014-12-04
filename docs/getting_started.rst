Getting started
===============

After cloning the repository, create a virtualenv environment, install
the prerequisites, create the database then run the testsite webapp.


.. code-block:: bash

    $ virtualenv-2.7 _installTop_
    $ source _installTop_/bin/activate
    $ pip install -r requirements.txt
    $ make initdb
    $ python manage.py runserver

    # Browse http://localhost:8000/
    # Start edit live templates
