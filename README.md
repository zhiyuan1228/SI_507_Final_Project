# SI_507_Final_Project
A program that lets a user search for a movie and gain information associated with the movie. Users can add movies to their watchlist and view their watchlist in a sorted way.
## Instructions
An API Key for Open Movie Database is required. You can get one at http://www.omdbapi.com/apikey.aspx.
To run the program, create a file called "secrets.py" and paste the code "OMDB_API_KEY=[your_key_here]", then run final_project.py.
## Interaction Options
On the main menu, 3 options are available: search, view the watchlist, exit. Enter a number to select an option.  

Perform a search:   
  - Enter a movie title
  - Select a movie from the numbered list
  - Enter a number to select an option from five: view the cast, view the poster in a web browser, add to the watchlist, reselect a movie, go back. 

View the watchlist:    
  - Choose a display option: sort by rating/year/time added, barplot

## Required Python Packages
BeautifulSoup, requests, sqlite3, webbrowser, tabulate, plotly

## Demo Video
https://www.bilibili.com/video/BV1nX4y1u7qB/

If the link above does not work, please try the following link. https://youtu.be/VPCx40zXPnk