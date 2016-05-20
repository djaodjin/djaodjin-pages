jQuery(document).ready(function($) {


    $("#toggle-code-editor").panelButton({defaultWidth: 800});
    $("#toggle-style-editor").panelButton({defaultWidth: 800});
    $("#toggle-media-gallery").panelButton({defaultWidth: 300});



    var $iframe_view = $('iframe#template_view');
    $('#style-editor').djstyles({
        api_bootstrap_overrides: urls_edit_bootstrap_variables,
        api_sitecss: urls_edit_api_sitecss,
        iframe_view: $iframe_view.get(0)
    });

    $("#code-editor .content").djtemplates({
        api_source_code: urls_edit_api_sources,
        iframe_view: $iframe_view.get(0)
    });

    $iframe_view.on("load", function(){
        console.log('loading iframe again');
        var view = $iframe_view.get(0);

        var djstyles = $('#style-editor').data('djstyles');


        function addScript(url){
            var doc = view.contentWindow.document;

            var script   = doc.createElement("script");
            script.type  = "text/javascript";
            script.src   = url;
            doc.body.appendChild(script);

        };
        function addLess(url){
            var doc = view.contentWindow.document;

            var script   = doc.createElement("link");
            script.rel  = "stylesheet/less";
            script.type = "text/css"
            script.href   = url;
            doc.body.appendChild(script);
        };

        view.contentWindow.urls_edit_api_page_elements = urls_edit_api_page_elements;
        view.contentWindow.less = {
            env: "development",
            async: false,
            fileAsync: false,
            functions: {},
            dumpLineNumbers: "comments",
            relativeUrls: false,
            rootpath: less_root
            ,  onReady: false
            // , modifyVars: djstyles.modifiedVars()
        };

        view.contentWindow.edition_sources = edition_sources.slice();
        addScript(load_edition_src);

        addScript(less_src);

    });

    $(".btn-tools .btn").click(function(){
        $(this).blur();
    });

    var djGalleryOptions = {
        mediaUrl: urls_edit_media_upload,
        csrfToken: csrf_token,
        loadImageEvent: "gallery-opened",

        saveDroppedMediaUrl:  urls_edit_api_page_elements ,
        mediaPrefix: media_prefix,
        buttonClass: "btn btn-block btn-primary",
        mediaClass: "thumbnail thumbnail-gallery",
        selectedMediaClass: "thumbnail-active",
        clickableArea: ".clickable-area",
        itemUploadProgress: function(progress){
            $(".gallery-upload-progress").slideDown();
            progress = progress.toFixed();
            $(".progress-bar").css("width", progress + "%");
            if (progress == 100){
                $(".progress-bar").text("Upload completed");
                setTimeout(function(){
                    $(".gallery-upload-progress").slideUp();
                    $(".progress-bar").text("").css("width", "0%");
                }, 2000);
            }
        },
        galleryItemOptionsTemplate: "<div class=\"input-group\"><input type=\"text\" class=\"form-control\" readonly data-dj-gallery-media-url><span class=\"input-group-btn\"><button data-dj-gallery-media-location class=\"dj-gallery-preview-item btn btn-primary\" type=\"button\"><i class=\"fa fa-eye fa-lg\"></i></button></span></div>\n<br><div class=\"input-group\"><input type=\"text\" data-dj-gallery-media-tag class=\"dj-gallery-tag-input form-control\" placeholder=\"tags...\" aria-describedby=\"basic-addon1\"><span class=\"input-group-btn\"><button class=\"dj-gallery-tag-item btn btn-primary\" type=\"button\">Tag</button></span></div><span class=\"help-block\">Tags must be separated by a comma. ex: video, title</span>\n<button data-dj-gallery-media-location class=\"dj-gallery-delete-item btn btn-primary btn-block\"><i class=\"fa fa-trash-o fa-lg\"></i> Delete</button>\n",
        galleryMessage: function(message, type){
            if (!type){
                type = "success";
            }
            toastr[type](message)
        },
        previewMediaItem: function(src, type){
            $("#modal-preview-media .modal-body").empty();
            if (type == "video"){
                $("#modal-preview-media .modal-body").append("<video src=\"" + src + "\" controls style=\"max-width:100%\"></video>");
            }else{
                $("#modal-preview-media .modal-body").append("<img src=\"" + src + "\" style=\"max-width:100%\">");
            }
            $("#modal-preview-media").modal('show');
        }
    };
    if ( window.s3_direct_upload_url && s3_direct_upload_url != ''){
        $.extend(djGalleryOptions,{
            S3DirectUploadUrl: s3_direct_upload_url,
            accessKey: access_key,
            policy: aws_policy,
            signature: aws_policy_signature,
            securityToken: security_token,
            amzCredential: x_amz_credential,
            amzDate: x_amz_date
        });
    }
    $(".dj-gallery").djgallery(djGalleryOptions);

    $(document).on("click", "[data-dj-gallery-media-url]" , function(){
        this.select();
    })
});
