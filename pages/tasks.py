import os

from celery import task
from pages.models import UploadedImage, PageElement
from pages.settings import IMG_PATH, NO_LOCAL_STORAGE
from django.conf import settings

# XXX -  not callable on pylint!
@task()#pylint: disable=not-callable
def upload_to_s3(uploaded_file, account, filename):
    full_path = IMG_PATH + account.slug + '/' + filename
    if not NO_LOCAL_STORAGE:
        
        uploaded_temp = UploadedImage.objects.get(
            uploaded_file_temp=full_path)

        uploaded_temp.uploaded_file = uploaded_file
        # uploaded_temp.uploaded_file_temp = None
        uploaded_temp.save()

        page_elements = PageElement.objects.filter(text='/media/' + full_path)
        for page_element in page_elements:
            page_element.text = settings.S3_URL + '/' + full_path
            page_element.save()
        # delete file in server
        os.remove(os.path.join(settings.MEDIA_ROOT, full_path))
    else:
        img_obj = UploadedImage(
                    uploaded_file=uploaded_file,
                    account=account
                    )
        img_obj.save()
        UploadedImage.objects.filter(
            uploaded_file=full_path).order_by('-created_at')[0].delete()



    # img_obj = UploadedImage(
    #             uploaded_file=uploaded_file,
    #             account=account
    #             )
    # img_obj.save()
    
    # UploadedImage.objects.filter(
    #     uploaded_file=full_path).order_by('-created_at')[0].delete()
