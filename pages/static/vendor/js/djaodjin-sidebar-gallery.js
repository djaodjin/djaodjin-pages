/* jshint multistr: true */

/* relies on:
    - jquery-ui.js
    - dropzone.js
*/
(function ($) {

    $(document).on('click', '.closeModal', function(event){
        event.preventDefault();
        $('#openModal').remove();
    });

    var modalPreview = function(url){
        var modal = '<div id="openModal" class="modalDialog">\
                    <div>\
                        <a href="#close" title="Close" class="closeModal">X</a>\
                        <video src="'+ url +'" width="500px" controls></video>\
                    </div>\
                </div>';
        return modal;
    };

    var singleMedia = function(file, index){
        var single_media = '';
        if (file.file_src.indexOf('.mp4') > 0){
            single_media = '<div class="media-single-container"><video data-id="'+ file.sha1 + '" id="image_'+ index + '" class="image  clickable-menu image_media" src="'+ file.file_src +'" style="max-height:80%;max-width:80%;"></video></div>';
        }else{
            single_media = '<div class="media-single-container"><img data-id="'+ file.sha1 + '" id="image_'+ index + '" class="image  clickable-menu image_media" src="'+ file.file_src +'" style="max-height:80%;max-width:80%;"></div>';
        }
        return single_media;
    };

    var sidebar = '\
        <div id="sidebar-container" class="">\
            <div id="sidebar-gallery">\
                <h1 class="">Media</h1>\
                <input placeholder="Search..." id="gallery-filter" type="text" class="form-control">\
                <div id="media-container">\
                    <div class="col-xs-12">Drag and drop or click to upload Media</div>\
                    <div id="list-media"></div>\
                </div>\
                <div id="media-info" class="placeholder">Click on an item to view more options</div>\
            </div>\
        </div>';

    var sidebar_size = 200;
    var loaded = false;
    var initialized = false;
    var id= null;
    var toggle_button = null;
    var count = 0;

    var modal = '<div class="modal fade" id="myModal" tabindex="-1" role="dialog" aria-labelledby="myModalLabel" aria-hidden="true">\
          <div class="modal-dialog">\
            <div class="modal-content">\
              <div class="modal-header">\
                <button type="button" class="close" data-dismiss="modal"><span aria-hidden="true">&times;</span><span class="sr-only">Close</span></button>\
                <h4 class="modal-title" id="myModalLabel">Modal title</h4>\
              </div>\
              <div class="modal-body">\
                <video src="" id="modal-video" controls style="width:100%" preload="auto"></video>\
              </div>\
              <div class="modal-footer">\
                <button type="button" class="btn btn-default" data-dismiss="modal">Close</button>\
                <button type="button" class="btn btn-primary">Save changes</button>\
              </div>\
            </div>\
          </div>\
        </div>';

    function SidebarGallery(options){
        this.options = options;
        this._init();
        Dropzone.autoDiscover = false;
    }

    function notify_user(descr, level){
        $('body').prepend('<div class="notify-user-label '+ level +'-label">'+ descr + '</div>');
        setTimeout(function(){
            $('.notify-user-label').remove();
        }, 5000);
    }

    function update_progress_info(url) {
        $.getJSON(url, {'X-Progress-ID': id}, function(data, status){
            if(data){
                $('#progress-span').text((data.uploaded /data.lenght)*100);
            }
            else{
                $('#progress-span').text(100);
                return false;
            }
            setTimeout(update_progress_info(url), 100);
        });
    }

    SidebarGallery.prototype = {

        _init: function(){
            _this = this;
            $('body').append(_this.options.toggle).append(sidebar);
            $(document).on('click','#btn-toggle', _this._toggle_sidebar);
            $(document).on('keyup', '#gallery-filter', _this.filterImage);
            if (_this.options.url_progress){
                $(document).on('start_upload', function(){
                    setTimeout(update_progress_info(_this.options.url_progress), 20);
                });
            }
            $(document).on('click', '#delete_media', _this.deleteMedia);
            $(document).on('click', '#tag_media', _this.tagMedia);
            $(document).on('click', '#preview_media', _this.previewMedia);

            $(document).on('editInputVisible', function(){
                $('#input_editor').droppable({
                    drop: function(event, ui){
                        var droppable = $(this);
                        var draggable = ui.draggable;
                        droppable.focus();
                        droppable.selection('insert',{text:'![Alt text]('+ draggable.attr('src') +')' ,mode:'before'});
                        $(ui.helper).remove();
                        $('#input_editor').trigger('autosize.resize');
                    }
                });
            });

            $('.droppable-image').droppable({
                drop: function( event, ui ) {
                    var droppable = $(this);
                    if (droppable.prop("tagName") == 'IMG'){
                        if (ui.draggable.attr('src').indexOf(".png") > 0 || ui.draggable.attr('src').indexOf(".jpg") > 0){
                            droppable.attr('src', ui.draggable.attr('src'));
                            $(ui.helper).remove();
                            _this.saveImage(droppable);
                        }else{
                            notify_user("You can't put other file than image in this place", 'error');
                        }
                    }else if (droppable.prop("tagName") == 'VIDEO'){
                        if (ui.draggable.attr('src').indexOf(".mp4") > 0){
                            droppable.attr('src', ui.draggable.attr('src'));
                            $(ui.helper).remove();
                            _this.saveImage(droppable);
                        }else{
                            notify_user("You can't put other file than video in this place", 'error');
                        }
                    }
              }
            });

            var DocDropzone = new Dropzone('#media-container', { // Make the whole body a dropzone
                paramName: 'file',
                url: _this.options.base_media_url,
                maxFilesize: 50,
                parallelUploads: 2,
                clickable: true,
                createImageThumbnails:false,
            });

            DocDropzone.on("processing", function(file){
                id = (new Date()).getTime();
                if (_this.options.url_progress){
                    this.options.url = _this.options.base_media_url + '?X-Progress-ID=' +id;
                }
            });

            DocDropzone.on("cancel", function(file){
                $('.progress-text').remove();
            });

            DocDropzone.on("sending", function(file, xhr, formData){
                formData.append('csrfmiddlewaretoken', _this.options.csrf_token);
                $('#media-container').append('<div class="col-md-12 padding-top-img progress-text text-center">Upload in progress<br><p><span id="progress-span">0</span>%</p>Please wait...</div>');
                $.event.trigger({
                  type:    "start_upload",
                  message: "myTrigger fired.",
                  time:    new Date()
                });
            });

            DocDropzone.on("dragover", function(event){
                if (count !== 0){
                    $('body').prepend('<div class="notify-user-label info-label">Release your file to upload it</div>');
                    count = 1;
                }
            });

            DocDropzone.on("drop", function(event){
                if ($('.url_info').length){
                    $('.url_info').remove();
                }
                $('.notify-user-label').remove();
                count = 0;
            });

            DocDropzone.on("dragleave", function(event){
                $('.notify-user-label').remove();
                count = 0;
            });

            DocDropzone.on("error", function(data, response){
                $('#media-container').append('<div class="col-md-12 padding-top-img alert">' + response.message + '</div>');
                setTimeout(function() {
                    $('.alert').remove();
                }, 3000);
            });

            DocDropzone.on("success", function(file, response){
                var status = file.xhr.status;
                $('.progress-text').remove();
                $('.dz-preview').remove();
                var last_index = $('#list-media').children().last().children().attr('id');
                if (last_index){
                    last_index = parseInt(last_index.split('image_')[1]) + 1;
                }else{
                    last_index = 0;
                }
                if (status == 201){
                    $('#list-media').prepend(singleMedia(response, last_index));

                    $('#image_' + last_index).draggable({
                        helper: 'clone',
                        revert: true,
                        appendTo: "body",
                        start: function() {
                            $(".ui-draggable").not(this).css({
                                width: 50
                            });
                        },
                    });
                    _this.makemenu();
                    var descr = "We're processing your uploaded file. You can start use it by using the sample in your gallery.";
                    notify_user(descr, 'info');
                }else{
                    notify_user(response.message, 'error');
                }
                if (!$('#sidebar-gallery').hasClass('active')){
                    _this._open_sidebar();
                }
            });
        },

        deleteMedia: function(event){
            event.preventDefault();
            var $this_element = $(this);
            $.ajax({
                method: 'delete',
                url: _this.options.base_media_url + $this_element.attr('media') +'/',
                success: function(){
                    $('img[data-id="' + $this_element.attr('media') + '"], video[data-id="' + $this_element.attr('media') + '"]').parent('.media-single-container').remove();
                }
            });
            $('#media-info').empty();
        },

        tagMedia: function(event){
            event.preventDefault();
            var $this_element = $(this);
            var orginal_tags = null;
            $.ajax({
                method: 'get',
                async:false,
                url:_this.options.base_media_url + $this_element.attr('media') +'/',
                success: function(response){
                    orginal_tags = response.tags;
                }
            });
            var tags = prompt('Please enter tags', orginal_tags);
            if (tags !== null){
                $.ajax({
                    method: 'patch',
                    url:_this.options.base_media_url + $this_element.attr('media') + '/',
                    data:{'tags': tags},
                    success: function(){
                        console.log('updated');
                    }
                });
            }
        },

        previewMedia: function(event){
            event.preventDefault();
            var $this_element = $(this);
            $('body').append(modalPreview($this_element.attr('src')));
        },

        saveImage: function(element){
            id_element = element.attr('id');
            data = {text: element.attr('src')};
            $.ajax({
                method:'PUT',
                async:false,
                url: _this.options.base_save_url + id_element +'/',
                data:data,
                success: function(data){
                    console.log('saved');
                }
            });
        },

        _initMediaInfo: function(){
            $('#media-info').addClass('placeholder').text('Click on an item to view more options');
        },

        _toggle_sidebar: function(){
            if ($('#sidebar-container').hasClass('active')){
                _this._close_sidebar();
            }else{
                _this._open_sidebar();
            }
        },

        _draggableButton: function(){
            $('#btn-toggle').draggable({
                axis: "x",
                cursor: "move",
                containment: "window",
                drag: function(event, ui){
                    var view_width = $(window).width();
                    if (view_width - ui.position.left - $(ui.helper).outerWidth() >= 300){
                        $('#sidebar-container').css("right", "0px").css("width", view_width - ui.position.left - $(ui.helper).outerWidth());
                    }else{
                        $('#btn-toggle').css("left", view_width - 300 - $(ui.helper).outerWidth());
                        return false;
                    }
                },
                stop : function(event, ui){
                    var view_width = $(window).width();
                    if (view_width - ui.position.left - $(ui.helper).outerWidth() >= 300){
                        $('#sidebar-container').css("right", "0px").css("width", view_width - ui.position.left - $(ui.helper).outerWidth());
                    }else{
                        $('#sidebar-container').css("right", "0px").css("width", 300);
                    }

                    $( event.toElement ).one('click', function(e){ e.stopImmediatePropagation(); } );
                }
            });
        },

        _open_sidebar: function(){
            $('#btn-toggle').addClass('active');
            _this._draggableButton();
            $('#sidebar-container').addClass('active');
            _this.loadImage();
        },

        _close_sidebar: function(){
            $('#sidebar-container').removeClass('active').attr("style", "");
            $('#btn-toggle').removeClass('active').attr("style", "");
            $('#btn-toggle').draggable('destroy');
            $('.image-gallery').remove();
        },

        filterImage: function(){
            var search_string = $(this).val();
            _this.loadImage(search_string);
        },

        loadImage: function(search){
            if (!search){
                search = "";
            }
            
            $.ajax({
                method:'GET',
                url:_this.options.base_media_url + '?q='+search,
                success: function(data){
                    $('#list-media').empty();
                    $.each(data, function(index,file){
                        $('#list-media').append(singleMedia(file, index));
                        $('#image_' + index).draggable({
                            helper: 'clone',
                            revert: true,
                            appendTo: "body",
                            start: function() {
                                $(".ui-draggable").not(this).css({
                                    // height: 50,
                                    width: 50
                                });
                            },
                        });
                    });
                }
            });
            _this.makemenu();
        },

        makemenu: function(){

            $(document).on('click', '.clickable-menu', function(){
                _this._initMediaInfo();
                $('.clickable-menu').not($(this)).removeClass('active-media');
                $('.media-single-container').css("border-color","transparent");
                if (!$(this).hasClass('active-media')){
                    $('#media-info').removeClass('placeholder').text('');
                    $(this).addClass('active-media');
                    $(this).parent('.media-single-container').css("border-color", "#000");
                    $.ajax({
                        method: 'get',
                        async:false,
                        url:_this.options.base_media_url + $(this).data('id') + '/',
                        success: function(response){
                            $('#media-info').append('<div class="url_info"><textarea style="width:98%" rows="4" readonly>'+response.file_src +'</textarea></div>');
                        }
                    });
                    $('#media-info').append(_this.menuMedia($(this).data('id'), $(this).prop("tagName") == 'VIDEO', $(this).attr('src')));
                }else{
                    $(this).removeClass('active-media');
                }
            });
        },

        menuMedia : function(sha, video, src){
            var menu = '\
                <button id="tag_media" media="' + sha + '" class="' + _this.options.button_class + '">Add tag</button>\
                <button id="delete_media" media="' + sha + '" class="' + _this.options.button_class + '">Delete</button>';
            if (video){
                menu += '<button id="preview_media" image="' + sha + '" src="'+ src +'" class="' + _this.options.button_class + '">Preview</button>';
            }
            return menu;
        }
    };

    $.sidebargallery = function(options) {
        var opts = $.extend( {}, $.sidebargallery.defaults, options );
        gallery = new SidebarGallery(opts);
    };

    $.sidebargallery.defaults = {
        base_save_url: null, // Url to send request to server
        csrf_token:'',
        base_media_url:'',
        url_progress:null,
        toggle: '<button class="btn btn-default" id="btn-toggle">Gallery</button>',
        button_class: ''
    };
})(jQuery);
