from bs4 import BeautifulSoup
import secrets
import requests
import json
import sqlite3
import webbrowser
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
        # print('Fetching cached data...')
        return CACHE_DICT[unique_key]
    else:
        # print('Making new request...')
        response = requests.get(baseurl, params)
        CACHE_DICT[unique_key] = json.loads(response.text)
        save_cache(CACHE_DICT)
    return CACHE_DICT[unique_key]

def get_single_movie(title):
    client_key = secrets.OMDB_API_KEY
    params = {'apikey':client_key, 't':title.lower()}
    results = make_request_with_cache('http://www.omdbapi.com', params)
    movie = Movie(results['Title'], results['Year'], results['imdbID'], 
        results['Poster'], results['Genre'], results['Runtime'], 
        results['Director'], results['Plot'], results['imdbRating'])
    return movie

def get_movie_list(title):
    client_key = secrets.OMDB_API_KEY
    params = {'apikey':client_key, 's':title.lower()}
    results = make_request_with_cache('http://www.omdbapi.com', params)
    movie_list = []
    for item in results['Search']:
        movie = None
        try:
            movie = get_single_movie(item['Title'])
        except KeyError:
            continue
        # params = {'apikey':client_key, 't':item['Title'].lower()}
        # new_results = make_request_with_cache('http://www.omdbapi.com', params)
        # try:
        #     movie = Movie(new_results['Title'], new_results['Year'], new_results['imdbID'], 
        #      new_results['Poster'], new_results['Genre'], new_results['Runtime'], 
        #      new_results['Director'], new_results['Plot'], new_results['imdbRating'])
        # except KeyError:
        #     continue
        try:
            insert_movie(movie)
        except ValueError:
            continue
        movie_list.append(movie)
    return movie_list

def print_numbered_list(list):
    for i in range(len(list)):
        print(f'[{i + 1}] {list[i].info()}')

def get_movie_rating(title):
    client_key = secrets.OMDB_API_KEY
    params = {'apikey':client_key, 't':title.lower()}
    results = make_request_with_cache('http://www.omdbapi.com', params)
    return results['imdbRating']

def get_results_via_scraping(url):
    CACHE_DICT = open_cache()
    if url in CACHE_DICT.keys():
        # print('Fetching cached data...')
        return CACHE_DICT[url]
    else:
        # print('Making new request...')
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

def get_actor_details(actor):
    soup = BeautifulSoup(get_results_via_scraping(actor.url), 'html.parser')
    print(f'-----------{actor.name} is Known For-----------')
    known_for = soup.find(id='knownfor')
    known_for_items = known_for.find_all(class_='knownfor-title-role')
    # title_list = []
    # rating_list = []
    insert_actor(actor)
    for movie in known_for_items:
        movie_title = movie.find('a').contents[0].strip()
        try:
            movie_rating = get_movie_rating(movie_title)
        except KeyError:
            continue
        # title_list.append(movie_title)
        # rating_list.append(float(movie_rating))
        print(f'{movie_title}, rating: {movie_rating}')
        # bar_plot(title_list, rating_list)
    # return known_for_items[0].find('a').contents[0].strip()

def get_first_known_for_title(actor):
    soup = BeautifulSoup(get_results_via_scraping(actor.url), 'html.parser')
    known_for = soup.find(id='knownfor')
    known_for_items = known_for.find_all(class_='knownfor-title-role')
    return known_for_items[0].find('a').contents[0].strip()

def bar_plot(xvals, yvals):
    bar_data = go.Bar(x=xvals, y=yvals)
    basic_layout = go.Layout(title="Bar Plot")
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
            "MovieId" INTEGER NOT NULL REFERENCES Movies(Id)
        );
    '''
    create_watchlist = '''
        CREATE TABLE IF NOT EXISTS "WatchList" (
            "Id" INTEGER PRIMARY KEY AUTOINCREMENT UNIQUE,
            "Title" TEXT NOT NULL,
            "Year" INTEGER NOT NULL,
            "Rating" REAL NOT NULL,
            "MovieId" INTEGER NOT NULL REFERENCES Movies(Id)
        );
    '''
    cur.execute(create_movies)
    cur.execute(create_actors)
    cur.execute(create_watchlist)
    conn.commit()

def connection_helper(query):
    connection = sqlite3.connect(DB_FILENAME)
    cursor = connection.cursor()
    result = cursor.execute(query).fetchall()
    connection.close()
    # print(result)
    return result

def data_exists(query):
    if not connection_helper(query):
        return False
    else:
        return True

def insert_movie(movie):
    query = f'''
    SELECT Id
    FROM Movies
    WHERE Title="{movie.title}"
    '''
    if not data_exists(query):
        conn = sqlite3.connect(DB_FILENAME)
        cur = conn.cursor()
        rating = float(movie.rating)
        runtime = int(movie.runtime.split(' ')[0])
        insert_movies = '''
            INSERT INTO Movies
            VALUES (NULL, ?, ?, ?, ?, ?, ?)
        '''
        values = [movie.title, movie.year, movie.imdbID, movie.director, rating, runtime]
        cur.execute(insert_movies, values)
        conn.commit()

def insert_actor(actor):
    firstname = actor.name.split(' ')[0]
    lastname = actor.name.split(' ')[1]
    query = f'''
    SELECT Id
    FROM Actors
    WHERE FirstName="{firstname}" AND LastName="{lastname}"
    '''
    if not data_exists(query):
        conn = sqlite3.connect(DB_FILENAME)
        cur = conn.cursor()
        knownfor = get_first_known_for_title(actor)
        # print(knownfor)
        insert_actors = '''
            INSERT INTO Actors
            VALUES (NULL, ?, ?, ?, ?)
        '''
        query = f'''
        SELECT Id
        FROM Movies
        WHERE Title="{knownfor}"
        '''
        result = connection_helper(query)
        if not result:
            insert_movie(get_single_movie(knownfor))
            query = "SELECT COUNT(*) FROM Movies"
            movieID = connection_helper(query)[0][0]
        else:
            movieID = result[0][0]
        values = [firstname, lastname, knownfor, movieID]
        cur.execute(insert_actors, values)
        conn.commit()

def insert_watchlist(movie):
    query = f'''
    SELECT Id
    FROM WatchList
    WHERE Title="{movie.title}"
    '''
    if not data_exists(query):
        conn = sqlite3.connect(DB_FILENAME)
        cur = conn.cursor()
        rating = float(movie.rating)
        insert_watchlist = '''
            INSERT INTO WatchList
            VALUES (NULL, ?, ?, ?, ?)
        '''
        query = f'''
        SELECT Id
        FROM Movies
        WHERE Title="{movie.title}"
        '''
        result = connection_helper(query)
        movieID = result[0][0]
        values = [movie.title, movie.year, rating, movieID]
        cur.execute(insert_watchlist, values)
        conn.commit()

class Movie:
    def __init__(self, title, year, imdbID, poster_url, genre, runtime, director, plot, rating):
        self.title = title
        self.year = int(year[0:4])
        self.imdbID = imdbID
        self.poster_url = poster_url
        self.genre = genre
        self.runtime = runtime
        self.director = director
        self.plot = plot
        self.rating = rating
    
    def info(self):
        return f'{self.title} ({self.year}) imdbRating: {self.rating}'

    def detailed_info(self):
        print(f'-----------More Info about "{self.title}"-----------')
        print(self.plot)
        print(f'Runtime: {self.runtime}\nGenre: {self.genre}\nDirector: {self.director}\nimdbID: {self.imdbID}')

class Actor:
    def __init__(self, name, character, url):
        self.name = name
        self.character = character
        self.url = url
    
    def info(self):
        return f'Actor: {self.name}, Character: {self.character}'

def prompt_title():
    movie_list = None
    while True:
        title = input('Please enter a movie title: ')
        try:
            movie_list = get_movie_list(title)
        except KeyError:
            print('Sorry! No results were found. Try again. ')
            continue
        print(f'-----------Results for "{title}"-----------')
        break
    return movie_list

def prompt_number(total_number):
    number = None
    while True:
        number = input('Please enter a number for more info, or "back" to go back: ')
        if number == 'back':
            return number
        if number.isnumeric():
            if int(number) > 0 and int(number) <= total_number:
                break
        print('Invalid input. Try again. ')
    return int(number)

def promt_first():
    while True:
        print('-'*30)
        print('The following options are available:')
        print('1: Search for a movie by title\n2: View my watch list\n3: Exit')
        first_input = input('Please enter a number to select an option: ')
        if first_input == '1' or first_input == '2' or first_input == '3':
            break
        print('Invalid input. Try again. ')
    return first_input

def prompt_next(selected_movie):
    while True:
        print('-'*30)
        print('The following options are available:')
        print('1: View the cast list\n2: View the poster\n3: Add to my watchlist\n4: Reselect a movie\n5: Go back to the main menu')
        next_input = input('Please enter a number to select an option: ')
        if next_input == '1' or next_input == '2' or next_input == '3' or next_input == '4' or next_input == '5':
            break
        print('Invalid input. Try again. ')
    return next_input

def print_watch_list():
    number = None
    while True:
        print('-'*30)
        print('The following options are available:')
        print('1: Sort by rating\n2: Sort by year\n3: Sort by time added\n4: Show a bar plot')
        number = input('Please enter a number to select an option: ')
        if number == '1' or number == '2' or number == '3' or number == '4':
            break
        print('Invalid input. Try again. ')
    print('----------Watch List----------')
    query = '''
        SELECT Title, Year, Rating
        FROM WatchList
        LIMIT 10
        '''
    if number == '1' or number == '4':
        query = '''
        SELECT Title, Year, Rating
        FROM WatchList
        ORDER BY Rating DESC
        LIMIT 10
        '''
    elif number == '2':
        query = '''
        SELECT Title, Year, Rating
        FROM WatchList
        ORDER BY Year DESC
        LIMIT 10
        '''
    raw_query_result = connection_helper(query)
    if number == '4':
        title_list = []
        rating_list = []
        for row in raw_query_result:
            title_list.append(row[0])
            rating_list.append(row[2])
        bar_plot(title_list, rating_list)
    else:
        print_query_result(raw_query_result)

def print_query_result(raw_query_result):
    table = []
    for row in raw_query_result:
        new_row = []
        for field in row:
            field = str(field)
            if len(field) > 20:
                field = field[:20] + '...'
            new_row.append(field)
        table.append(new_row)
    print(tabulate(table, headers=['Title', 'Year', 'Rating'], tablefmt="pretty"))

def main():
    next_input = None
    create_database()
    # watch_list = []
    while True:
        first_input = promt_first()
        if first_input == '1':
            movie_list = prompt_title()
            print_numbered_list(movie_list)
        elif first_input == '2':
            # print(watch_list)
            print_watch_list()
        elif first_input == '3':
            print('Bye! ')
            exit(0)
        if first_input == '1':
            while True:
                print('-'*30)
                print('Which movie would you like to know more? ')
                number = prompt_number(len(movie_list))
                if number == 'back':
                    break
                selected_movie = movie_list[number - 1]
                selected_movie.detailed_info()
                next_input = prompt_next(selected_movie)
                if next_input == '1':
                    cast_list = get_cast(selected_movie.imdbID)
                    print(f'-----------Cast List for "{selected_movie.title}"-----------')
                    print_numbered_list(cast_list)
                    while True:
                        print('-'*30)
                        print('Which actor would you like to know more about his/her famous works? ')
                        number = prompt_number(len(cast_list))
                        if number == 'back':
                            break
                        selected_actor = cast_list[number - 1]
                        get_actor_details(selected_actor)
                elif next_input == '2':
                    print('*'*30)
                    print(f'Launching {selected_movie.poster_url} in web browser...')
                    webbrowser.open(selected_movie.poster_url)
                    print('*'*30)
                elif next_input == '3':
                    # watch_list.append(selected_movie)
                    insert_watchlist(selected_movie)
                    print('*'*30)
                    print(f'"{selected_movie.title}" has successfully been added to your watchlist! ')
                    print('*'*30)
                elif next_input == '4':
                    continue
                elif next_input == '5':
                    break

if __name__ == "__main__":
	main()

