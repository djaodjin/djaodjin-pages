(function ($) {
    "use strict";

    var djUpload = null;

    function Djupload(options){
        this.options = options;
        this.init();
        Dropzone.autoDiscover = false;
    }

    Djupload.prototype = {
        init: function(){
            djUpload = this;
            djUpload.initDropzone();
        },

        initDropzone: function(){
            var dropzoneUrl = djUpload.options.uploadUrl;

            if (!dropzoneUrl){
                alert("No upload URL provided.", "error");
                throw new Error("No upload URL provided.");
            }

            var djDropzone = new Dropzone("body", {
                paramName: djUpload.options.uploadParamName,
                url: dropzoneUrl,
                maxFilesize: djUpload.options.uploadMaxFileSize,
                clickable: djUpload.options.uploadClickableZone,
                createImageThumbnails: false
            });

            djDropzone.on("sending", function(file, xhr, formData){
                if( djUpload.options.accessKey) {
                    if (djUpload.options.mediaPrefix !== "" && !djUpload.options.mediaPrefix.match(/\/$/)){
                        djUpload.options.mediaPrefix += "/";
                    }
                    formData.append("key", djUpload.options.mediaPrefix + file.name);
                    formData.append("policy", djUpload.options.policy);
                    formData.append("x-amz-algorithm", "AWS4-HMAC-SHA256");
                    formData.append("x-amz-credential",
                        djUpload.options.amzCredential);
                    formData.append("x-amz-date", djUpload.options.amzDate);
                    formData.append("x-amz-security-token",
                        djUpload.options.securityToken);
                    formData.append("x-amz-signature",
                        djUpload.options.signature);
                } else {
                    formData.append("csrfmiddlewaretoken",
                        djUpload.options.csrfToken);
                }
            });

            djDropzone.on("success", function(file, response){
                $(".dz-preview").remove();
                djUpload.options.uploadSuccess(file, response);
            });

            djDropzone.on("error", function(file, message){
                $(".dz-preview").remove();
                djUpload.options.uploadError(file, message);
            });

            djDropzone.on("uploadprogress", function(file, progress){
                djUpload.options.uploadProgress(file, progress);
            });
        }
    };

    $.djupload = function(options) {
        var opts = $.extend( {}, $.djupload.defaults, options );
        return new Djupload(opts);
    };

    $.djupload.defaults = {

        uploadUrl: null,
        csrfToken: "",
        uploadZone: "body",
        uploadClickableZone: true,
        uploadParamName: "file",
        uploadMaxFileSize: 250,

        // S3 direct upload
        accessKey: null,
        mediaPrefix: null,
        securityToken: null,
        policy: "",
        signature: null,
        amzCredential: null,
        amzDate: null,

        // callback
        uploadSuccess: function(file, response){ return true; },
        uploadError: function(file, message){ return true; },
        uploadProgress: function(progress){ return true; },

    };

})(jQuery);

