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
    maxFilesizeUpload :                 default: 50, type: Integer
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

    var djGallery = null;

    function Djgallery(options){
        this.options = options;
        this.init();
        Dropzone.autoDiscover = false;
    }

    Djgallery.prototype = {
        init: function(){
            djGallery = this;
            djGallery.originalTags = [];
            djGallery.selectedMediaLocation = "";
            djGallery.currentInfo = "";
            djGallery.selectedMedia = null;
            djGallery.initGallery();
            djGallery.initDocument();
            djGallery.initDropzone();
            djGallery.initMediaInfo();
            if (djGallery.options.startLoad){
                djGallery.loadImage();
            }
        },

        initGallery: function(){
            if ($(".dj-gallery").length === 0){
                $("body").append(djGallery.options.galleryTemplate);
            }
        },

        initDocument: function(){
            $(".dj-gallery").on("click", ".dj-gallery-delete-item", djGallery.deleteMedia);
            $(".dj-gallery").on("click", ".dj-gallery-preview-item", djGallery.previewMedia);
            $(".dj-gallery").on("keyup", ".dj-gallery-filter", djGallery.loadImage);
            $(".dj-gallery").on("click", ".dj-gallery-tag-item", djGallery.tagMedia);
            $(".dj-gallery").on("click", ".dj-gallery-item-container", djGallery.selectMedia);

            $("body").on("click", ".closeModal", function(event){
                event.preventDefault();
                $("#openModal").remove();
            });

            $(djGallery.options.mediaPlaceholder).droppable({
                drop: function( event, ui ) {
                    var droppable = $(this);
                    var source = ui.draggable.attr("src").toLowerCase();
                    if (droppable.prop("tagName") === "IMG"){
                        if (djGallery.options.acceptedImages.some(function(v) { return source.indexOf(v) >= 0; })){
                            droppable.attr("src", ui.draggable.attr("src"));
                            $(ui.helper).remove();
                            djGallery.saveDroppedMedia(droppable);
                        }else{
                            djGallery.options.galleryMessage("This placeholder accepts only: " + djGallery.options.acceptedImages.join(", ") + " files.");
                        }
                    }else if (droppable.prop("tagName") === "VIDEO"){
                        if (djGallery.options.acceptedVideos.some(function(v) { return source.indexOf(v) >= 0; })){
                            droppable.attr("src", ui.draggable.attr("src"));
                            $(ui.helper).remove();
                            djGallery.saveDroppedMedia(droppable);
                        }else{
                            djGallery.options.galleryMessage("This placeholder accepts only: " + djGallery.options.acceptedVideos.join(", ") + " files.");
                        }
                    }
                }
            });
        },

        initMenuMedia: function(){
            $(".dj-gallery-info-item").html(djGallery.options.galleryItemOptionsTemplate);
            $("[data-dj-gallery-media-src]").attr("src", djGallery.selectedMedia.attr("src"));
            $("[data-dj-gallery-media-location]").attr("location", djGallery.selectedMedia.attr("src"));
            $("[data-dj-gallery-media-url]").val(djGallery.selectedMedia.attr("src"));
            $("[data-dj-gallery-media-tag]").val(djGallery.orginalTags.join(", "));
        },

        initMediaInfo: function(){
            $(".dj-gallery-info-item").text("Click on an item to view more options");
        },

        initDropzone: function(){
            var dropzoneUrl = djGallery.options.mediaUrl;
            if (djGallery.options.accessKey){
                dropzoneUrl = djGallery.options.S3DirectUploadUrl;
            }

            if (!dropzoneUrl){
                djGallery.options.galleryMessage("No media URL. Provide either mediaUrl or S3DirectUploadUrl", "error");
                throw new Error("No media URL. Provide either mediaUrl or S3DirectUploadUrl");
            }

            var djDropzone = new Dropzone("body", {
                paramName: djGallery.options.paramNameUpload,
                url: dropzoneUrl,
                maxFilesize: djGallery.options.maxFilesizeUpload,
                parallelUploads: 2,
                clickable: true,
                createImageThumbnails: false
            });

            djDropzone.on("sending", function(file, xhr, formData){
                if( djGallery.options.accessKey) {
                    if (!djGallery.options.mediaPrefix.match(/\/$/)){
                        djGallery.options.mediaPrefix += "/";
                    }
                    formData.append("key", djGallery.options.mediaPrefix + file.name);
                    formData.append("policy", djGallery.options.policy);
                    formData.append("x-amz-algorithm", "AWS4-HMAC-SHA256");
                    formData.append("x-amz-credential",
                        djGallery.options.amzCredential);
                    formData.append("x-amz-date", djGallery.options.amzDate);
                    formData.append("x-amz-security-token",
                        djGallery.options.securityToken);
                    formData.append("x-amz-signature",
                        djGallery.options.signature);
                } else {
                    formData.append("csrfmiddlewaretoken",
                        djGallery.options.csrfToken);
                }
            });

            djDropzone.on("success", function(file, response){
                var status = file.xhr.status;
                $(".dz-preview").remove();
                var lastIndex = $(".dj-gallery-items").children().last().children().attr("id");
                if (lastIndex){
                    lastIndex = parseInt(lastIndex.split("image_")[1]) + 1;
                }else{
                    lastIndex = 0;
                }
                if ([201, 204].indexOf(status) >= 0){
                    if (djGallery.options.accessKey){
                        djGallery.loadImage();
                    }else{
                        djGallery.addMediaItem(response, lastIndex);
                    }
                    djGallery.options.galleryMessage("Media correctly uploaded.");
                }else if (status === 200){
                    djGallery.options.galleryMessage(response.message);
                }
            });

            djDropzone.on("uploadprogress", function(file, progress){
                djGallery.options.itemUploadProgress(progress);
            });
        },

        loadImage: function(){
            var search = "";
            if ($(".dj-gallery-filter").val() !== ""){
                search = $(".dj-gallery-filter").val();
            }
            $(".dj-gallery-items").empty();
            $.ajax({
                method: "GET",
                url: djGallery.options.mediaUrl + "?q=" + search,
                success: function(data){
                    $.each(data.results, function(index, file){
                        djGallery.addMediaItem(file, index);
                    });
                }
            });
        },

        addMediaItem: function(file, index){
            var mediaItem = "";
            if (file.location.toLowerCase().indexOf(".mp4") > 0){
                mediaItem = "<div class=\"dj-gallery-item-container " + djGallery.options.mediaClass + " \"><video id=\"image_" + index + "\" class=\"image dj-gallery-item image_media\" src=\"" + file.location + "\" tags=\"" + file.tags + "\"></video></div>";
            }else{
                mediaItem = "<div class=\"dj-gallery-item-container " + djGallery.options.mediaClass + " \"><img id=\"image_" + index + "\" class=\"image dj-gallery-item image_media\" src=\"" + file.location + "\" tags=\"" + file.tags + "\"></div>";
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

        selectMedia: function(){
            djGallery.initMediaInfo();

            $(".dj-gallery-item-container").not($(this)).removeClass(djGallery.options.selectedMediaClass);

            if (!$(this).hasClass(djGallery.options.selectedMediaClass)){
                djGallery.selectedMedia = $(this).children(".dj-gallery-item");
                $(this).addClass(djGallery.options.selectedMediaClass);
                djGallery.orginalTags = djGallery.selectedMedia.attr("tags").split(",");
                djGallery.selectedMediaLocation = djGallery.selectedMedia.attr("src");
                djGallery.initMenuMedia();
            }else{
                $(this).removeClass(djGallery.options.selectedMediaClass);
                djGallery.selectedMedia = null;
            }
        },

        deleteMedia: function(event){
            event.preventDefault();
            $.ajax({
                method: "DELETE",
                url: djGallery.options.mediaUrl,
                data: JSON.stringify({"items": [{"location": djGallery.selectedMedia.attr("src")}]}),
                datatype: "json",
                contentType: "application/json; charset=utf-8",
                success: function(){
                    $("[src=\"" + djGallery.selectedMedia.attr("src") + "\"]").parent(".dj-gallery-item-container").remove();
                    $(".dj-gallery-info-item").empty();
                    djGallery.options.galleryMessage("Media correctly deleted.");
                }
            });
        },

        tagMedia: function(){
            var tags = $(".dj-gallery-tag-input").val().replace(/\s+/g, "");
            tags = tags.split(",");
            if (tags !== djGallery.originalTags){
                $.ajax({
                    type: "PUT",
                    url: djGallery.options.mediaUrl,
                    data: JSON.stringify({"items": [{"location": djGallery.selectedMediaLocation}], "tags": tags}),
                    datatype: "json",
                    contentType: "application/json; charset=utf-8",
                    success: function(response){
                        $.each(response.results, function(index, element) {
                            $("[src=\"" + element.location + "\"]").attr("tags", element.tags);
                        });
                        djGallery.options.galleryMessage("Tags correctly updated.");
                    }
                });
            }
        },

        previewMedia: function(event){
            event.preventDefault();
            var modal = "<div id=\"openModal\" class=\"modalDialog\">\n<div>\n<a href=\"#close\" title=\"Close\" class=\"closeModal\">X</a>\n<video src=\"" + djGallery.selectedMedia.attr("src") + "\" width=\"500px\" controls></video>\n</div>\n</div>";
            $("body").append(modal);
        },

        saveDroppedMedia: function(element){
            var idElement = element.attr("id");
            var data = {text: element.attr("src")};
            $.ajax({
                method: "PUT",
                async: false,
                url: djGallery.options.saveDroppedMediaUrl + idElement + "/",
                data: data,
                success: function(response){
                    djGallery.options.droppedMediaCallback(response);
                }
            });
        }
    };

    $.djgallery = function(options) {
        var opts = $.extend( {}, $.djgallery.defaults, options );
        return new Djgallery(opts);
    };

    $.djgallery.defaults = {

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
        acceptedImages: [".jpg", ".png", ".gif"],
        acceptedVideos: [".mp4"],
        maxFilesizeUpload: 50,
        paramNameUpload: "file",

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

})(jQuery);
