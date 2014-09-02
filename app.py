from flask import Flask, request, jsonify, render_template
import json, urllib.request, json, os

app = Flask(__name__)
apikey = ''

def apicall(interface, method, ver, query):
	global apikey
	url = 'http://api.steampowered.com/' + interface + '/' + method + '/v000' + ver + '/?key=' + apikey + '&format=json&' + query
	out = urllib.request.urlopen(url).read()
	j = json.loads(str(out, 'UTF-8'))
	return j

def resolveVanityID(vanityurl):
	j = apicall('ISteamUser', 'ResolveVanityURL', '1', 'vanityurl=' + vanityurl)
	if j['response']['success'] != 1:
		return None;
	return j['response']['steamid']

def checkSteamIDs(steamids):
	j = apicall('ISteamUser', 'GetPlayerSummaries', '2', 'steamids=' + ','.join(steamids))
	return len(j['response']['players']) == len(steamids)

def getGames(steamid):
	j = apicall('IPlayerService', 'GetOwnedGames', '1', 'steamid=' + steamid +
		'&include_played_free_games=1&include_appinfo=1')

	if 'games' not in j['response']:
		return {}

	return {
		game['appid']: {
				'name': game['name'],
				'logo': 
					(('http://media.steampowered.com/steamcommunity/public/images/apps/' +
					str(game['appid']) + '/' + game['img_logo_url'] + '.jpg')
					if game['img_logo_url']
					else '')
			} 
			for game in j['response']['games']
		}

def getGameCategories(appidlist):
	url = 'http://store.steampowered.com/api/appdetails/?appids='+(','.join(map(str, appidlist)))+'&filters=categories,genres'
	out = urllib.request.urlopen(url).read()
	j = json.loads(str(out, 'utf-8'))

	categories = {}
	genres = {}
	games = {}

	for appid in j:
		if j[appid]['success'] == True and j[appid]['data'] != []:
			games[int(appid)] = {}

			if 'categories' in j[appid]['data']:
				games[int(appid)]['categories'] = [int(cat['id']) for cat in j[appid]['data']['categories']]
			else:
				games[int(appid)]['categories'] = []

			if 'genres' in j[appid]['data']:
				games[int(appid)]['genres'] = [int(gen['id']) for gen in j[appid]['data']['genres']]
			else:
				games[int(appid)]['genres'] = []

			if 'categories' in j[appid]['data']:
				for cat in j[appid]['data']['categories']:
					categories[int(cat['id'])] = cat['description']
			
			if 'genres' in j[appid]['data']:
				for gen in j[appid]['data']['genres']:
					genres[int(gen['id'])] = gen['description']

	return {'categories': categories, 'genres': genres, 'games': games}

@app.route('/compare/<idlist>')
def compare(idlist):
	idlist = idlist.split(',');

	ids = []
	for id in idlist:
		if not id.isdigit():
			id = resolveVanityID(id)
		if id is not None:
			ids.append(id)

	if len(ids) != len(idlist):
		return "Invalid ID(s)"

	games = []
	for id in ids:
		games.append(getGames(id))

	gameids = set(games[0].keys())
	for g in games:
		gameids = gameids.intersection(set(g.keys()))

	gameids = list(gameids)
	gamecats = getGameCategories(gameids)
	
	gamelist = {key: {
				'name': games[0][key]['name'],
				'logo': games[0][key]['logo'],
				'categories': gamecats['games'][key]['categories'] if key in gamecats['games'] else [],
				'genres': gamecats['games'][key]['genres'] if key in gamecats['games'] else []
			}
			for key in games[0] if key in gameids
		}

	output = {'games': gamelist, 'categories': gamecats['categories'], 'genres': gamecats['genres']}

	return jsonify(output)

@app.route('/')
def index():
	return render_template('index.html')

@app.before_first_request
def before_first_request(*args, **kwargs):
	# Get Steam API key
	global apikey
	apifile = open('apikey.txt', 'r')
	apikey = apifile.read()[:-1]

def main():
	if not os.path.isfile('apikey.txt'):
		print('No SteamAPI key found (apikey.txt)')
	else:
		app.run(host='0.0.0.0')

if __name__ == '__main__':
	main()

