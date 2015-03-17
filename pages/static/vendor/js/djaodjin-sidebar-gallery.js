
 /* jshint multistr: true */
(function ($) {

    
    var sidebar = '<div id="sidebar-gallery"><h1 class="text-center" style="color:white;">Media gallery</h1><input placeholder="Search..." id="gallery-filter" type="text" class="form-control"><div id="media-container"><div id="list-media"></div><div class="col-xs-12">Drag and drop or click to upload Media</div></div></div>';
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

    function update_progress_info() {
        $.getJSON("/get-progress/upload/", {'X-Progress-ID': id}, function(data, status){
            if(data){
                $('#progress-span').text((data.uploaded /data.lenght)*100);
            }
            else{
                $('#progress-span').text(100);
                return false;
            }
            setTimeout(update_progress_info, 10);
        });
    }

    SidebarGallery.prototype = {

        _init: function(){
            _this = this;

            if (_this.options.toggle){
                toggle_button = _this.options.toggle;
            }else{
                toggle_button = '<button class="btn btn-default" id="btn-toggle">Gallery</button>';
            }
            
            $('body').append(toggle_button).append(sidebar);
            $('body').wrapInner('<div id="gallery-wrapper"></div>');
            $(document).on('click','#btn-toggle', _this._toggle_sidebar);
            $(document).on('keyup', '#gallery-filter', _this.filterImage);
            $(document).on('start_upload', function(){
                
                setTimeout(update_progress_info, 20);
            });

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
                this.options.url = _this.options.base_media_url + '?X-Progress-ID=' +id;
            });

            DocDropzone.on("cancel", function(file){
                $('.progress-text').remove();
            });

            DocDropzone.on("sending", function(file, xhr, formData){
                formData.append('csrfmiddlewaretoken', _this.options.csrf_token);
                formData.append('csrfmiddlewaretoken', _this.options.csrf_token);
                $('#media-container').append('<div class="col-md-12 padding-top-img progress-text text-center">Upload in progress<br><p><span id="progress-span">0</span>%</p>Please wait...</div>');                      
                $.event.trigger({
                  type:    "start_upload",
                  message: "myTrigger fired.",
                  time:    new Date()
                });
            });

            DocDropzone.on("dragover", function(event){
                if (count == 0){
                    $('body').prepend('<div class="notify-user-label info-label">Release your file to upload it</div>');
                    count = 1;
                }
            });

            DocDropzone.on("drop", function(event){
                $('.notify-user-label').remove();
                count = 0;
            });

            DocDropzone.on("dragleave", function(event){
                $('.notify-user-label').remove();
                count = 0;
            });

            DocDropzone.on("success", function(data, response){
                $('.progress-text').remove();
                $('.dz-preview').remove();
                var last_index = $('#list-media').children().last().children().attr('id');
                if (last_index){
                    last_index = parseInt(last_index.split('image_')[1]) + 1;
                }else{
                    last_index = 0;
                }
                if (!response.exist){
                    if (response.uploaded_file_temp.indexOf('.mp4') > 0){
                        $('#list-media').append('<div class="col-md-6 padding-top-img"><video data-id="'+ response.id + '" id="image_'+ last_index + '" class="image  clickable-menu image_media" src="'+ response.uploaded_file_temp +'" width="50px"></video></div>');
                    }else{
                        $('#list-media').append('<div class="col-md-6 padding-top-img"><img data-id="'+ response.id + '" id="image_'+ last_index + '" class="image  clickable-menu image_media" src="'+ response.uploaded_file_temp +'" width="50px"></div>');
                    }
                    
                
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
                    $('#media-container').append('<div class="col-md-12 padding-top-img alert">Image already in your gallery</div>');
                    setTimeout(function() {
                        $('.alert').remove();
                    }, 3000);
                    
                }
                if (!$('#sidebar-gallery').hasClass('active')){
                    _this._open_sidebar();
                }
            });
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

        _toggle_sidebar: function(){
            
            if ($('#sidebar-gallery').hasClass('active')){
                _this._close_sidebar();
            }else{
                _this._open_sidebar();
            }
        },

        _open_sidebar: function(){
            var width_wrap = $('#gallery-wrapper').css('width').split('px')[0];
            $('#btn-toggle').addClass('active');
            $('#sidebar-gallery').addClass('active');
            $('#gallery-wrapper').css({'max-width':width_wrap - sidebar_size});
            $('.row').css({'padding-right':'30px'});
            $('.row').css({'padding-left':'30px'});
            $('.row').css({'margin-right':'30px'});
            _this.loadImage();
        },

        _close_sidebar: function(){
            var width_wrap = $('#gallery-wrapper').css('width').split('px')[0];
            $('#sidebar-gallery').removeClass('active');
            $('#btn-toggle').removeClass('active');
            $('#gallery-wrapper').css({'max-width': '100%'});
            $('.row').css({'padding-right':'0px'});
            $('.row').css({'padding-left':'0px'});
            $('.row').css({'margin-right':'0px'});
            $('.row').css({'margin-left':'0px'});
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
            $('#list-media').empty();
            $.ajax({
                method:'GET',
                url:_this.options.base_media_url + '?search='+search,
                success: function(data){
                    $.each(data, function(index,element){
                        var src_file = null;
                        if (element.file_src){
                            src_file = element.file_src;
                        }else{
                            src_file = element.file_src_temp;
                        }
                        if (src_file.indexOf('.mp4') > 0){
                            $('#list-media').append('<div class="col-md-6 padding-top-img"><img data-id="'+ element.id + '" id="image_'+ index + '" class="image clickable-menu padding-top-img image_media" src="'+ src_file +'" width="50px"></div>');
                        }else{
                            $('#list-media').append('<div class="col-md-6 padding-top-img"><img data-id="'+ element.id + '" id="image_'+ index + '" class="image clickable-menu padding-top-img image_media" src="'+ src_file +'" width="50px"></div>');
                        }
                        // $('#list-images').append('<div class="col-md-6 padding-top-img"><img data-id="'+ element.id + '" id="image_'+ index + '" class="image clickable-menu padding-top-img image_media" src="'+ src_file+'" width="50px"></div>');
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
            $(document).contextmenu({
                delegate: ".clickable-menu",
                menu: [
                    {title: "Delete", cmd: "delete_media"},
                    {title: "Add tag", cmd: "add_tag"},
                    {title: "Preview Video", cmd: "preview_video" }
                    ],
                select: function(event, ui) {
                    var id = $(ui.target).data('id');
                    if (ui.cmd == 'delete_media'){
                        $.ajax({
                            method: 'delete',
                            url:_this.options.base_media_url +id +'/',
                            success: function(){
                                $(ui.target).parent('.col-md-6').remove();
                            }
                        });
                    }else if (ui.cmd == 'add_tag'){
                        var orginal_tags = null;
                        $.ajax({
                            method: 'get',
                            async:false,
                            url:_this.options.base_media_url+id+'/',
                            success: function(response){
                                orginal_tags = response.tags;
                            }
                        });
                        
                        var tags = prompt('Please enter tags', orginal_tags);
                        if (tags !== null){
                            $.ajax({
                                method: 'patch',
                                url:_this.options.base_media_url+id+'/',
                                data:{'tags': tags},
                                success: function(){
                                    console.log('updated');
                                }
                            });
                        }
                        
                    }else if (ui.cmd == 'preview_video'){
                        $('body').append(modal);
                        $('#modal-video').attr('src',$(ui.target).attr('src'));
                        $('#myModal').modal('show');
                    }
                }
            });
        }


    };

    $.sidebargallery = function(options) {
        var opts = $.extend( {}, $.sidebargallery.defaults, options );
        gallery = new SidebarGallery(options);
    };

    $.sidebargallery.defaults = {
        base_save_url: null, // Url to send request to server
        csrf_token:'',
        base_media_url:'',
        toggle: null
    };
})(jQuery);