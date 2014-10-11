var app = angular.module('UploaderApp',[]);
var url = null

// app.config(function($interpolateProvider,$locationProvider,$httpProvider) {
//    $interpolateProvider.startSymbol('[%');
//    $interpolateProvider.endSymbol('%]');
//    // $httpProvider.defaults.xsrfCookieName = 'csrftoken';
//    // $httpProvider.defaults.xsrfHeaderName = 'X-CSRFToken';
//    console.log($httpProvider.defaults)
// });

app.directive('dropzone', function (csrf) {
   return function (scope, element, attrs) {
      var config, dropzone;

      config = scope[attrs.dropzone];

      // create a Dropzone for the element with the given options
      dropzone = new Dropzone(element[0], config.options);

      // bind the given event handlers
      dropzone.on('sending', function (file, xhr, formData) {
         formData.append('csrfmiddlewaretoken', csrf.csrf_token)
      });

      dropzone.on('drop', function (event) {
         var ans = confirm("Are you sure?");
         if (!ans){
            dropzone.emit('error');
         }
      });
      
      dropzone.on('error', function (file, response) {
         console.log(response.info)
      });

      dropzone.on('success', function (file, response) {
         scope.$apply(function(){
            var updated_template = $.grep(scope.uploadedtemplate_list, function(element, index){
               return element.id == response.id;
            })[0];
            if (updated_template){
               var idx = scope.uploadedtemplate_list.indexOf(updated_template);
               scope.uploadedtemplate_list[idx].updated_at = response.updated_at;
            }else{
               scope.uploadedtemplate_list.push(response);
            }
         })
      });
   }
});

app.controller('UploaderCtrl',function($scope, UploadedTemplateFactory, urls, csrf, $timeout){
   // $scope.uploadedtemplate_list = [];
   $scope.dropzoneConfig = {
       'options': { // passed into the Dropzone constructor
         'url': urls.upload_template,
         'addRemoveLinks':true
       }}
   
   $scope.init = function(){
      
      UploadedTemplateFactory.getUploadedTemplates(urls.get_uploaded_templates).success(function(data){
         $scope.uploadedtemplate_list = data;
      });
   }
   
   $scope.init();
   // $scope.uploadedtemplate_list[0].updated_at = "nullqsdfqsd";
   

})

app.factory('UploadedTemplateFactory', function($http){
   var factory = {};
   
   factory.getUploadedTemplates = function(url) {
      return $http.get(url);
   }
   
   return factory;
});