
function Round(n, dec) {
	return n.toFixed(dec);
}

function formatNumber(rate, unit /*= 'h/s'*/) {
	if (rate == null) {
		return "";
	}

	if (rate < 0.0000007) {
		return Round(rate * 1000000000, 2) + " n" + unit;
	}
	else if (rate < 0.0007) {
		return Round(rate * 1000000, 2) + " µ" + unit;
	}
	else if (rate < 0.7) {
		return Round(rate * 1000, 2) + " m" + unit;
	}
	else if (rate < 700) {
		return Round(rate.Value, 2) + " " + unit;
	}
	else if (rate < 700000) {
		return Round(rate / 1000, 2) + " K" + unit;
	}
	else if (rate < 700000000) {
		return Round(rate / 1000000, 2) + " M" + unit;
	}
	else if (rate < 700000000000) {
		return Round(rate / 1000000000, 2) + " G" + unit;
	}
	else if (rate < 700000000000000) {
		return Round(rate / 1000000000000, 2) + " T" + unit;
	}
	else {
		return Round(rate / 1000000000000000, 2) + " P" + unit;
	}
}

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

  	function getTitle(row) {
  		for (i in $scope.titles) {
  			if ($scope.titles[i].id == row.id) {
  				$scope.titles[i].i = row.i;
  				$scope.titles[i].size = row.size;

  				if (row.size) {
  					$scope.titles[i].percent = Math.round(row.i * 100 / row.size);
  				} else {
  					$scope.titles[i].percent = 0;
  				}

  				$scope.titles[i].sizeFormatted = formatNumber(row.size, 'b');
  				$scope.titles[i].speed = formatNumber(row.speed, '/s');
  				return $scope.titles[i];
  			}
  		}
  		return null;
  	}

  	setInterval(function () {
  		$http.get('/api/queue').then(function (res) {
  			queue = [];

  			for (key in res.data) {
  				row = res.data[key];
  				t = getTitle(row);
  				if(t) queue.push(t);
  			}
  			$scope.queue = queue;
  		});
  	}, 3000);

  	$scope.showTitle = function (title) {
  		$scope.title = title;
  		$('#popup').show();
  		$('#popup > div').hide();
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

  	$scope.download = function (id) {
  		$http.get('/api/download/' + id).then(function (res) {
  		});
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