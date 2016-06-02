jQuery(document).ready(function($) {

  $(".editable").editor({
    baseUrl:  urls_edit_api_page_elements ,
    preventBlurOnClick: "#toggle-media-gallery, .dj-gallery-item"
  });

});
