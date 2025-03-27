import logging
import os
import time
from collections import Counter
from flask import Flask, render_template, request, flash, jsonify
from keyword_research import SEOKeywordAgent

# Configure logging
logging.basicConfig(level=logging.DEBUG)
logger = logging.getLogger('app')

app = Flask(__name__)
app.secret_key = os.environ.get('SECRET_KEY', 'development-key')

# Initialize the SEO keyword agent
keyword_agent = SEOKeywordAgent()

@app.route('/', methods=['GET', 'POST'])
def index():
    """Handle the main application page and form submission."""
    query = ''
    keywords = {}
    top_keywords = []
    error = None
    search_time = None
    
    if request.method == 'POST':
        query = request.form.get('query', '').strip()
        
        if not query:
            flash('Please enter a search query', 'warning')
        else:
            try:
                logger.debug(f'Processing query: {query}')
                start_time = time.time()
                
                # Run the keyword research
                keyword_counts = keyword_agent.run(query)
                
                search_time = round(time.time() - start_time, 2)
                logger.debug(f'Search completed in {search_time} seconds')
                
                if keyword_counts is not None and not keyword_counts.empty:
                    # Convert to dictionary for template use
                    keywords = keyword_counts.to_dict()
                    logger.debug(f'Found {len(keywords)} optimized keywords')
                    
                    # Get top 10 keywords for the summary section
                    top_keywords = [
                        {'keyword': k, 'count': v} 
                        for k, v in list(keywords.items())[:10]
                    ]
                else:
                    error = 'Unable to find keywords for this query. Please try a different search term.'
                    flash(error, 'danger')
            except Exception as e:
                logger.exception('Error processing keyword research')
                error = f'An error occurred: {str(e)}'
                flash(error, 'danger')
    
    return render_template(
        'index.html',
        query=query,
        keywords=keywords,
        top_keywords=top_keywords,
        error=error,
        search_time=search_time
    )

@app.route('/api/keyword-research', methods=['POST'])
def api_keyword_research():
    """API endpoint for keyword research."""
    data = request.get_json()
    
    if not data or 'query' not in data:
        return jsonify({'error': 'Missing query parameter'}), 400
    
    query = data['query'].strip()
    
    if not query:
        return jsonify({'error': 'Query cannot be empty'}), 400
    
    try:
        # Run the keyword research
        keyword_counts = keyword_agent.run(query)
        
        if keyword_counts is not None and not keyword_counts.empty:
            # Convert to dictionary for JSON response
            keywords = keyword_counts.to_dict()
            return jsonify({
                'query': query,
                'keywords': keywords,
                'count': len(keywords)
            })
        else:
            return jsonify({'error': 'No keywords found'}), 404
    except Exception as e:
        logger.exception('Error processing API keyword research')
        return jsonify({'error': str(e)}), 500

@app.errorhandler(404)
def page_not_found(e):
    """Handle 404 errors."""
    return render_template('index.html', error='Page not found'), 404

@app.errorhandler(500)
def server_error(e):
    """Handle 500 errors."""
    return render_template('index.html', error='Server error occurred'), 500

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000, debug=True)
