from bs4 import BeautifulSoup
import secrets
import requests
import json
import sqlite3

from tabulate import tabulate
import plotly.graph_objs as go

CACHE_FILENAME = "cache.json"
DB_FILENAME = "movie.sqlite"
CACHE_DICT = {}

def open_cache():
    try:
        cache_file = open(CACHE_FILENAME, 'r')
        cache_contents = cache_file.read()
        cache_dict = json.loads(cache_contents)
        cache_file.close()
    except:
        cache_dict = {}
    return cache_dict

def save_cache(cache_dict):
    dumped_json_cache = json.dumps(cache_dict)
    fw = open(CACHE_FILENAME,"w")
    fw.write(dumped_json_cache)
    fw.close() 

def construct_unique_key(baseurl, params):
    param_strings = []
    connector = '_'
    for k in params.keys():
        param_strings.append(f'{k}_{params[k]}')
    param_strings.sort()
    unique_key = baseurl + connector + connector.join(param_strings)
    return unique_key

def make_request_with_cache(baseurl, params):
    unique_key = construct_unique_key(baseurl, params)
    CACHE_DICT = open_cache()
    if unique_key in CACHE_DICT.keys():
        print('Fetching cached data...')
        return CACHE_DICT[unique_key]
    else:
        print('Making new request...')
        response = requests.get(baseurl, params)
        CACHE_DICT[unique_key] = json.loads(response.text)
        save_cache(CACHE_DICT)
    return CACHE_DICT[unique_key]

def get_movie_list(title):
    client_key = secrets.OMDB_API_KEY
    params = {'apikey':client_key, 's':title.lower()}
    results = make_request_with_cache('http://www.omdbapi.com', params)
    movie_list = []
    for item in results['Search']:
        movie = Movie(item['Title'], item['Year'], item['imdbID'], item['Poster'])
        movie_list.append(movie)
    return movie_list

def print_numbered_list(list):
    for i in range(len(list)):
        print(f'[{i + 1}] {list[i].info()}')

def get_movie_details(title):
    client_key = secrets.OMDB_API_KEY
    params = {'apikey':client_key, 't':title.lower()}
    results = make_request_with_cache('http://www.omdbapi.com', params)
    # print(results)
    runtime = results['Runtime']
    genre = results['Genre']
    director = results['Director']
    rating = results['Ratings'][0]['Value']
    # rating_source = results['Ratings'][0]['Source']
    # print('-'*30)
    # print(f'More Info about {title}')
    # print('-'*30)
    # print(f'Runtime: {runtime}, Genre: {genre}, Director: {director}, Rating: {rating} (from {rating_source})')
    return [director, rating, runtime]

def get_results_via_scraping(url):
    CACHE_DICT = open_cache()
    if url in CACHE_DICT.keys():
        print('Fetching cached data...')
        return CACHE_DICT[url]
    else:
        print('Making new request...')
        page = requests.get(url)
        CACHE_DICT[url] = page.text
        save_cache(CACHE_DICT)
    return CACHE_DICT[url]


def get_cast(imdbID):
    url = 'https://www.imdb.com/title/' + imdbID
    soup = BeautifulSoup(get_results_via_scraping(url), 'html.parser')
    cast_list = soup.find(class_='cast_list')
    cast_list_items = cast_list.find_all('tr')[1:]
    actor_list = []
    for person in cast_list_items:
        try:
            actor_name = person.select('td')[1].find('a').contents[0].strip()
            # print(actor_name)
            character = person.find(class_='character').find('a').contents[0].strip()
            actor_url = 'https://www.imdb.com' + person.find(class_='primary_photo').find('a').get('href')
            # print(character)
            # print(actor_url)
            actor = Actor(actor_name, character, actor_url)
            actor_list.append(actor)
        except AttributeError:
            break
    return actor_list

def get_actor_details(actor_url):
    soup = BeautifulSoup(get_results_via_scraping(actor_url), 'html.parser')
    known_for = soup.find(id='knownfor')
    known_for_items = known_for.find_all(class_='knownfor-title-role')
    title_list = []
    rating_list = []
    for movie in known_for_items:
        movie_title = movie.find('a').contents[0].strip()
        movie_rating = get_movie_details(movie_title)[1].split('/')[0]
        title_list.append(movie_title)
        rating_list.append(float(movie_rating))
        print(f'movie title: {movie_title}, rating: {movie_rating}')
    return title_list
    # bar_plot(title_list, rating_list)

def bar_plot(xvals, yvals):
    bar_data = go.Bar(x=xvals, y=yvals)
    basic_layout = go.Layout(title="Known For")
    fig = go.Figure(data=bar_data, layout=basic_layout)
    fig.show()

def create_database():
    conn = sqlite3.connect(DB_FILENAME)
    cur = conn.cursor()
    create_movies = '''
        CREATE TABLE IF NOT EXISTS "Movies" (
            "Id" INTEGER PRIMARY KEY AUTOINCREMENT UNIQUE,
            "Title" TEXT NOT NULL,
            "Year" INTEGER NOT NULL,
            "IMDBId" TEXT NOT NULL,
            "Director" TEXT NOT NULL,
            "Rating" REAL NOT NULL,
            "Runtime" INTEGER NOT NULL
        );
    '''
    create_actors = '''
        CREATE TABLE IF NOT EXISTS "Actors" (
            "Id" INTEGER PRIMARY KEY AUTOINCREMENT UNIQUE,
            "FirstName" TEXT NOT NULL,
            "LastName" TEXT NOT NULL,
            "KnownForTitle" TEXT NOT NULL,
            "MovieId" INTEGER 
        );
    '''
    cur.execute(create_movies)
    cur.execute(create_actors)
    conn.commit()

def insert_movie(movie):
    conn = sqlite3.connect(DB_FILENAME)
    cur = conn.cursor()
    director, rating, runtime = get_movie_details(movie.title)
    rating = rating.split('/')[0]
    runtime = runtime.split(' ')[0]
    insert_movies = '''
        INSERT INTO Movies
        VALUES (NULL, ?, ?, ?, ?, ?, ?)
    '''
    values = [movie.title, movie.year, movie.imdbID, director, rating, runtime]
    cur.execute(insert_movies, values)
    conn.commit()

def insert_actor(actor):
    conn = sqlite3.connect(DB_FILENAME)
    cur = conn.cursor()
    firstname = actor.name.split(' ')[0]
    lastname = actor.name.split(' ')[1]
    knownfor = get_actor_details(actor.url)[0]
    insert_actors = '''
        INSERT INTO Actors
        VALUES (NULL, ?, ?, ?, 1)
    '''
    values = [firstname, lastname, knownfor]
    cur.execute(insert_actors, values)
    conn.commit()

class Movie:
    def __init__(self, title, year, imdbID, poster_url):
        self.title = title
        self.year = year
        self.imdbID = imdbID
        self.poster_url = poster_url
        self.rating = None
        self.runtime = None
    
    def info(self):
        return f'{self.title} ({self.year}) imdbID: {self.imdbID}'

class Actor:
    def __init__(self, name, character, url, known_for=None):
        self.name = name
        self.character = character
        self.url = url
    
    def info(self):
        return f'Actor: {self.name}, Character: {self.character}'

def main():
    create_database()
    title = 'Titanic'
    movie_list = get_movie_list(title)
    print_numbered_list(movie_list)
    get_movie_details(movie_list[0].title)
    cast_list = get_cast(movie_list[0].imdbID)
    print_numbered_list(cast_list)
    get_actor_details(cast_list[0].url)
    for movie in movie_list:
        insert_movie(movie)
    for actor in cast_list:
        insert_actor(actor)



if __name__ == "__main__":
	main()


# url = 'https://www.imdb.com/name/nm0000138/'
# page = requests.get(url)
# soup = BeautifulSoup(page.text, 'html.parser')
# # bio = soup.find(class_='inline').contents[0]
# # print(bio)
# known_for = soup.find(id='knownfor')
# known_for_items = known_for.find_all(class_='knownfor-title-role')
# for movie in known_for_items:
#     print(movie.find('a').contents[0].strip())