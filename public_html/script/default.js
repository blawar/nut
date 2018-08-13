$(document).ready(function() {
	$.getJSON('/api/titles', function(titles) {
		list = $('#titles');
		for(key in titles) {
			title = titles[key];
			if(!title.isUpdate && !title.isDLC && title.key != '00000000000000000000000000000000') {
				list.append('<li><div style="background-image: url(/api/titleImage/' + title.id + '/192)">' + title.name + '</div></li>');
			}
		};
	});
});