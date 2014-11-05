
from celery import task
from pages.models import UploadedImage
from pages.settings import IMG_PATH

# XXX -  not callable on pylint!
@task()#pylint: disable=not-callable
def upload_to_s3(uploaded_file, account, filename):
    img_obj = UploadedImage(
                uploaded_file=uploaded_file,
                account=account
                )
    img_obj.save()
    full_path = IMG_PATH + account.slug + '/' + filename
    UploadedImage.objects.filter(
        uploaded_file=full_path).order_by('-created_at')[0].delete()
