/* jshint multistr: true */

/* relies on:
    - jquery-ui.js
    - dropzone.js

Media request:

GET mediaUrl:

    - request

    - response: 200 OK
    {
        ...,
        "results":[
            {"location": "/media/item/url1.jpg", "tags" : []},
            {"location": "/media/item/url2.jpg", "tags" : ["html", "django"]}
        ],
        ...
    }

POST mediaUrl:
    - request: {<paramNameUpload>: uploaded_file}

    - response: 201 CREATED
    {"location":"/media/item/url1.jpg","tags":[]}


PUT mediaUrl:

    - request: {items: [{location: "/media/item/url1.jpg"}, {location: "/media/item/url2.jpg"}], tags: ["tag1", "tag2"]}

    - response: 200 OK
    {
        ...,
        "results":[
            {"location": "/media/item/url1.jpg", "tags" : ["tag1", "tag2"]},
            {"location": "/media/item/url2.jpg", "tags" : ["tag1", "tag2"]}
        ],
        ...
    }

DELETE mediaUrl 200 OK
    - request: {items: [{location: "/media/item/url1.jpg"}, {location: "/media/item/url2.jpg"}]}
    - response: 200 OK

Options:

    mediaUrl :                          default: null, type: String, url to get, post, put and delete media from backend
    csrfToken :                         default: null, type: String, security token

    // AWS S3 Direct upload settings
    S3DirectUploadUrl :                 default: null, type: String, A S3 url
    mediaPrefix :                       default: null, type: String, S3 folder ex: media/
    accessKey :                         default: null, type: String, S3 Temporary credentials
    securityToken :                     default: null, type: String, S3 Temporary credentials
    policy :                            default: null, type: String, S3 Temporary credentials
    signature :                         default: null, type: String, S3 Temporary credentials
    amzCredential :                     default: null, type: String, S3 Temporary credentials
    amzDate :                           default: null, type: String, S3 Temporary credentials

    // Custom gallery callback and templates
    paramNameUpload :                   default: "file", type: String, Custom param name for uploaded file
    maxFilesizeUpload :                 default: 256, type: Integer
    acceptedImages :                    default: [".jpg", ".png", ".gif"], type: Array
    acceptedVideos :                    default: [".mp4"], type: Array
    buttonClass :                       type: String
    galleryItemOptionsTemplate :        type: String, template used when a media item is selected
    selectedMediaClass :                type: String, class when a media item is selected
    startLoad :                         type: Boolean, if true load image on document ready
    itemUploadProgress :                type:function, params:progress, return the progress on upload
    galleryMessage :                    type:function, params:message, notification of the gallery

    // Custom droppable media item and callback
    mediaPlaceholder :                  type:string, seclector to init droppable placeholder
    saveDroppedMediaUrl :               type:string, Url to send request when media is dropped in placeholder
    droppedMediaCallback :              type:function, params:response, Callback on succeeded dropped media item

*/

(function ($) {
    "use strict";

    function Djgallery(el, options){
        this.element = $(el);
        this.options = options;
        this.init();
    }

    Djgallery.prototype = {
        init: function(){
            var self = this;
            self.originalTags = [];
            self.selectedMediaLocation = "";
            self.currentInfo = "";
            self.selectedMedia = null;
            self.initGallery();
            self.initDocument();
            self.initDropzone();
            self.initMediaInfo();
            if (self.options.startLoad){
                self.loadImage();
            }
        },

        initGallery: function(){
            var self = this;
            if ($(".dj-gallery").length === 0){
                $("body").append(self.options.galleryTemplate);
            }
        },

        initDocument: function(){
            var self = this;
            $(".dj-gallery").on("click", ".dj-gallery-delete-item",
                function(event) { self.deleteMedia(event); });
            $(".dj-gallery").on("click", ".dj-gallery-preview-item",
                function(event) { self.previewMedia(event); });
            $(".dj-gallery").on("keyup", ".dj-gallery-filter",
                function(event) { self.loadImage(); });
            $(".dj-gallery").on("click", ".dj-gallery-tag-item",
                function(event) { self.tagMedia(); });
            $(".dj-gallery").on("click", ".dj-gallery-item-container",
                function(event) { self.selectMedia($(this)); });
            $("body").on("click", ".closeModal", function(event){
                event.preventDefault();
                $("#openModal").remove();
            });

            $(self.options.mediaPlaceholder).droppable({
                drop: function( event, ui ) {
                    var droppable = $(this);
                    var source = ui.draggable.attr("src").toLowerCase();
                    if (droppable.prop("tagName") === "IMG"){
                        if (self.options.acceptedImages.some(function(v) { return source.toLowerCase().indexOf(v) >= 0; })){
                            droppable.attr("src", ui.draggable.attr("src"));
                            $(ui.helper).remove();
                            self.saveDroppedMedia(droppable);
                        }else{
                            self.options.galleryMessage("This placeholder accepts only: " + self.options.acceptedImages.join(", ") + " files.");
                        }
                    }else if (droppable.prop("tagName") === "VIDEO"){
                        if (self.options.acceptedVideos.some(function(v) { return source.toLowerCase().indexOf(v) >= 0; })){
                            droppable.attr("src", ui.draggable.attr("src"));
                            $(ui.helper).remove();
                            self.saveDroppedMedia(droppable);
                        }else{
                            self.options.galleryMessage("This placeholder accepts only: " + self.options.acceptedVideos.join(", ") + " files.");
                        }
                    }
                }
            });
        },

        initMenuMedia: function(){
            var self = this;
            $(".dj-gallery-info-item").html(self.options.galleryItemOptionsTemplate);
            $("[data-dj-gallery-media-src]").attr("src", self.selectedMedia.attr("src"));
            $("[data-dj-gallery-media-location]").attr("location", self.selectedMedia.attr("src"));
            $("[data-dj-gallery-media-url]").val(self.selectedMedia.attr("src"));
            $("[data-dj-gallery-media-tag]").val(self.orginalTags.join(", "));
        },

        initMediaInfo: function(){
            var self = this;
            $(".dj-gallery-info-item").text("Click on an item to view more options");
        },

        initDropzone: function(){
            var self = this;
            var dropzoneUrl = self.options.mediaUrl;
            if (self.options.accessKey){
                dropzoneUrl = self.options.S3DirectUploadUrl;
            }
            self.element.djupload({
                uploadUrl: dropzoneUrl,
                csrfToken: self.options.csrfToken,
                uploadZone: "body",
                uploadClickableZone: self.options.clickableArea,
                uploadParamName: "file",

                // S3 direct upload
                accessKey: self.options.accessKey,
                mediaPrefix: self.options.mediaPrefix,
                securityToken: self.options.securityToken,
                policy: self.options.policy,
                signature: self.options.signature,
                amzCredential: self.options.amzCredential,
                amzDate: self.options.amzDate,

                // callback
                uploadSuccess: function(file, response){
                    var status = file.xhr.status;
                    $(".dz-preview").remove();
                    var lastIndex = $(".dj-gallery-items").children().last().children().attr("id");
                    if (lastIndex){
                        lastIndex = parseInt(lastIndex.split("image_")[1]) + 1;
                    }else{
                        lastIndex = 0;
                    }
                    if ([201, 204].indexOf(status) >= 0){
                        if (self.options.accessKey){
                            self.loadImage();
                        }else{
                            self.addMediaItem(response, lastIndex);
                        }
                        self.options.galleryMessage("Media correctly uploaded.");
                    }else if (status === 200){
                        self.options.galleryMessage(response.message);
                    }
                },
                uploadError: function(file, message){
                    self.options.galleryMessage(message, "error");
                },
                uploadProgress: function(file, progress){
                    self.options.itemUploadProgress(progress);
                }
            });
        },

        loadImage: function(){
            var self = this;
            var search = "";
            if ($(".dj-gallery-filter").val() !== ""){
                search = $(".dj-gallery-filter").val();
            }
            $(".dj-gallery-items").empty();
            $.ajax({
                method: "GET",
                url: self.options.mediaUrl + "?q=" + search,
                datatype: "json",
                contentType: "application/json; charset=utf-8",
                success: function(data){
                    $(".dj-gallery-items").empty();
                    $.each(data.results, function(index, file){
                        self.addMediaItem(file, index);
                    });
                }
            });
        },

        addMediaItem: function(file, index){
            var self = this;
            var mediaItem = "";
            if (file.location.toLowerCase().indexOf(".mp4") > 0){
                mediaItem = "<div class=\"dj-gallery-item-container " + self.options.mediaClass + " \"><video id=\"image_" + index + "\" class=\"image dj-gallery-item image_media\" src=\"" + file.location + "\" tags=\"" + file.tags + "\"></video></div>";
            }else{
                mediaItem = "<div class=\"dj-gallery-item-container " + self.options.mediaClass + " \"><img id=\"image_" + index + "\" class=\"image dj-gallery-item image_media\" src=\"" + file.location + "\" tags=\"" + file.tags + "\"></div>";
            }
            $(".dj-gallery-items").prepend(mediaItem);
            $("#image_" + index).draggable({
                helper: "clone",
                revert: true,
                appendTo: "body",
                zIndex: 1000000,
                start: function(event, ui) {
                    ui.helper.css({
                        width: 65
                    });
                }
            });
        },

        selectMedia: function(item) {
            var self = this;
            self.initMediaInfo();

            $(".dj-gallery-item-container").not(item).removeClass(self.options.selectedMediaClass);
            if (!item.hasClass(self.options.selectedMediaClass)){
                self.selectedMedia = item.children(".dj-gallery-item");
                item.addClass(self.options.selectedMediaClass);
                self.orginalTags = self.selectedMedia.attr("tags").split(",");
                self.selectedMediaLocation = self.selectedMedia.attr("src");
                self.initMenuMedia();
            }else{
                item.removeClass(self.options.selectedMediaClass);
                self.selectedMedia = null;
            }
        },

        deleteMedia: function(event){
            var self = this;
            event.preventDefault();
            $.ajax({
                method: "DELETE",
                url: self.options.mediaUrl,
                data: JSON.stringify({"items": [{"location": self.selectedMedia.attr("src")}]}),
                datatype: "json",
                contentType: "application/json; charset=utf-8",
                success: function(){
                    $("[src=\"" + self.selectedMedia.attr("src") + "\"]").parent(".dj-gallery-item-container").remove();
                    $(".dj-gallery-info-item").empty();
                    self.options.galleryMessage("Media correctly deleted.");
                }
            });
        },

        tagMedia: function(){
            var self = this;
            var tags = $(".dj-gallery-tag-input").val().replace(/\s+/g, "");
            tags = tags.split(",");
            if (tags !== self.originalTags){
                $.ajax({
                    type: "PUT",
                    url: self.options.mediaUrl,
                    data: JSON.stringify({"items": [{"location": self.selectedMediaLocation}], "tags": tags}),
                    datatype: "json",
                    contentType: "application/json; charset=utf-8",
                    success: function(response){
                        $.each(response.results, function(index, element) {
                            $("[src=\"" + element.location + "\"]").attr("tags", element.tags);
                        });
                        self.options.galleryMessage("Tags correctly updated.");
                    }
                });
            }
        },

        previewMedia: function(event){
            var self = this;
            event.preventDefault();
            var src = self.selectedMedia.attr("src");
            var type = "image";
            if (self.options.acceptedVideos.some(function(v) { return src.toLowerCase().indexOf(v) >= 0; })){
                type = "video";
            }
            self.options.previewMediaItem(self.selectedMedia.attr("src"), type);
        },

        saveDroppedMedia: function(element){
            var self = this;
            var idElement = element.attr("id");
            var data = {slug: idElement, text: element.attr("src")};
            $.ajax({
                method: "PUT",
                async: false,
                url: self.options.saveDroppedMediaUrl + idElement + "/",
                data: data,
                success: function(response){
                    self.options.droppedMediaCallback(response);
                }
            });
        }
    };

    $.fn.djgallery = function(options) {
        var opts = $.extend( {}, $.fn.djgallery.defaults, options );
        return new Djgallery($(this), opts);
    };

    $.fn.djgallery.defaults = {

        // Djaodjin gallery required options
        mediaUrl: null, // Url to get list of media and upload, update and delete a media item
        csrfToken: "", //

        // Customize djaodjin gallery.
        buttonClass: "",
        galleryTemplate: "<div class=\"dj-gallery\">\n  <div class=\"sidebar-gallery\">\n    <h1>Media</h1>\n    <input placeholder=\"Search...\" class=\"dj-gallery-filter\" type=\"text\" >\n    <div class=\"dj-gallery-items\">\n    </div>\n    <div class=\"dj-gallery-info-item\"></div>\n  </div>\n</div>",
        galleryItemOptionsTemplate: "<textarea rows=\"4\" style=\"width:100%;\" readonly data-dj-gallery-media-url></textarea>\n<button data-dj-gallery-media-location class=\"dj-gallery-delete-item\">Delete</button>\n<button data-dj-gallery-media-location class=\"dj-gallery-preview-item\">Preview</button>\n<br>\n<input data-dj-gallery-media-tag class=\"dj-gallery-tag-input\" type=\"text\" placeholder=\"Please enter tag.\"><button class=\"dj-gallery-tag-item\">Update tags</button>",
        mediaClass: "",
        selectedMediaClass: "dj-gallery-active-item",
        startLoad: true,
        itemUploadProgress: function(progress){ return true; },
        galleryMessage: function(message, type){ return true; },
        previewMediaItem: function(src){ return true; },
        acceptedImages: [".jpg", ".png", ".gif"],
        acceptedVideos: [".mp4"],
        maxFilesizeUpload: 256,
        paramNameUpload: "file",
        clickableArea: false,

        // S3 direct upload
        S3DirectUploadUrl: null,
        accessKey: null,
        mediaPrefix: null,
        securityToken: null,
        policy: "",
        signature: null,
        amzCredential: null,
        amzDate: null,


        // Custom droppable media item and callback
        mediaPlaceholder: ".droppable-image",
        saveDroppedMediaUrl: null,
        droppedMediaCallback: function(reponse) { return true; }
    };

    Dropzone.autoDiscover = false;

})(jQuery);
