$(document).ready(function() {
	$.getJSON('/api/titles', function(titles) {
		list = $('#titles');
		for(key in titles) {
			title = titles[key];
			list.append('<li><div>' + title.name + '</div></li>');
		};
	});
});