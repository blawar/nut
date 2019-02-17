
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
  	$scope.titlesDict = {};
  	$scope.queue = [];
  	$scope.updates = [];
  	$scope.title = null;
  	$scope.regionFilter = { US: true };
  	$scope.sortReverse = false;
  	$scope.sortPropertyName = 'name';
  	$scope.user = null;

  	$scope.ownedOptions = [
		{ id: 0, name: '' },
		{ id: 1, name: 'Purchased' },
		{ id: -1, name: 'Not Purchased' }
  	];

  	$scope.preloadedOptions = [
		{ id: 0, name: '' },
		{ id: 1, name: 'Preloaded' },
		{ id: -1, name: 'Not Preloaded' }
  	];

  	$scope.ownedFilter = $scope.ownedOptions[1];
  	$scope.preloadedFilter = $scope.preloadedOptions[0];

  	$scope.getTitle = function (id) {
  		return $scope.titlesDict[id];
  	};

  	$scope.sortBy = function (sortPropertyName) {
  		$scope.sortReverse = ($scope.sortPropertyName === sortPropertyName) ? !$scope.sortReverse : false;
  		$scope.sortPropertyName = sortPropertyName;
  	};

  	$scope.titleFilter = function (title) {
  		isOwned = title.base;
  		if ((!title.region || $scope.regionFilter[title.region]) && ($scope.ownedFilter.id != 1 || isOwned) && ($scope.preloadedFilter.id != 1 || (title.base && title.base.length > 0)) && ($scope.preloadedFilter.id != -1 || !title.base || title.base.length < 1) && ($scope.ownedFilter.id != -1 || !isOwned)) {
  			return true;
  		}

  		return false;
  	};

  	$http.get('/api/user').then(function (res) {
  		$scope.user = res.data;
  	});

  	$http.get('/api/titles').then(function (res) {
  		titles = [];
  		titlesDict = {};
  		for (key in res.data) {
  			title = res.data[key];
  			if (!title.isUpdate && !title.isDLC && !title.isDemo /*&& title.key != '00000000000000000000000000000000'*/) {
  				if (title.publisher == 'Nintendo') {
  					title.span = { col: 3, row: 3 };
					title.thumbSize = 640
  				} else if (['Bethesda Softworks', 'Team Cherry', 'Capcom', 'Motion Twin', 'Ubisoft', 'Activision', 'Mojang AB', 'Shin\'en', 'NIS America'].includes(title.publisher)) {
  					title.span = { col: 2, row: 2 };
  					title.thumbSize = 384
  				} else {
  					title.span = { col: 1, row: 1 };
  					title.thumbSize = 192
  				}
  				title.currentVersion = 0;
  				title.size = formatNumber(title.size, 'B');
  				title.children = [];
  				titlesDict[title.id] = title;
  				titles.push(title);
  			}
  		}
  		for (key in res.data) {
  			title = res.data[key];
  			if (title.isUpdate || title.isDLC) {
  				titlesDict[title.id] = title;

  				if (title.baseId != title.id && titlesDict[title.baseId] !== undefined) {
  					if (!titlesDict[title.baseId].children) {
  						titlesDict[title.baseId].children = [];
  					}
  					titlesDict[title.baseId].children.push(title);
  				}
  			}
  		}

  		for (key in res.data) {
  			title = res.data[key];
  			if (!title.isUpdate && !title.isDLC && title.id) {
  				updateId = title.id.substring(0, title.id.length - 3) + '800';
  				if (titlesDict[updateId]) {
  					title.latestVersion = titlesDict[updateId].version;
  				} else {
  					title.latestVersion = 0;
  				}
  			}
  		}

  		$http.get('/api/files').then(function (res) {
  			for (key in res.data) {
  				nsp = res.data[key];
  				title = titlesDict[key];
  				if (title) {
  					title.base = nsp.base;
  					title.dlc = nsp.dlc;
  					title.update = nsp.update;

  					for (i = 0; i < title.update.length; i++) {
  						f = title.update[i];
  						if (f.version >= title.currentVersion) {
  							title.currentVersion = f.version;
  						}
  					}
  				}
  			}
  		});
  		$scope.titles = titles;
  		$scope.titlesDict = titlesDict;
  	});

  	function getTitle(id) {
  		for (i in $scope.titles) {
  			if ($scope.titles[i].id == id) {
  				return $scope.titles[i];
  			}
  		}
  		return null;
  	}

  	/*setInterval(function () {
  		$http.get('/api/queue').then(function (res) {
  			queue = [];

  			for (key in res.data) {
  				row = res.data[key];
  				t = $scope.titlesDict[row.id];
  				if (t !== undefined) {
  					t.i = row.i;
  					t.size = row.size;

  					if (row.size) {
  						t.percent = Math.round(row.i * 100 / row.size);
  					} else {
  						t.percent = 0;
  					}

  					t.sizeFormatted = formatNumber(row.size, 'b');
  					t.speed = formatNumber(row.speed, '/s');
  					queue.push(t);
  				} else {
  				}
  			}
  			$scope.queue = queue;
  		});
  	}, 3000);*/

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

  	$scope.showUpdates = function () {
  		$('#popup').show();
  		$('#popup > div').hide();
  		$('#updates').show();

  		$http.get('/api/titleUpdates').then(function (res) {
  			updates = [];

  			for (key in res.data) {
  				row = res.data[key];
  				t = $scope.titlesDict[row.id];
  				if (t) {
  					row.name = t.name;

  					if (row.currentVersion) {
  						row.currentVersion = parseInt(row.currentVersion).toString(16);
  					}

  					row.newVersion = parseInt(row.newVersion).toString(16);
  					updates.push(row);
  				}
  			}
  			$scope.updates = updates;
  		});
  	};

  	$scope.closePopup = function () {
  		$('#popup').hide();
  		$('#popup > div').hide();
  	};

  	$scope.download = function (id) {
  		$http.get('/api/download/' + id).then(function (res) {
  		});
  	};

  	$scope.preload = function (id) {
  		$http.get('/api/preload/' + id).then(function (res) {
  		});
  	};

  	$scope.regionChanged = function (region) {
  		$scope.regionFilter[region] = $scope.regionFilter[region] ? false : true;
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