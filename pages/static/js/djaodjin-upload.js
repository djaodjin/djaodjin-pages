(function ($) {
    "use strict";

    function Djupload(el, options){
        this.element = $(el);
        this.options = options;
        this.init();
    }

    /* UI element to upload files directly to S3.

       <div data-complete-url="">
       </div>
     */
    Djupload.prototype = {

        _csrfToken: function() {
            var self = this;
            if( self.options.csrfToken ) { return self.options.csrfToken; }
            return getMetaCSRFToken();
        },

        _uploadSuccess: function(file, resp) {
            var self = this;
            if( self.options.uploadSuccess ) {
                self.options.uploadSuccess(file, resp);
            } else {
                showMessages(
                    ["\"" + file.name + "\" uploaded sucessfully to \"" + resp.location + "\""], "success");
            }
            return true;
        },

        _uploadError: function(file, resp) {
            var self = this;
            if( self.options.uploadError ) {
                self.options.uploadError(file, resp);
            } else {
                if( typeof resp === "string" ) {
                    showErrorMessages(
                 "Error: " + resp + "(while uploading '" + file.name + "')");
                } else {
                    showErrorMessages(resp);
                }
            }
        },

        _uploadProgress: function(file, progress) {
            var self = this;
            if( self.options.uploadProgress ) {
                self.options.uploadProgress(file, progress);
            }
            return true;
        },

        init: function(){
            var self = this;
            var dropzoneUrl = self.options.uploadUrl;
            if( !dropzoneUrl ) {
                showErrorMessages(
                    "instantiated djupload() with no uploadUrl specified.");
                throw new Error(
                    "instantiated djupload() with no uploadUrl specified.");
            }
            if( self.options.mediaPrefix !== ""
                && !self.options.mediaPrefix.match(/\/$/)){
                self.options.mediaPrefix += "/";
            }
            self.element.dropzone({
                paramName: self.options.uploadParamName,
                url: dropzoneUrl,
                maxFilesize: self.options.uploadMaxFileSize,
                clickable: self.options.uploadClickableZone,
                createImageThumbnails: false,
                previewTemplate: "<div></div>",
                init: function() {
                    this.on("sending", function(file, xhr, formData){
                        if( self.options.accessKey) {
                            formData.append("key", self.options.mediaPrefix + file.name);
                            formData.append("acl", self.options.acl);
                            formData.append("policy", self.options.policy);
                            formData.append("x-amz-algorithm", "AWS4-HMAC-SHA256");
                            formData.append("x-amz-credential",
                                            self.options.amzCredential);
                            formData.append("x-amz-date", self.options.amzDate);
                            formData.append("x-amz-security-token",
                                            self.options.securityToken);
                            formData.append("x-amz-signature",
                                            self.options.signature);
                            var ext = file.name.slice(
                                file.name.lastIndexOf('.')).toLowerCase();
                            if( ext === ".jpg" ) {
                                formData.append("Content-Type", "image/jpeg");
                            } else if( ext === ".png" ) {
                                formData.append("Content-Type", "image/png");
                            } else if( ext === ".mp4" ) {
                                formData.append("Content-Type", "video/mp4");
                            } else {
                                formData.append(
                                    "Content-Type", "binary/octet-stream");
                            }
                        } else {
                            formData.append(
                                "csrfmiddlewaretoken", self._csrfToken());
                        }
                        var data = self.element.data();
                        for( var key in data ) {
                            if( data.hasOwnProperty(key) ) {
                                formData.append(key, data[key]);
                            }
                        }
                    });

                    this.on("success", function(file, response){
                        if( self.options.accessKey) {
                            // With a direct upload to S3, we need to build
                            // a custom response with location url ourselves.
                            response = {
                                location: file.xhr.responseURL + self.options.mediaPrefix + file.name
                            };
                            // We will also call back a completion url
                            // on the server.
                            var completeUrl = self.element.attr(
                                "data-complete-url");
                            if( completeUrl ) {
                                $.extend(response, self.element.data());
                                delete response.djupload;
                                $.ajax({
                                    type: "POST",
                                    url: completeUrl,
                                    beforeSend: function(xhr) {
                                        xhr.setRequestHeader(
                                            "X-CSRFToken", self._csrfToken());
                                    },
                                    data: JSON.stringify(response),
                                    datatype: "json",
                                    contentType: "application/json; charset=utf-8",
                                    success: function(resp) {
                                        // Use ``response`` instead of ``resp``
                                        // to have consistent API.
                                        self._uploadSuccess(file, response);
                                    },
                                    error: function(resp) {
                                        self._uploadError(file, resp);
                                    }
                                });
                            } else {
                                self._uploadSuccess(file, response);
                            }
                        } else {
                            self._uploadSuccess(file, response);
                        }
                    });

                    this.on("error", function(file, message){
                        self._uploadError(file, message);
                    });

                    this.on("uploadprogress", function(file, progress){
                        self._uploadProgress(file, progress);
                    });
                }
            });
        }
    };

    $.fn.djupload = function(options) {
        var opts = $.extend( {}, $.fn.djupload.defaults, options );
        return this.each(function() {
            if (!$.data(this, "djupload")) {
                $.data(this, "djupload", new Djupload(this, opts));
            }
        });
    };

    $.fn.djupload.defaults = {
        // location
        uploadUrl: null,
        mediaPrefix: "",

        uploadZone: "body",
        uploadClickableZone: true,
        uploadParamName: "file",
        uploadMaxFileSize: 250,

        // Django upload
        csrfToken: null,

        // S3 direct upload
        accessKey: null,
        securityToken: null,
        acl: "private",
        policy: "",
        signature: null,
        amzCredential: null,
        amzDate: null,

        // callback
        uploadSuccess: null,
        uploadError: null,
        uploadProgress: null
    };

    Dropzone.autoDiscover = false;

})(jQuery);

