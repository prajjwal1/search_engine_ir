from flask import Flask, abort, redirect, render_template, request, url_for
import json
import webbrowser
import time
import sys
import nltk
sys.path.append("../clustering")
from rerankingkmeans import getDocs
from rerankingComplete import getDocsComplete
from rerankingSingle import getDocsSingle

app = Flask(__name__)

# New Home Page
@app.route('/',methods = ['POST', 'GET'])
def index():
    if request.method == 'POST':
        q = request.form['query']
        if len(q) > 0:
            return redirect(url_for('search', q=q))
    return render_template('index.html', title="Travel Search")

# Search Page
@app.route('/search/<q>', methods=['GET', 'POST'])
def search(q=""):
    timeStart = time.perf_counter()

    # Sets eq to be the Expanded Query # TODO: Expand Query
    eq = q

    # Gets Results for Column #1
    results1 = []
    with open('sampleResults1.json') as f:
        results1 = json.load(f)  # TODO: Load Real Results

    # Gets Results for Column #2
    results2 = getDocs(q)
    
    # Gets Results for Column #3
    results3 = getDocsComplete(q)

    # Gets Results for Column #4
    results4 = getDocsSingle(q)
    
    # Gets the Query from the Interface
    if request.method == 'POST' and 'query' in request.form:
        q = request.form['query']
        return redirect(url_for('search', q=q))
    
    # Determines Time to Show Results
    elapsedTime = time.perf_counter() - timeStart

    webbrowser.open('https://www.google.com/search?q=' + q) # Search Google Simulateously
    webbrowser.open('https://www.bing.com/search?q=' + q)   # Search Bing Simulatenously
    return render_template('search.html', q=q, eq=eq, title=q, time=elapsedTime, results1=results1, results2=results2, results3=results3, results4=results4)

# Handles an Unknown Page
@app.route('/<unknown_page>')
def var_page(unknown_page):
    abort(404)

# 404 Page
@app.errorhandler(404)
def not_found(error):
    if request.method == 'POST':
        return redirect(url_for('search', q=request.form['query']))
    return render_template('404.html', title="Page Not Found")

if __name__ == '__main__':
    nltk.download('stopwords')
    nltk.download('punkt')
    nltk.download('wordnet')
    app.run(debug=True)