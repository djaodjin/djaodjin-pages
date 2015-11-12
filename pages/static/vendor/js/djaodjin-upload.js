(function ($) {
    "use strict";

    function Djupload(el, options){
        this.element = $(el);
        this.options = options;
        this.init();
    }

    Djupload.prototype = {
        init: function(){
            var self = this;
            this.initDropzone();
        },

        initDropzone: function(){
            var self = this;
            var dropzoneUrl = self.options.uploadUrl;

            if (!dropzoneUrl){
                alert("No upload URL provided.", "error");
                throw new Error("No upload URL provided.");
            }

//            var djDropzone = new Dropzone(self.element, {
            self.element.dropzone({
                paramName: self.options.uploadParamName,
                url: dropzoneUrl,
                maxFilesize: self.options.uploadMaxFileSize,
                clickable: self.options.uploadClickableZone,
                createImageThumbnails: false,
                init: function() {

                    this.on("sending", function(file, xhr, formData){
                        if( self.options.accessKey) {
                            if (self.options.mediaPrefix !== "" && !self.options.mediaPrefix.match(/\/$/)){
                                self.options.mediaPrefix += "/";
                            }
                            formData.append("key", self.options.mediaPrefix + file.name);
                            formData.append("policy", self.options.policy);
                            formData.append("x-amz-algorithm", "AWS4-HMAC-SHA256");
                            formData.append("x-amz-credential",
                                            self.options.amzCredential);
                            formData.append("x-amz-date", self.options.amzDate);
                            formData.append("x-amz-security-token",
                                            self.options.securityToken);
                            formData.append("x-amz-signature",
                                            self.options.signature);
                        } else {
                            formData.append("csrfmiddlewaretoken",
                                            self.options.csrfToken);
                        }
                    });

                    this.on("success", function(file, response){
                        $(".dz-preview").remove();
                        self.options.uploadSuccess(file, response);
                    });

                    this.on("error", function(file, message){
                        $(".dz-preview").remove();
                        self.options.uploadError(file, message);
                    });

                    this.on("uploadprogress", function(file, progress){
                        self.options.uploadProgress(file, progress);
                    });
                }
            });
        }
    };

    $.fn.djupload = function(options) {
        var opts = $.extend({}, $.fn.djupload.defaults, options);
        return new Djupload($(this), opts);
    };

    $.fn.djupload.defaults = {

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

    Dropzone.autoDiscover = false;

})(jQuery);

