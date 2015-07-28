/* jshint multistr: true */

/* relies on:
    - jquery-ui.js
    - dropzone.js
*/

(function ($) {
    "use strict";

    var sidebarGallery = null;

    var sidebarHtml = "\
        <div id=\"sidebar-container\">\
            <div id=\"sidebar-gallery\">\
                <h1>Media</h1>\
                <input placeholder=\"Search...\" id=\"gallery-filter\" type=\"text\" class=\"form-control\">\
                <div id=\"media-container\">\
                    <div class=\"col-xs-12\">Drag and drop or click to upload Media</div>\
                    <div id=\"list-media\"></div>\
                </div>\
                <div id=\"media-info\" class=\"placeholder\">Click on an item to view more options</div>\
            </div>\
        </div>";

    function SidebarGallery(options){
        this.options = options;
        this.init();
        Dropzone.autoDiscover = false;
    }

    SidebarGallery.prototype = {
        init: function(){
            sidebarGallery = this;
            sidebarGallery.originalTags = [];
            sidebarGallery.selectedMediaLocation = "";
            sidebarGallery.currentInfo = "";
            sidebarGallery.selectedMedia = null;
            sidebarGallery.initSidebar();
            sidebarGallery.initDocument();
            sidebarGallery.initDropzone();
        },

        initSidebar: function(){
            $("body").append(sidebarHtml);
            $("body").append(sidebarGallery.options.toggle);
        },

        initDocument: function(){
            $("#sidebar-container").on("click", "#delete_media", sidebarGallery.deleteMedia);
            $("#sidebar-container").on("click", "#tag_media", sidebarGallery.tagMedia);
            $("#sidebar-container").on("click", "#preview_media", sidebarGallery.previewMedia);
            $("body").on("click", "#btn-toggle", sidebarGallery.toggleSidebar);
            $("#sidebar-container").on("keyup", "#gallery-filter", sidebarGallery.loadImage);
            $("#sidebar-container").on("click", "#add-tag", function(){
                var tags = $("#input-tag").val().replace(/\s+/g, "");
                tags = tags.split(",");
                if (tags !== sidebarGallery.originalTags){
                    $.ajax({
                        type: "PUT",
                        url: sidebarGallery.options.requestMediaUrl,
                        data: JSON.stringify({"items": [{"location": sidebarGallery.selectedMediaLocation}], "tags": tags}),
                        datatype: "json",
                        contentType: "application/json; charset=utf-8",
                        success: function(response){
                            $.each(response.results, function(index, element) {
                                $("[src=\"" + element.location + "\"]").attr("tags", element.tags);
                            });
                        }
                    });
                }
                $("#media-info").empty().append(sidebarGallery.currentInfo);
            });

            $("#sidebar-container").on("click", ".media-single-container", function(){
                sidebarGallery.initMediaInfo();
                $(".media-single-container").not($(this)).removeClass("active-media");
                if (!$(this).hasClass("active-media")){
                    sidebarGallery.selectedMedia = $(this).children(".clickable-menu");
                    $("#media-info").removeClass("placeholder").text("");
                    $(this).addClass("active-media");
                    $("#media-info").append("<div class=\"url_info\"><textarea style=\"width:98%\" rows=\"4\" readonly>" + sidebarGallery.selectedMedia.attr("src") + "</textarea></div>");
                    sidebarGallery.initMenuMedia(sidebarGallery.selectedMedia);

                }else{
                    $(this).removeClass("active-media");
                    sidebarGallery.selectedMedia = null;
                }
            });

            $("body").on("click", ".closeModal", function(event){
                event.preventDefault();
                $("#openModal").remove();
            });

            $(".droppable-image").droppable({
                drop: function( event, ui ) {
                    var droppable = $(this);
                    var source = ui.draggable.attr("src").toLowerCase();
                    if (droppable.prop("tagName") === "IMG"){
                        if (sidebarGallery.options.acceptedImages.some(function(v) { return source.indexOf(v) >= 0; })){
                            droppable.attr("src", ui.draggable.attr("src"));
                            $(ui.helper).remove();
                            sidebarGallery.saveDropMedia(droppable);
                        }else{
                            console.log("This placeholder accepts only: " + sidebarGallery.options.acceptedImages.join(", ") + " files.");
                        }
                    }else if (droppable.prop("tagName") === "VIDEO"){
                        if (sidebarGallery.options.acceptedVideos.some(function(v) { return source.indexOf(v) >= 0; })){
                            droppable.attr("src", ui.draggable.attr("src"));
                            $(ui.helper).remove();
                            sidebarGallery.saveDropMedia(droppable);
                        }else{
                            console.log("This placeholder accepts only: " + sidebarGallery.options.acceptedVideos.join(", ") + " files.");
                        }
                    }
              }
            });
        },

        initMenuMedia: function(item){
            var menu = "\
                <button id=\"tag_media\" location=\"" + item.attr("src") + "\" class=\"" + sidebarGallery.options.buttonClass + "\">Update tags</button>\
                <button id=\"delete_media\" location=\"" + item.attr("src") + "\" class=\"" + sidebarGallery.options.buttonClass + "\">Delete</button>";
            if (item.prop("tagName") === "VIDEO"){
                menu += "<button id=\"preview_media\" location=\"" + item.attr("src") + "\"  class=\"" + sidebarGallery.options.buttonClass + "\">Preview</button>";
            }
            $("#media-info").append(menu);
        },

        initMediaInfo: function(){
            $("#media-info").addClass("placeholder").text("Click on an item to view more options");
        },

        initDropzone: function(){
            var dropzoneUrl = sidebarGallery.options.requestMediaUrl;
            if (sidebarGallery.options.accessKey){
                dropzoneUrl = sidebarGallery.options.S3DirectUploadUrl;
            }

            var DocDropzone = new Dropzone("body", {
                paramName: "file",
                url: dropzoneUrl,
                maxFilesize: 50,
                parallelUploads: 2,
                clickable: false,
                createImageThumbnails: false
            });

            DocDropzone.on("sending", function(file, xhr, formData){
                if( sidebarGallery.options.accessKey) {
                    formData.append("key", sidebarGallery.options.mediaPrefix + file.name);
                    formData.append("policy", sidebarGallery.options.policy);
                    formData.append("x-amz-algorithm", "AWS4-HMAC-SHA256");
                    formData.append("x-amz-credential",
                        sidebarGallery.options.amzCredential);
                    formData.append("x-amz-date", sidebarGallery.options.amzDate);
                    formData.append("x-amz-security-token",
                        sidebarGallery.options.securityToken);
                    formData.append("x-amz-signature",
                        sidebarGallery.options.signature);
                } else {
                    formData.append("csrfmiddlewaretoken",
                        sidebarGallery.options.csrf_token);
                }
            });

            DocDropzone.on("success", function(file, response){
                var status = file.xhr.status;
                $(".progress-text").remove();
                $(".dz-preview").remove();
                var lastIndex = $("#list-media").children().last().children().attr("id");
                if (lastIndex){
                    lastIndex = parseInt(lastIndex.split("image_")[1]) + 1;
                }else{
                    lastIndex = 0;
                }
                if ([200, 201, 204].indexOf(status) >= 0){
                    if (sidebarGallery.options.accessKey){
                        sidebarGallery.loadImage();
                    }else{
                        sidebarGallery.addMediaItem(response, lastIndex);
                    }
                }
                if (!$("#sidebar-container").hasClass("active")){
                    sidebarGallery.openSidebar();
                }
            });
        },

        toggleSidebar: function(){
            if ($("#sidebar-container").hasClass("active")){
                sidebarGallery.closeSidebar();
            }else{
                sidebarGallery.openSidebar();
            }
        },

        openSidebar: function(){
            $("#btn-toggle").addClass("active");
            sidebarGallery.initResizeSidebar();
            $("#sidebar-container").addClass("active");
            sidebarGallery.loadImage();
        },

        closeSidebar: function(){
            $("#sidebar-container").removeClass("active").attr("style", "");
            $("#btn-toggle").removeClass("active").attr("style", "");
            $("#btn-toggle").draggable("destroy");
            $(".image-gallery").remove();
        },

        initResizeSidebar: function(){
            $("#btn-toggle").draggable({
                axis: "x",
                cursor: "move",
                containment: "window",
                drag: function(event, ui){
                    var viewWidth = $(window).width();
                    if (viewWidth - ui.position.left - $(ui.helper).outerWidth() >= 300){
                        $("#sidebar-container").css("right", "0px").css("width", viewWidth - ui.position.left - $(ui.helper).outerWidth());
                    }else{
                        $("#btn-toggle").css("left", viewWidth - 300 - $(ui.helper).outerWidth());
                        return false;
                    }
                },
                stop: function(event, ui){
                    var viewWidth = $(window).width();
                    if (viewWidth - ui.position.left - $(ui.helper).outerWidth() >= 300){
                        $("#sidebar-container").css("right", "0px").css("width", viewWidth - ui.position.left - $(ui.helper).outerWidth());
                    }else{
                        $("#sidebar-container").css("right", "0px").css("width", 300);
                    }
                    $( event.toElement ).one("click", function(e){ e.stopImmediatePropagation(); } );
                }
            });
        },

        loadImage: function(){
            var search = "";
            if ($("#gallery-filter").val() !== ""){
                search = $("#gallery-filter").val();
            }
            $("#list-media").empty();
            $.ajax({
                method: "GET",
                url: sidebarGallery.options.requestMediaUrl + "?q=" + search,
                success: function(data){
                    $.each(data.results, function(index, file){
                        sidebarGallery.addMediaItem(file, index);
                    });
                }
            });
        },

        addMediaItem: function(file, index){
            var mediaItem = "";
            if (file.location.indexOf(".mp4") > 0){
                mediaItem = "<div class=\"media-single-container\"><video id=\"image_ " + index + "\" class=\"image clickable-menu image_media\" src=\"" + file.location + "\" tags=\"" + file.tags + "\"></video></div>";
            }else{
                mediaItem = "<div class=\"media-single-container\"><img id=\"image_" + index + "\" class=\"image clickable-menu image_media\" src=\"" + file.location + "\" tags=\"" + file.tags + "\"></div>";
            }
            $("#list-media").append(mediaItem);
            $("#image_" + index).draggable({
                helper: "clone",
                revert: true,
                appendTo: "body",
                zIndex: 10000,
                start: function(event, ui) {
                    ui.helper.css({
                        // height: 50,
                        width: 50
                    });
                }
            });
        },

        tagMedia: function(event){
            event.preventDefault();

            sidebarGallery.orginalTags = sidebarGallery.selectedMedia.attr("tags").split(",");
            sidebarGallery.selectedMediaLocation = sidebarGallery.selectedMedia.attr("src");

            sidebarGallery.currentInfo = $("#media-info").html();
            $("#media-info").empty().append("<h4>Update media tag</h4><input id=\"input-tag\" type=\"text\" value=\"" + sidebarGallery.orginalTags.join(", ") + "\" placeholder=\"Please enter tag.\" class=\"form-control\"><button id=\"add-tag\" class=\"" + sidebarGallery.options.buttonClass + "\">Update tags</button>");
            $("#input-tag").focus();

        },

        deleteMedia: function(event){
            event.preventDefault();

            $.ajax({
                method: "DELETE",
                url: sidebarGallery.options.requestMediaUrl,
                data: {"location": sidebarGallery.selectedMedia.attr("src")},
                success: function(){
                    $("[src=\"" + sidebarGallery.selectedMedia.attr("src") + "\"]").parent(".media-single-container").remove();
                }
            });
            $("#media-info").empty();
        },

        previewMedia: function(event){
            event.preventDefault();
            var modal = "<div id=\"openModal\" class=\"modalDialog\">\
                    <div>\
                        <a href=\"#close\" title=\"Close\" class=\"closeModal\">X</a>\
                        <video src=\"" + sidebarGallery.selectedMedia.attr("src") + "\" width=\"500px\" controls></video>\
                    </div>\
                </div>";
            $("body").append(modal);
        },

        saveDropMedia: function(element){
            var idElement = element.attr("id");
            var data = {text: element.attr("src")};
            $.ajax({
                method: "PUT",
                async: false,
                url: sidebarGallery.options.saveDropMediaUrl + idElement + "/",
                data: data,
                success: function(data){
                    console.log("saved");
                }
            });
        }

    };

    $.sidebargallery = function(options) {
        var opts = $.extend( {}, $.sidebargallery.defaults, options );
        return new SidebarGallery(opts);
    };

    $.sidebargallery.defaults = {
        saveDropMediaUrl: null, // Url to send request to server
        requestMediaUrl: "",
        acceptedImages: [".jpg", ".png", ".gif"],
        acceptedVideos: [".mp4"],
        csrfToken: "",
        S3DirectUploadUrl: null,
        accessKey: null,
        mediaPrefix: null,
        securityToken: null,
        policy: "",
        signature: null,
        amzCredential: null,
        amzDate: null,
        toggle: "<button class=\"btn btn-default\" id=\"btn-toggle\">Gallery</button>",
        buttonClass: ""
    };

})(jQuery);
