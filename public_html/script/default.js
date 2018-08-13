angular
  .module('nutApp', ['ngMaterial'])
  .controller('gridTitlesController', function ($scope, $http) {
  	$scope.titles = [];
  	$scope.title = null;

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

  	$scope.showTitle = function (title) {
  		$scope.title = title;
  		$('#popup').show();
  		$('#options').hide();
  		$('#game').show();
  	};

  	$scope.showOptions = function () {
  		$('#popup').show();
  		$('#game').hide();
  		$('#options').show();
  	};

  	$scope.closePopup = function () {
  		$('#popup').hide();
  		$('#game').hide();
  		$('#options').hide();
  	};
  }).filter('unique', function () {
  	return function (collection, keyname) {
  		var output = [],
		keys = [];
  		angular.forEach(collection, function (item) {
  			var key = item[keyname];
  			if (keys.indexOf(key) === -1) {
  				keys.push(key);
  				output.push(item);
  			}
  		});
  		return output;
  	};
  });