Pages Upload Media
==================

Djaodjin-pages integrate also a Media gallery. You will be able to upload media file like images or videos.

Configuration
-------------

There are two different configuration possible. 

Basic
~~~~~

This configuration upload media into server. Only add this settings in your settings.py

.. code-block:: python

    MEDIA_ROOT = '/media_path'    
    PAGES_MEDIA_PATH = '/path/to/uploaded/media'


All uploaded media will be on ```/media_path/path/to/uploaded/media```

In the case you use the PAGES_ACCOUNT_MODEL to specify property of media, path will be ``/media_path/path/to/uploaded/media/account_slug```

Amazon S3 storage
~~~~~~~~~~~~~~~~~

If you want external media storage, djaodjin-pages allows to upload media to Amazon S3. For this we need boto and django-celery

.. code-block:: bash
    
    $ pip install boto django-celery

.. code-block:: python

    # allows you to switch between classic upload and S3 upload. Useful to debug.
    USE_S3 = True

    # By default djaodjin-pages will save uploaded file in your server
    # while the file is being uploaded to S3. If you don't want any file
    # in you server turn it to True. In this case, djaodjin-pages will
    # create a image miniature/ video sample to be uploaded quickly to S3.
    # In both case, the upload to S3 is background job.
    PAGES_NO_LOCAL_STORAGE = False

    # Your Amazon credential
    AWS_ACCESS_KEY_ID = ''
    AWS_SECRET_ACCESS_KEY = ''

    # Amazon S3 bucket name
    AWS_STORAGE_BUCKET_NAME = ''

    # Your S3 bucket url to serve files. 
    # Don't forget to allow anybody to read it. on amazon console
    S3_URL = 'https://%s.s3.amazonaws.com' % AWS_STORAGE_BUCKET_NAME

    DEFAULT_FILE_STORAGE = 'storages.backends.s3boto.S3BotoStorage'


Upload to S3 may take a while. So Djaodjin-pages offer two possibilities to make this time invisible for user.

- **With local storage**

.. code-block:: python

    PAGES_NO_LOCAL_STORAGE = False

In this case, djaodjin-pages will save in first time the uploaded file in previous ```MEDIA_PATH``` directory, and will upload to S3 the file in background. Once the file uploaded to S3 the local file is deleted.

- **Without local storage**

.. code-block:: python

    PAGES_NO_LOCAL_STORAGE = True

If you don't want any uploaded file in your directory (even temporary), djaodjin-pages create an Image minitiature/ sample video to upload it to S3, In background djaodjin-pages upload to S3 the original media.

In this case it's necessary to install FFMEPG library to process the video file, and add path to ffmepg.

.. code-block:: python

    # You need to install ffmep library sample the video
    PAGES_FFMPEG_PATH = '/usr/local/bin/ffmpeg'


Usage
-----

By Using djaodjin-sidebar-gallery jquery plugin, you will be able to drag and drop media and use them into your HTML.

You only need to add image/video tags with an id starting by ```djmedia_``` ex: ```id="djmedia-image-top"```

Images
~~~~~~

.. code-block:: html
    
    <img alt="Generic placeholder image" class=" droppable-image" id="djmedia-zero" src="/static/vendor/img/test.gif" style="width: 140px; height: 140px;"/>


Video
~~~~~

.. code-block:: html
    
    <video controls="controls" src="" class="droppable-image video-bordered" id="djmedia-one" style="width:100%" ></video>



