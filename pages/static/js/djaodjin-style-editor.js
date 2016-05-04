/* global $ ace document:true */

(function ($) {
    "use strict";

    function StyleEditor(el, options){
        this.element = el;
        this.$element = $(el);
        this.options = options;
        this.$refreshButton = this.$element.find('.refresh-styles');
        this.init();
    }

    StyleEditor.prototype = {
        init: function () {
            var self = this;
            self.$refreshButton.on("click", function(event) {
                self.refreshStyles();
            });
            self.refreshBootstrap();
        },

        refreshBootstrap: function(){
            var formValues = $('#editable-styles-form').serializeArray();

            var modifiedVars = {};
            for(var i = 0; i < formValues.length ; i ++){
                var formElem = formValues[i];
                if ( formElem.value != '' ){
                    modifiedVars[formElem.name] = formElem.value;
                }
            }
            less.refresh(true, modifiedVars);
        },
        refreshStyles: function(){
            var self = this;
            var formValues = $('#editable-styles-form').serializeArray();
            var bootstrap_variables = []
            
            for(var i = 0; i < formValues.length ; i ++){
                var formElem = formValues[i];
                if ( formElem.value != '' ){
                    bootstrap_variables.push({
                        variable_name: formElem.name,
                        variable_value: formElem.value
                    });
                }
            }

            $.ajax({
                url: self.options.api_bootstrap_overrides,
                method: "PUT",
                datatype: "json",
                contentType: "application/json; charset=utf-8",
                data: JSON.stringify(bootstrap_variables),
                success: function(response) {
                    self.refreshBootstrap();
                },                
                error: function(resp) {
                    showErrorMessages(resp);
                }
            });
        }
    };

    $.fn.djstyles = function(options) {
        var opts = $.extend( {}, $.fn.djstyles.defaults, options );
        return this.each(function() {
            if (!$.data($(this), "djstyles")) {
                $.data($(this), "djstyles", new StyleEditor(this, opts));
            }
        });
    };

    $.fn.djstyles.defaults = {
        api_bootstrap_overrides: "/api/bootstrap_variables"
    };

})(jQuery);
