import os
import logging
import time
import traceback
from flask import Flask, request, render_template, session, redirect, url_for, flash, jsonify
from keyword_research import SEOKeywordAgent

# Set up logging
logging.basicConfig(level=logging.DEBUG)
logger = logging.getLogger(__name__)

# Initialize Flask app
app = Flask(__name__)
app.secret_key = os.environ.get("SESSION_SECRET", "dev-secret-key")

# Initialize the SEO keyword agent
agent = SEOKeywordAgent()

@app.route('/', methods=['GET', 'POST'])
def index():
    """Handle the main application page and form submission."""
    keywords = None
    query = ""
    error = None
    search_time = None
    top_keywords = []
    
    if request.method == 'POST':
        query = request.form.get('query', '').strip()
        
        if not query:
            flash("Please enter a search query", "danger")
            return render_template('index.html', keywords=None, query="", error="Empty query")
        
        logger.debug(f"Processing query: {query}")
        
        try:
            # Track execution time
            start_time = time.time()
            
            # Run the keyword research
            optimized_keywords = agent.run(query)
            
            # Calculate execution time
            search_time = round(time.time() - start_time, 2)
            logger.debug(f"Search completed in {search_time} seconds")
            
            if optimized_keywords.empty:
                error = "No keywords found. Please try a different query."
                flash(error, "warning")
            else:
                # Get the total number of keywords found
                total_keywords = len(optimized_keywords)
                
                # Get the top 5 keywords for the summary box
                top_keywords = [
                    {"keyword": k, "count": v} 
                    for k, v in optimized_keywords.head(5).items()
                ]
                
                # Convert to dictionary for template rendering
                # Limit to top 50 keywords for display
                keywords = optimized_keywords.head(50).to_dict()
                logger.debug(f"Found {total_keywords} optimized keywords")
                flash(f"Found {total_keywords} keywords for '{query}' in {search_time} seconds", "success")
                
        except Exception as e:
            error = f"An error occurred: {str(e)}"
            logger.error(f"Error while processing query '{query}': {str(e)}")
            logger.error(traceback.format_exc())
            flash(error, "danger")
    
    return render_template(
        'index.html', 
        keywords=keywords, 
        query=query, 
        error=error, 
        search_time=search_time,
        top_keywords=top_keywords
    )

@app.route('/api/keyword-research', methods=['POST'])
def api_keyword_research():
    """API endpoint for keyword research."""
    data = request.json
    
    if not data or 'query' not in data:
        return jsonify({
            'error': 'Missing query parameter'
        }), 400
    
    query = data['query'].strip()
    
    if not query:
        return jsonify({
            'error': 'Empty query'
        }), 400
    
    try:
        # Run the keyword research
        start_time = time.time()
        optimized_keywords = agent.run(query)
        search_time = round(time.time() - start_time, 2)
        
        if optimized_keywords.empty:
            return jsonify({
                'query': query,
                'error': 'No keywords found',
                'search_time': search_time
            }), 200
        
        # Convert to dictionary with counts
        keywords_dict = optimized_keywords.to_dict()
        
        return jsonify({
            'query': query,
            'keywords': keywords_dict,
            'total_keywords': len(optimized_keywords),
            'search_time': search_time
        }), 200
        
    except Exception as e:
        logger.error(f"API error while processing query '{query}': {str(e)}")
        logger.error(traceback.format_exc())
        return jsonify({
            'query': query,
            'error': str(e)
        }), 500

@app.errorhandler(404)
def page_not_found(e):
    """Handle 404 errors."""
    return render_template('index.html', error="Page not found"), 404

@app.errorhandler(500)
def server_error(e):
    """Handle 500 errors."""
    logger.error(f"Server error: {str(e)}")
    logger.error(traceback.format_exc())
    return render_template('index.html', error="Server error occurred. Please try again later."), 500