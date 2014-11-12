$(document).ready(function(){

    var template_path = $('#template_path').val();
    var url_gallery = $('#url_gallery').val();
    var url_editor = $('#url_editor').val();
    var csrf_token = $('#csrf_token').val();
    
    $('body').editor({
        base_url: url_editor,
        autotag: false,
        template_path: template_path,
        csrf_token: csrf_token,
        enable_upload: false,
        img_upload_url:url_gallery,
    });

    $.sidebargallery({
        base_url:'/api/editables/',
        media_upload_url:url_gallery,
        csrf_token: csrf_token,
        list_media_url:'/api/list/uploaded-media/',
        base_update_media_url:'/api/media-detail/'


    });
});