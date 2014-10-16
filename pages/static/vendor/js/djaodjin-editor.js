
/*djaodjin-editor.js
jQuery plugin allowing to edit html online.
*/
/* jshint multistr: true */
(function ($) {
	var _this = null;

	var tags = ['p','h1','h2','h3','h4','h5','h6', 'a'];

	var clicked_element = null;
	var orig_element = null;
	var class_element = null;
	var new_text = null;
	var orig_text = null;
	var font_size = null;
	var line_height = null;
	var height = null;
	var width = null;
	var margin_bottom = null;
	var margin_top = null;
	var font_family = null;
	var font_weight = null;
	var text_align = null;
	var padding = null;
	var color = null;
	var id_element = null;
	var new_id = null;

	var markdown_tool = false;

	function Editor(el, options){
		this.$el = el;
		this.options = options;
		this.debug = false;
		this._init();
	}

	Editor.prototype = {
		_init: function(){
			_this = this;
			// add editable class on all tags
			if (_this.options.autotag){
				$.each(tags, function(index,element){
					$(element).each(function(){
						if (!($(this).children().length > 0 && $(this).children().first().text() == $(this).text())){
							$(this).addClass('editable');
						}

						if (($(this).prop("tagName") == _this.options.markdown_identifier.toUpperCase() ) && _this.options.enable_markdown){
							$(this).addClass('edit-markdown');
						}
					});
				});
			}	

			// add toggle edit mode
			/* XXX toggle_button creates an unnecessary ugly checkbox
			   and should be moved to the test page.
			   In general, if a developper runs $("body").editor(),
			   it is because editing functionality is required.
			*/
			$(document).on('click', _this.documentClick);
			$(document).on('click, keydown','#input_editor', _this.removeAlert);
			$(document).on('click', '.btn_tool',_this.addMarkdowntag);
			// $(document).on('drop', '#input_editor', _this.DropImage);
		},

		_clickEditable: function(){
			
			id_element = clicked_element.attr(_this.options.unique_identifier);
			orig_element = clicked_element;
			if (clicked_element.hasClass('edit-markdown')){
				_this.getTextElement();
			}else{
				orig_text = $.trim(clicked_element.text());
			}
			// orig_text = $.trim(clicked_element.text());
			
			class_element = clicked_element.attr('class');
			font_size = parseInt(clicked_element.css('font-size').split("px"));
			line_height = parseInt(clicked_element.css('line-height').split("px"));
			height = clicked_element.css('height');
			margin_bottom = clicked_element.css('margin-bottom');
			margin_top = clicked_element.css('margin-top');
			font_family = clicked_element.css('font-family');
			font_weight = clicked_element.css('font-weight');
			text_align =clicked_element.css('text-align');
			padding = clicked_element.css('padding');
			color = clicked_element.css('color');
			width = clicked_element.css('width');

			
			if (clicked_element.prop('tagName') == 'DIV'){
				if (clicked_element.children('p').length > 0){
					font_size = parseInt(clicked_element.children('p').css('font-size').split("px"));
					line_height = parseInt(clicked_element.children('p').css('line-height').split("px"));
					height = clicked_element.children('p').css('height');
					margin_bottom = clicked_element.children('p').css('margin-bottom');
					margin_top = clicked_element.children('p').css('margin-top');
					font_family = clicked_element.children('p').css('font-family');
					font_weight = clicked_element.children('p').css('font-weight');
					text_align =clicked_element.children('p').css('text-align');
					padding = clicked_element.children('p').css('padding');
					color = clicked_element.children('p').css('color');
					width = clicked_element.children('p').css('width');
				}else{
					font_size = parseInt($('p').first().css('font-size').split("px"));
					line_height = parseInt($('p').first().css('line-height').split("px"));
					height = $('p').first().css('height');
					margin_bottom = $('p').first().css('margin-bottom');
					margin_top = $('p').first().css('margin-top');
					font_family = $('p').first().css('font-family');
					font_weight = $('p').first().css('font-weight');
					text_align =$('p').first().css('text-align');
					padding = $('p').first().css('padding');
					color = $('p').first().css('color');
					width = $('p').first().css('width');
				}
				
			}
			_this.inputEdit();
		},

		inputEdit: function(){
			_this.toggleInput();

		},

		toggleInput: function(){
			var upload_enable = false;
			var upload_form = ''
			markdown_tool = false;
			if (clicked_element.hasClass('edit-markdown')){
				markdown_tool = true;
			}
			var mardown_tool_html = '<div id="tool_markdown"><button type="button" class="btn_tool" id="title_h3">H3</button>\
		             <button type="button" class="btn_tool" id="title_h4">H4</button>\
		             <button type="button" class="btn_tool" id="bold"><strong>B</strong></button>\
		             <button type="button" class="btn_tool" id="italic"><em>I</em></button>\
		             <button type="button" class="btn_tool" id="list_ul">List</button>\
		             <button type="button" class="btn_tool" id="link">Link</button></div>';
		    if (_this.options.enable_upload){
		    	upload_form = '<form action="/file-upload" class="dropzone" id="uploadzone" style="display:none;height:50px;position:absolute;bottom:0px;width:100%;border:1px solid #AAA;border-radius:5px;color:#AAA;padding:5px;margin-bottom:0px"></form>';
		    }
      	    var textarea_html = '<div class="input-group" id="editable_section"><textarea class="form-control editor" id="input_editor" value="" spellcheck="false"></textarea>'+upload_form+'</div>';
      	    if (clicked_element.hasClass('edit-markdown')){
      	    	upload_enable = true;
      	    }
		    clicked_element.replaceWith(textarea_html);

		    if (_this.options.enable_upload){
		    	if (upload_enable){
					$("#uploadzone").dropzone({
		                paramName: 'img',
		                url: _this.options.img_upload_url,
		                dictDefaultMessage: "To add an image in this part place the cursor where you want it and drag an image from your desktop to this zone.",
		                clickable: true,
		                enqueueForUpload: true,
		                createImageThumbnails:false,
		                maxFilesize: 1,
		                uploadMultiple: false,
		                addRemoveLinks: true,
		                sending: function(file, xhr, formData){
		                	formData.append('csrfmiddlewaretoken', _this.options.csrf_token)
		                },
		                success: function(data, response){
		                	$('#input_editor').focus()
		                	$('#input_editor').selection('insert',{text:'![Alt text]('+ response.img +')' ,mode:'before'})
		                }
	            	});
					$('#uploadzone').show();
					$('#input_editor').css({'margin-bottom':"50px"});
				}
		    }

			$('#editable_section').css({
				'margin-bottom':parseInt(margin_bottom.split("px"))-(line_height-font_size)+'px',
				'margin-top':parseInt(margin_top.split("px"))+'px',
			});

			$('#editable_section').addClass(class_element);
			$('#editable_section').removeClass('edit-hover editable');
			$('#input_editor').val($.trim(orig_text)).focus();
			
			$('#input_editor').css({
				'position':'relative',
				'padding-top':-(line_height-font_size)+'px',
				'line-height':line_height + 'px',
				'font-size': font_size + 'px',
				'font-family':font_family,
				'font-weight':font_weight,
				'text-align':text_align,
				'color':color,
				'width':width,
				'height':parseInt(height.split("px"))+(line_height-font_size)+'px',				
			});
			$('#input_editor').autosize({append:''});

			if (markdown_tool){
				$('body').append(mardown_tool_html);
				$('#tool_markdown').css({
					'top': ($('#editable_section').offset().top - 45) + 'px',
					'left': $('#editable_section').offset().left +'px',
				});
			}
			// focus input end of text
			$('#input_editor')[0].setSelectionRange($('#input_editor').val().length, $('#input_editor').val().length);
		},

		toggleTextarea: function(){
			
		},

		checkInput: function () {
			if ($('#input_editor').length > 0){
				new_text = $('#input_editor').val();
				if (new_text != "" && new_text != "Please enter text"){ //jshint ignore:line
					if (new_text != orig_text){
						if (clicked_element.attr('data-type') == 'currency_to_integer'){
							new_text = (parseFloat(new_text.replace('$',''))*100).toFixed();
						}
						_this.saveEdition();
						if (clicked_element.attr('data-type') == 'currency_to_integer'){
							new_text = '$' + parseFloat(new_text)/100;
						}
					}
					if (markdown_tool){
						convert = new Markdown.getSanitizingConverter().makeHtml;
            			clicked_element.html(convert(new_text));
					}else{
						clicked_element.text(new_text);
					}
					
					$('#editable_section').replaceWith(clicked_element);
					if (clicked_element.attr('id') === undefined && new_id){
						clicked_element.attr('id',new_id);
						new_id = null;
					}
					$('#tool_markdown').remove();
				}else if (new_text == "" || new_text == "Please enter text"){ //jshint ignore:line
					$('#input_editor').val('Please enter text');
					$('#input_editor').css('color','red').focus();
				}
			}
		},

		saveEdition: function(){
			if (_this.debug == false){//jshint ignore:line
				if (!_this.options.base_url){
					if ($('.error-label').length > 0){
						$('.error-label').remove();
					}
					$('body').prepend('<div class="error-label">No base_url option provided. Please update your script to use save edition.</div>');
					return false;
				}
				if (!id_element){
					id_element = 'undefined';
				}
				var data = {};
				if (clicked_element.attr('data-key')){
					data[clicked_element.attr('data-key')] = $.trim(new_text);
				}else{
					data = {text:$.trim(new_text), old_text:$.trim(orig_text), template_name:_this.options.template_name, template_path:_this.options.template_path, tag: clicked_element.prop("tagName")};
				}
				$.ajax({
					method:'PUT',
					async:false,
					url: _this.options.base_url + id_element +'/',
					data:data,
					success: function(data){
						new_id = data.slug;
					}
				});
			}
		},

		getTextElement: function(){
			if (_this.debug == false){//jshint ignore:line
				$.ajax({
					method:'GET',
					async:false,
					url: _this.options.base_url + id_element +'/',
					success: function(data){
						if (clicked_element.attr('data-key')){
							orig_text = data[clicked_element.attr('data-key')];
						}else{
							orig_text = data.text;
						}
					},
					error: function(){
						orig_text = $.trim(clicked_element.text());
					}
				});
			}
		},

		removeAlert: function(){
			if ($('#input_editor').val() == 'Please enter text' && event.keycode != 27){
				$('#input_editor').val('');
				$('#input_editor').css('color',color);
			}
		},

		documentClick: function(event){
			if ($(event.target).hasClass('editable') || $(event.target).parents('.editable').length > 0){
				_this.checkInput();
				if ($('#input_editor').length == 0){//jshint ignore:line
					if (!$(event.target).hasClass('editable')){
						clicked_element = $(event.target).closest('.editable');
					}else{
						clicked_element = $(event.target);
					}
					_this._clickEditable();
				}
			}else if ($(event.target).attr('id') != 'input_editor' && $(event.target).parents('#tool_markdown').length == 0){//jshint ignore:line
				_this.checkInput();
				clicked_element = null;
			}
		},

		addMarkdowntag: function(event){
			if ($(this).attr('id') == 'title_h3'){
				$('#input_editor').selection('insert',{text:'###' ,mode:'before'}).selection('insert', {text: '', mode: 'after'});
			}else if($(this).attr('id') == 'title_h4'){
				$('#input_editor').selection('insert',{text:'####' ,mode:'before'}).selection('insert', {text: '', mode: 'after'});
			}else if($(this).attr('id') == 'bold'){
				$('#input_editor').selection('insert',{text:'**' ,mode:'before'}).selection('insert', {text: '**', mode: 'after'});
			}else if($(this).attr('id') == 'list_ul'){
				$('#input_editor').selection('insert',{text:'* ' ,mode:'before'}).selection('insert', {text: '', mode: 'after'});
			}else if($(this).attr('id') == 'link'){
				var text = $('#input_editor').selection();
        		if (text.indexOf("http://") >= 0){
           			$('#input_editor').selection('insert',{text:'['+text+'](' ,mode:'before'}).selection('insert', {text: ')', mode: 'after'});
        		}else{
           			$('#input_editor').selection('insert',{text:'[http://'+text+'](http://' ,mode:'before'}).selection('insert', {text: ')', mode: 'after'});
        		}
			}else if($(this).attr('id') == 'italic'){
				$('#input_editor').selection('insert',{text:'*' ,mode:'before'}).selection('insert', {text: '*', mode: 'after'});
			}
		}
	};

	$.fn.editor = function(options) {
		var opts = $.extend( {}, $.fn.editor.defaults, options );
		editor = new Editor($(this), opts);
		return editor;
	};

	$.fn.editor.defaults = {
		base_url: null, // Url to send request to server
		unique_identifier: 'id',
		autotag:false,
		enable_markdown: true,
		markdown_identifier: 'p',
		template_name:'',
		template_path:'',
		csrf_token:'',
		enable_upload:false,
		img_upload_url:'',
	};

})(jQuery);
