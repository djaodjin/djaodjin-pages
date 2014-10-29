
from celery import task
from pages.models import UploadedImage
from pages.settings import IMG_PATH

# XXX -  not callable on pylint!
@task()#pylint: disable=not-callable
def upload_to_s3(img, account, tags, filename):
    img_obj = UploadedImage(
                img=img,
                account=account,
                tags=tags
                )
    img_obj.save()
    print filename
    full_path = IMG_PATH + account.slug + '/' + filename
    UploadedImage.objects.filter(
        img=full_path).order_by('-created_at')[0].delete()
