/* global jQuery: true*/

(function ($) {
    "use strict";

    function Editor(element, options){
        var self = this;
        self.el = element;
        self.$el = $(element);
        self.options = options;
        self.init();
        return self;
    }

    Editor.prototype = {
        init: function(){

            var self = this;
            self.$el.on("click", function(){
                self.toggleEdition();
            });

            self.$el.on("blur", function(){
                self.saveEdition();
            });

            self.$el.on("mouseover mouseleave", function(event){
                self.hoverElement(event);
            });

            $(".editable").bind("hallomodified", function(event, data) {
                $("#modified").html("Editables modified");
            });

        },

        hoverElement: function(event){
            var self = this;
            if (event.type === "mouseover"){
                self.$el.addClass("hover-editable");
            }else{
                self.$el.removeClass("hover-editable");
            }
        },

        getId: function() {
            var self = this;
            var slug = self.$el.attr(self.options.uniqueIdentifier);
            if( !slug ) {
                slug = self.$el.parents(
                    "[" + self.options.uniqueIdentifier + "]").attr(
                        self.options.uniqueIdentifier);
            }
            if( !slug ) {
                slug = "undefined";
            }
            return slug;
        },

        getOriginText: function(){
            var self = this;
            self.originText = $.trim(self.$el[0].outerHTML);
            return self.originText;
        },

        toogleStartOptional: function(){
            return true;
        },

        toogleEndOptional: function(){
            return true;
        },

        initHallo: function(){
            var self = this;
            self.$el.hallo().focus();
        },

        toggleEdition: function(){
            var self = this;
            self.initHallo();
            self.getOriginText();
            self.$el.attr("placeholder", self.options.emptyInputText);
        },

        getSavedText: function(){
            var self = this;
            return self.$el.html();
        },

        checkInput: function(){
            var self = this;
            if (self.$el.html() === ""){
                return false;
            }else{
                return true;
            }
        },

        formatDisplayedValue: function(){
            return true;
        },

        saveEdition: function(){
            var self = this;
            var savedText = self.getSavedText();
            if (!self.checkInput()){
                return false;
            }

            var data = {};
            var method = "PUT";
            if (self.$el.attr("data-key")){
                data[self.$el.attr("data-key")] = $.trim(savedText);
                method = "PATCH";
            } else {
                data = {
                    slug: self.getId(),
                    body: $.trim(savedText),
                    oldBody: self.originText,
                    tag: self.$el.prop("tagName")
                };
            }

            if (self.options.debug){
                console.log(data);
            }else{
                $.ajax({
                    method: method,
                    async: false,
                    url: self.options.baseUrl + self.getId() + "/",
                    data: data,
                    success: function(response) {
                        self.options.onSuccess(self, response);
                        self.$el.removeAttr("contenteditable");
                        self.formatDisplayedValue();
                    },
                    error: self.options.onError
                });
            }
        }
    };

    function CurrencyEditor(element, options){
        var self = this;
        self.el = element;
        self.$el = $(element);
        self.options = options;
        self.init();
        return self;
    }

    CurrencyEditor.prototype = $.extend({}, Editor.prototype, {
        getSavedText: function(){
            var self = this;
            var enteredValue = self.$el.text();
            var amount = parseInt(
                (parseFloat(enteredValue.replace(/[^0-9\.]+/g, "")) * 100).toFixed(2));
            return amount;
        },

        formatDisplayedValue: function(){
            var self = this;
            var defaultCurrencyUnit = "$";
            var defaultCurrencyPosition = "before";
            if (self.$el.data("currency-unit")){
                defaultCurrencyUnit = self.$el.data("currency-unit");
            }

            if (self.$el.data("currency-position")){
                defaultCurrencyPosition = self.$el.data("currency-position");
            }

            var amount = String((self.getSavedText() / 100).toFixed(2));
            if (defaultCurrencyPosition === "before"){
                amount = defaultCurrencyUnit + amount;
            }else if(defaultCurrencyPosition === "after"){
                amount = amount + defaultCurrencyUnit;
            }
            self.$el.html(amount);
        }
    });

    function FormattedEditor(element, options){
        var self = this;
        self.el = element;
        self.$el = $(element);
        self.options = options;
        self.init();
        return self;
    }

    FormattedEditor.prototype = $.extend({}, Editor.prototype, {
        initHallo: function(){
            var self = this;
            self.$el.hallo({
                plugins: {
                    "halloheadings": {},
                    "halloformat": {},
                    "halloblock": {},
                    "hallojustify": {},
                    "hallolists": {},
                    "hallolink": {},
                    "halloreundo": {}
                },
                editable: true,
                toolbar: "halloToolbarFixed"
            }).focus();
            self.initDroppable();
        },

        // method only applicable
        initDroppable: function(){
            // Build our own droppable to avoid useless features
            var self = this;
            $.each(self.$el.children(), function(index, element){
                if (!$(element).hasClass("ui-droppable")){
                    $(element).droppable({
                        drop: function(){
                            var droppable = $(this);
                            droppable.focus();
                        },
                        over: function(event, ui){
                            var droppable = $(this);
                            var draggable = ui.draggable;
                            droppable.append("<img src=\"" + draggable.attr("src") + "\" style=\"max-width:100%;\">");
                        },
                        out: function(event, ui){
                            var draggable = ui.draggable;
                            $(this).children("[src=\"" + draggable.attr("src") + "\"]").remove();
                        }
                    });
                }
            });
        }
    });

    $.fn.editor = function(options, custom){
        var opts = $.extend( {}, $.fn.editor.defaults, options );
        return this.each(function() {
            if (!$.data($(this), "editor")) {
                if ($(this).hasClass("edit-formatted")){
                    $.data($(this), "editor", new FormattedEditor($(this), opts));
                }else if ($(this).hasClass("edit-currency")){
                    $.data($(this), "editor", new CurrencyEditor($(this), opts));
                }else{
                    $.data($(this), "editor", new Editor($(this), opts));
                }
            }
        });
    };

    $.fn.editor.defaults = {
        baseUrl: null, // Url to send request to server
        emptyInputText: "Impossible to save an empty element.",
        uniqueIdentifier: "id",
        onSuccess: function(){
            return true;
        },
        onError: function(){
            return true;
        },
        debug: false
    };

}( jQuery ));
