angular
  .module('nutApp', ['ngMaterial'])
  .controller('gridTitlesController', function ($scope, $http) {
  	$scope.titles = [];
  	$http.get('/api/titles').then(function (res) {
  		titles = [];
  		for (key in res.data) {
  			title = res.data[key];
  			if (!title.isUpdate && !title.isDLC && !title.isDemo && title.key != '00000000000000000000000000000000') {
  				titles.push(title);
  			}
  		}
  		$scope.titles = titles;
  	});
  });