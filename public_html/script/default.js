angular
  .module('nutApp', ['ngMaterial'])
  .controller('gridTitlesController', function ($scope, $http) {
  	$scope.titles = [];
  	$scope.queue = [];
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

  	function getTitle(id) {
  		for (i in $scope.titles) {
  			if ($scope.titles[i].id == id) {
  				return $scope.titles[i];
  			}
  		}
  	}

  	$http.get('/api/queue').then(function (res) {
  		queue = [];
  		for (key in res.data) {
  			queue.push(getTitle(res.data[key]));
  		}
  		$scope.queue= queue;
  	});

  	$scope.showTitle = function (title) {
  		$scope.title = title;
  		$('#popup').show();
  		$$('#popup > div').hide();
  		$('#game').show();
  	};

  	$scope.showOptions = function () {
  		$('#popup').show();
  		$('#popup > div').hide();
  		$('#options').show();
  	};

  	$scope.showQueue = function () {
  		$('#popup').show();
  		$('#popup > div').hide();
  		$('#queue').show();
  	};

  	$scope.closePopup = function () {
  		$('#popup').hide();
  		$('#popup > div').hide();
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