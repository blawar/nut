import Titles
import json

def getTitles(request, response):
	o = []
	map = ['id', 'isUpdate', 'isDLC', 'isDemo', 'name', 'version', 'region']
	for k, t in Titles.items():
		o.append(t.dict())
	response.write(json.dumps(o))