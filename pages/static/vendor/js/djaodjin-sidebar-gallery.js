

(function ($) {

    var toggle_button = '<button class="btn btn-primary" id="btn-toggle">Toggle</button>';
    var sidebar = '<div id="sidebar-gallery"><h1 class="text-center" style="color:white;">Image gallery</h1><input placeholder="Search..." id="gallery-filter" type="text" class="form-control"><div id="list-images"></div><form action="/file-upload" class="dropzone" id="uploadzone-gallery" style="display:none"></form></div>';
    var sidebar_size = 200;
    var loaded = false;
    var initialized = false;
    var id= null;

    function SidebarGallery(options){
        this.options = options;
        this._init();
        Dropzone.autoDiscover = false;
    }


    function update_progress_info() {
        $.getJSON("/get-progress/upload/", {'X-Progress-ID': id}, function(data, status){
            if(data){
                NProgress.set(data.uploaded /data.lenght);
                $('#progress-span').text((data.uploaded /data.lenght)*100)
            }
            else{
                console.log('upload finish');
                $('#progress-span').text(100);
                return false;
            }
            setTimeout(update_progress_info, 10);
        });
    }

    SidebarGallery.prototype = {

        _init: function(){
            _this = this;
            $('body').append(toggle_button).append(sidebar);
            $('body').wrapInner('<div id="gallery-wrapper"></div>');
            $(document).on('click','#btn-toggle', _this._toggle_sidebar);
            $(document).on('keyup', '#gallery-filter', _this.filterImage);
            $(document).on('start_upload', function(){
                
                setTimeout(update_progress_info, 20);
            });
            
            
            $('.droppable-image').droppable({
                drop: function( event, ui ) {
                    var droppable = $(this);
                    droppable.attr('src', ui.draggable.attr('src'));
                    $(ui.helper).remove();
                    _this.saveImage(droppable);
              }
            });
        
            $("#uploadzone-gallery").dropzone({
                    paramName: 'img',
                    // url: _this.options.img_upload_url,
                    dictDefaultMessage: "Drag and drop your image here",
                    // clickable: true,
                    // enqueueForUpload: false,
                    // createImageThumbnails:false,
                    maxFilesize: 20,
                    // autoProcessQueue: true,
                    parallelUploads: 2,
                    // uploadMultiple: false,
                    // addRemoveLinks: true,
                    processing: function(file){
                        id = (new Date).getTime();
                        this.options.url = _this.options.img_upload_url + '?X-Progress-ID=' +id;

                    },

                    sending: function(file, xhr, formData){
                        var tags = prompt("Please enter your tags","");
                        formData.append('csrfmiddlewaretoken', _this.options.csrf_token);
                        formData.append('csrfmiddlewaretoken', _this.options.csrf_token);
                        formData.append('tags', tags);
                        $('#list-images').append('<div class="col-md-12 padding-top-img progress-text text-center">Upload in progress<br><p><span id="progress-span">0</span>%</p>Please wait...</div>');                      
                        $.event.trigger({
                          type:    "start_upload",
                          message: "myTrigger fired.",
                          time:    new Date()
                        });
                    },

                    uploadprogress: function(file, progress, bytesent){
                        
                    },

                    canceled: function(file){
                        $('.progress-text').remove();
                    },

                    success: function(data, response){
                        $('.progress-text').remove();
                        var last_index = $('#list-images').children().last().children().attr('id');
                        if (last_index){
                            last_index = parseInt(last_index.split('image_')[1]) + 1;
                        }else{
                            last_index = 0;
                        }
                        if (!response.exist){
                            $('#list-images').append('<div class="col-md-6 padding-top-img"><img id="image_'+ last_index + '" class="image" src="'+ response.img +'" width="50px"></div>');
                        
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
                        }else{
                            $('#list-images').append('<div class="col-md-12 padding-top-img alert">Image already in your gallery</div>');
                            setTimeout(function() {
                                $('.alert').remove();
                            }, 3000);
                        }
                        
                    }
                });
                $("#uploadzone-gallery").show();
        },

        saveImage: function(element){
            id_element = element.attr('id');
            data = {text: element.attr('src')};
            $.ajax({
                method:'PUT',
                async:false,
                url: _this.options.base_url + id_element +'/',
                data:data,
                success: function(data){
                    console.log('saved');
                }
            });
        },

        _toggle_sidebar: function(){
            var width_wrap = $('#gallery-wrapper').css('width').split('px')[0];
            if ($('#sidebar-gallery').hasClass('active')){
                $('#sidebar-gallery').removeClass('active');
                $('#btn-toggle').removeClass('active');
                $('#gallery-wrapper').css({'max-width': '100%'});
                $('.row').css({'padding-right':'0px'});
                $('.row').css({'padding-left':'0px'});
                $('.row').css({'margin-right':'0px'});
                $('.row').css({'margin-left':'0px'});
                $('.image-gallery').remove();
            }else{
                $('#sidebar-gallery').addClass('active');
                $('#btn-toggle').addClass('active');
                $('#gallery-wrapper').css({'max-width':width_wrap - sidebar_size});
                $('.row').css({'padding-right':'30px'});
                $('.row').css({'padding-left':'30px'});
                $('.row').css({'margin-right':'30px'});
                _this.loadImage();
                
                
                // $('.row').css({'margin-left':'30px'});
            }
        },

        filterImage: function(){
            var search_string = $(this).val();
            _this.loadImage(search_string);
        },

        loadImage: function(search){
            if (!search){
                search = "";
            }
            $('#list-images').empty();
            $.ajax({
                    method:'GET',
                    url:'/example/api/list/uploaded-images/?search='+search,
                    success: function(data){
                        $.each(data, function(index,element){
                            $('#list-images').append('<div class="col-md-6 padding-top-img"><img id="image_'+ index + '" class="image" src="'+ element.img_src +'" width="50px"></div>');
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
        }

    };

    $.sidebargallery = function(options) {
        var opts = $.extend( {}, $.sidebargallery.defaults, options );
        gallery = new SidebarGallery(options);
    };

    $.sidebargallery.defaults = {
        base_url: null, // Url to send request to server
        csrf_token:'',
        img_upload_url:'',
    };
})(jQuery);