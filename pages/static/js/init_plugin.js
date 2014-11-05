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
        enable_upload: true,
        img_upload_url:url_gallery,
    });

    $.sidebargallery({
        base_url:'/example/api/editables/',
        img_upload_url:url_gallery,
        csrf_token: csrf_token,

    });

    
});