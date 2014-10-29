from django.core.cache import cache
from django.core.files.uploadhandler import FileUploadHandler


class ProgressBarUploadHandler(FileUploadHandler):
    """
    Cache system for TemporaryFileUploadHandler
    """
    def __init__(self, *args, **kwargs):
        super(ProgressBarUploadHandler, self).__init__(*args, **kwargs)
        self.progress_id = None
        self.cache_key = None

    def handle_raw_input(self, input_data, META, content_length, boundary, encoding=None):
        self.content_length = content_length
        if 'X-Progress-ID' in self.request.GET:
            self.progress_id = self.request.GET['X-Progress-ID']
        elif 'X-Progress-ID' in self.request.META:
            self.progress_id = self.request.META['X-Progress-ID']
        if self.progress_id:
            self.cache_key = "%s_%s" % (self.request.META['REMOTE_ADDR'], self.progress_id)
            cache.set(self.cache_key, {
                'length': self.content_length,
                'uploaded': 0
            })

    def new_file(self, field_name, file_name, content_type, content_length, charset=None, *args, **kwargs):
        pass

    def receive_data_chunk(self, raw_data, start):
        if self.cache_key:
            data = cache.get(self.cache_key)
            data['uploaded'] += self.chunk_size
            cache.set(self.cache_key, data)
        return raw_data

    def file_complete(self, file_size):
        pass

    def upload_complete(self):
        if self.cache_key:
            cache.delete(self.cache_key)