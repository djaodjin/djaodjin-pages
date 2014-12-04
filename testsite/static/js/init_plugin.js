$(document).ready(function(){

    function getCookie(name) {
        var cookieValue = null;
        if (document.cookie && document.cookie != '') {
            var cookies = document.cookie.split(';');
            for (var i = 0; i < cookies.length; i++) {
                var cookie = jQuery.trim(cookies[i]);
                // Does this cookie string begin with the name we want?
                if (cookie.substring(0, name.length + 1) == (name + '=')) {
                    cookieValue = decodeURIComponent(cookie.substring(name.length + 1));
                    break;
                }
            }
        }
        return cookieValue;
    }
    var csrftoken = getCookie('csrftoken');
    function csrfSafeMethod(method) {
        // these HTTP methods do not require CSRF protection
        return (/^(GET|HEAD|OPTIONS|TRACE)$/.test(method));
    }

    $.ajaxSetup({
        crossDomain: false, // obviates need for sameOrigin test
        beforeSend: function(xhr, settings) {
            if (!csrfSafeMethod(settings.type)) {
                xhr.setRequestHeader("X-CSRFToken", csrftoken);
            }
        }
    });
    
    var template_path = $('#template_path').val();
    var url_gallery = $('#url_gallery').val();
    var url_editor = $('#url_editor').val();
    var csrf_token = csrftoken;
    
    $('body').editor({
        base_url: url_editor,
        autotag: false,
        template_path: template_path,
        csrf_token: csrftoken,
        enable_upload: false,
    });

    $.sidebargallery({
        base_save_url:'/api/editables/',
        csrf_token: csrftoken,
        base_media_url:url_gallery
    });
});