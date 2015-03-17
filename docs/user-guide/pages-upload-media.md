#Djaodjin-pages: Upload media

*__Add Medias in your page by a simple drag'n'drop__*

---

##Configuration
----

Djaodjin-pages offer two configuration type.

1. Basic: Upload media Django way (file saved and served by your server)
1. Amazon S3 Storage: Upload media to Amazon S3 (file saved and served by Amazon)

### Basic

Update your settings.py to manage Media.

    PAGES = {
        ...
        'MEDIA_ROOT' : '/media_path',
        'MEDIA_PATH' : '/path/to/uploaded/media',
        ...
    }

All uploaded media will be saved on ```/media_path/path/to/uploaded/media```. If the [ACCOUNT_MODEL](pages-edition.md#configuration), medias will be saved automatically per account so in ```/media_path/path/to/uploaded/media/account_slug```

### Amazon S3 Storage

This feature requires two more dependencies: boto, django-storages and django-celery, So first:

    $ pip install boto django-celery django-storages

Add configuration to your settings.py

    PAGES = {
        ...
        'USE_S3' : True,
        'AWS_ACCESS_KEY_ID' : '',
        'AWS_SECRET_ACCESS_KEY' : '',
        ...
    }


By default djaodjin-pages will save uploaded file in your server while the file is being uploaded to S3. If you don't want any file in you server turn ```NO_LOCAL_STORAGE```to True. In this case, Djaodjin-pages will create a image miniature / video sample to be uploaded quickly to S3. In both case, the upload to S3 is background job.


    PAGES = {
        ...
        'NO_LOCAL_STORAGE': True,
        ...
    }

If ```NO_LOCAL_STORAGE``` Djaodjin-pages need the [FFMEG](https://www.ffmpeg.org/) library to proccess video file (make sample)


---
##Usage
---

By Using djaodjin-sidebar-gallery jquery plugin, you will be able to drag and drop media and use them into your HTML.

You only need to add image/video tags with an id starting by ```djmedia_``` ex: ```id="djmedia-image-top"```

**Images**

    <img alt="Generic placeholder image" class=" droppable-image" id="djmedia-zero" src="/static/vendor/img/test.gif" style="width: 140px; height: 140px;"/>


**Video**

    <video controls="controls" src="" class="droppable-image video-bordered" id="djmedia-one" style="width:100%" ></video>
