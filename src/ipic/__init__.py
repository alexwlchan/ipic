#!/usr/bin/env python
# encoding: utf8
"""
iTunes API searcher.

Usage:
  ipic (-i | --ios)       <search_term>
  ipic (-m | --mac)       <search_term>
  ipic (-a | --album)     <search_term>
  ipic (-f | --film)      <search_term>
  ipic (-t | --tv)        <search_term>
  ipic (-b | --book)      <search_term>
  ipic (-n | --narration) <search_term>
  ipic                    <search_term>
  ipic (-h | --help)      <search_term>

Options:
  -h --help         Show this screen
  -i --ios          iOS app
  -m --mac          Mac app
  -a --album        album
  -f --film         movie (film)
  -t --tv           TV show
  -b --book         book
  -n --narration    audiobook (narration)
"""

import collections
import subprocess
import tempfile

import docopt
import requests


# URL for the iTunes search API
API_URL = 'https://itunes.apple.com/search'

# Browser bundle identifier
BROWSER = 'com.apple.Safari'


def parse_command_line_args(args=None):
    """
    Parses the command-line arguments, and returns a tuple with
    the search term, and some variables for the iTunes API call.
    """
    # If no arguments are provided, read them from the command-line.
    if args is None:
        args = docopt.docopt(__doc__)

    # Get the search term we're using.
    search_term = args['<search_term>']

    # Set up the API parameters for the different types of media.
    APIParameters = collections.namedtuple(
        'APIParameters', ['size', 'media', 'entity', 'name'])

    if args['--ios']:
        parms = APIParameters(512, 'software', 'software',    'trackName')
    elif args['--mac']:
        parms = APIParameters(512, 'software', 'macSoftware', 'trackName')
    elif args['--album']:
        parms = APIParameters(600, 'music',    'album',       'collectionName')
    elif args['--film']:
        parms = APIParameters(600, 'movie',    'movie',       'trackName')
    elif args['--tv']:
        parms = APIParameters(600, 'tvShow',   'tvSeason',    'collectionName')
    elif args['--book']:
        parms = APIParameters(600, 'ebook',    'ebook',       'trackName')
    else:
        parms = APIParameters(600, '',         '',            '')

    return search_term, parms


def retrieve_itunes_api_results(search_term, api_params):
    """
    Given search terms and API parameters, call the iTunes API.
    Return a list of (thumb_url, img_url, name) tuples.
    """
    # Make the iTunes search call
    req_params = {
        'term': search_term,
        'media': api_params.media,
        'entity': api_params.entity,
    }
    req = requests.get(API_URL, params=req_params)

    # Read the results from the API
    raw_results = req.json()['results']

    # Clean up the results
    Result = collections.namedtuple('Result', ['thumb_url', 'img_url', 'name'])
    results = []
    for result in raw_results:
        thumb_url = result['artworkUrl100']
        img_url = thumb_url.replace('100x100', '{0}x{0}'.format(api_params.size))
        name = api_params.name
        results.append(Result(thumb_url, img_url, name.encode('utf8')))

    return results


def construct_html(search_term, results):
    """
    Given a list of results, construct the HTML page.
    """
    link_format = '<a href="{0.img_url}"><img src="{0.thumb_url}" alt="{0.name}" title="{0.name}"></a>'
    html_links = '\n'.join([link_format.format(result) for result in results])

    html_output = (
        '<html>'
        '<head><title>{search_term} pictures</title></head>'
        '<body>'
        '<h1>&ldquo;{search_term}&rdquo; pictures</h1>'
        '{html_links}'
        '</body>'
        '</html>'
    ).format(search_term=search_term, html_links=html_links)

    return html_output


def main():
    import sys

    # This is some special casing to allow the script to be called
    # by Alfred.  Since Alfred can only pass through a single query
    # string, and can't break it up, we do it for Alfred.  If the first
    # term of the search string is a filter argument, then use that --
    # otherwise just drop the --alfred flag.
    if (len(sys.argv) >= 2) and (sys.argv[1] == '--alfred'):
        try:
            media_type, search_term = sys.argv[2].split(' ', 1)
        except ValueError:
            media_type, search_term = None, sys.argv[2]

        if media_type in ('ios', 'mac', 'album', 'film', 'tv', 'book', 'narration'):
            sys.argv = [sys.argv[0], '--{0}'.format(media_type), search_term]
        else:
            sys.argv = [sys.argv[0], sys.argv[2]]

    # Parse the command-line arguments
    search_term, api_params = parse_command_line_args()

    # Given the API parameters for iTunes and the search term,
    # call the iTunes API and retrieve the results
    results = retrieve_itunes_api_results(search_term, api_params)

    # Render those results into an HTML string
    html_output = construct_html(search_term, results)

    # Write that string to an HTML file, and open it in the browser
    _, html_file = tempfile.mkstemp(suffix='.html')
    with open(html_file, 'w') as outfile:
        outfile.write(html_output)

    subprocess.check_call(['open', '-b', BROWSER, html_file])
