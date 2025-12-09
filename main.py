import os
import math
import requests
import logging
from collections import Counter
from flask import Flask, send_file, request, make_response

# Configure logging
logging.basicConfig(filename='app.log', level=logging.INFO, 
                    format='%(asctime)s %(levelname)s: %(message)s',
                    datefmt='%Y-%m-%d %H:%M:%S')

app = Flask(__name__)

# Language colors are shared across themes for consistency
LANG_COLORS = {
    "Python": "#3572A5",
    "JavaScript": "#f1e05a",
    "HTML": "#e34c26",
    "CSS": "#563d7c",
    "TypeScript": "#2b7489",
    "Java": "#b07219",
    "Shell": "#89e051",
    "C++": "#f34b7d",
    "C": "#555555",
    "PHP": "#4F5D95",
    "Ruby": "#701516",
    "Go": "#00ADD8",
    "Other": "#ededed"
}

# Definição de múltiplos temas
THEMES = {
    "tokyonight": {
        "background": "#1a1b27",
        "title": "#70a5fd",
        "text": "#38bdae",
        "icon": "#bf91f3",
        "border": "#414868",
        "lang_colors": LANG_COLORS
    },
    "dracula": {
        "background": "#282a36",
        "title": "#ff79c6",
        "text": "#f8f8f2",
        "icon": "#bd93f9",
        "border": "#44475a",
        "lang_colors": LANG_COLORS
    },
    "gruvbox": {
        "background": "#282828",
        "title": "#fabd2f",
        "text": "#ebdbb2",
        "icon": "#d3869b",
        "border": "#504945",
        "lang_colors": LANG_COLORS
    },
    "onedark": {
        "background": "#282c34",
        "title": "#61afef",
        "text": "#abb2bf",
        "icon": "#c678dd",
        "border": "#3f444f",
        "lang_colors": LANG_COLORS
    }
}

def fetch_github_stats(username):
    '''Fetches user and repository stats from GitHub API.'''
    user_url = f"https://api.github.com/users/{username}"
    repos_url = f"https://api.github.com/users/{username}/repos?per_page=100&type=owner"
    
    try:
        logging.info(f"Fetching user data from: {user_url}")
        user_response = requests.get(user_url)
        logging.info(f"User data response status: {user_response.status_code}")
        user_response.raise_for_status()
        user_data = user_response.json()

        logging.info(f"Fetching repos data from: {repos_url}")
        repos_response = requests.get(repos_url)
        logging.info(f"Repos data response status: {repos_response.status_code}")
        repos_response.raise_for_status()
        repos_data = repos_response.json()

        total_stars = sum(repo['stargazers_count'] for repo in repos_data)
        total_forks = sum(repo['forks_count'] for repo in repos_data)
        total_repos = user_data.get('public_repos', 0)
        followers = user_data.get('followers', 0)

        stats = {
            "name": user_data.get('name') or user_data.get('login'),
            "Total Stars": total_stars,
            "Total Forks": total_forks,
            "Public Repos": total_repos,
            "Followers": followers
        }
        logging.info("Successfully fetched GitHub stats.")
        return stats

    except requests.exceptions.RequestException as e:
        logging.error(f"Error fetching GitHub data: {e}")
        return None

def create_stats_svg(stats, theme):
    '''Creates an SVG image for the GitHub stats.'''
    if not stats:
        return f'''<svg width="450" height="180" xmlns="http://www.w3.org/2000/svg">
                    <rect width="100%" height="100%" fill="{theme['background']}" rx="5" ry="5"/>
                    <text x="50%" y="50%" fill="#ff4a4a" text-anchor="middle" font-family="Arial, sans-serif">Failed to fetch GitHub stats</text>
                  </svg>'''

    stat_items_svg = ""
    y_position = 70
    
    for key, value in list(stats.items())[1:]: # Skip name
        stat_items_svg += f'''
        <g transform="translate(25, {y_position})">
            <text x="25" y="15" font-family="Arial, sans-serif" font-size="14" fill="{theme['text']}">
                <tspan font-weight="bold">{key}:</tspan> {value}
            </tspan>
        </g>
        '''
        y_position += 25

    svg = f'''
    <svg width="450" height="180" xmlns="http://www.w3.org/2000/svg">
        <rect width="448" height="178" x="1" y="1" rx="5" ry="5" fill="{theme['background']}" stroke="{theme['border']}" stroke-width="2"/>
        <g>
            <text x="25" y="35" font-family="Arial, sans-serif" font-size="18" font-weight="bold" fill="{theme['title']}">
                {stats['name']}\'s GitHub Stats
            </text>
        </g>
        {stat_items_svg}
    </svg>
    '''
    return svg.strip()

def fetch_top_languages(username):
    '''Fetches and aggregates language data from user\'s repos.'''
    repos_url = f"https://api.github.com/users/{username}/repos?per_page=100&type=owner"
    try:
        logging.info(f"Fetching repos for languages from: {repos_url}")
        repos_response = requests.get(repos_url)
        logging.info(f"Repos for languages response status: {repos_response.status_code}")
        repos_response.raise_for_status()
        repos = repos_response.json()
        
        lang_stats = Counter()
        for repo in repos:
            if repo['fork']:
                continue
            lang_url = repo["languages_url"]
            logging.info(f"Fetching language data from: {lang_url}")
            lang_response = requests.get(lang_url)
            logging.info(f"Language data response status: {lang_response.status_code} for repo {repo['name']}")
            lang_response.raise_for_status()
            for lang, size in lang_response.json().items():
                lang_stats[lang] += size
        
        logging.info(f"Successfully fetched and processed language data.")
        return lang_stats
    except requests.exceptions.RequestException as e:
        logging.error(f"Error fetching top languages: {e}")
        return None

def create_language_donut_chart_svg(langs, theme):
    "Creates a donut chart SVG for top languages."
    if not langs:
        return f'''<svg width="450" height="180" xmlns="http://www.w3.org/2000/svg">
                    <rect width="100%" height="100%" fill="{theme['background']}" rx="5" ry="5"/>
                    <text x="50%" y="50%" fill="#ff4a4a" text-anchor="middle" font-family="Arial, sans-serif">Failed to fetch language data</text>
                   </svg>'''

    total_size = sum(langs.values())
    top_langs = langs.most_common(6)

    cx, cy, r = 225, 90, 50
    inner_r = 30
    start_angle = -90
    
    paths = []
    legend_items = []

    for i, (lang, size) in enumerate(top_langs):
        percent = (size / total_size) * 100
        angle = (size / total_size) * 360
        end_angle = start_angle + angle

        large_arc_flag = 1 if angle > 180 else 0
        
        x1_outer = cx + r * math.cos(math.radians(start_angle))
        y1_outer = cy + r * math.sin(math.radians(start_angle))
        x2_outer = cx + r * math.cos(math.radians(end_angle))
        y2_outer = cy + r * math.sin(math.radians(end_angle))

        x1_inner = cx + inner_r * math.cos(math.radians(start_angle))
        y1_inner = cy + inner_r * math.sin(math.radians(start_angle))
        x2_inner = cx + inner_r * math.cos(math.radians(end_angle))
        y2_inner = cy + inner_r * math.sin(math.radians(end_angle))

        color = theme["lang_colors"].get(lang, theme["lang_colors"]['Other'])
        
        path_d = f"M {x1_outer} {y1_outer} A {r} {r} 0 {large_arc_flag} 1 {x2_outer} {y2_outer} L {x2_inner} {y2_inner} A {inner_r} {inner_r} 0 {large_arc_flag} 0 {x1_inner} {y1_inner} Z"
        paths.append(f'<path d="{path_d}" fill="{color}" />')
        
        legend_x = 20
        legend_y = 50 + i * 20
        legend_items.append(f'''
            <g transform="translate({legend_x}, {legend_y})">
                <rect width="10" height="10" fill="{color}" rx="2" ry="2"/>
                <text x="15" y="10" font-family="Arial, sans-serif" font-size="12" fill="{theme['text']}">
                    {lang} ({percent:.1f}%)
                </text>
            </g>
        ''')

        start_angle = end_angle

    svg = f'''
    <svg width="450" height="180" xmlns="http://www.w3.org/2000/svg">
        <rect width="448" height="178" x="1" y="1" rx="5" ry="5" fill="{theme['background']}" stroke="{theme['border']}" stroke-width="2"/>
        <text x="20" y="30" font-family="Arial, sans-serif" font-size="18" font-weight="bold" fill="{theme['title']}">Top Languages</text>
        <g transform="translate(200, 0)">
           {" ".join(paths)}
        </g>
        <g>
            {" ".join(legend_items)}
        </g>
    </svg>'''
    return svg.strip()


@app.route('/')
def index():
    return send_file('src/index.html')

@app.route("/api")
def api_stats():
    username = request.args.get('username')
    theme_name = request.args.get('theme', 'tokyonight')
    logging.info(f"Received request for stats for username: {username} with theme: {theme_name}")
    if not username:
        logging.warning("Username not provided.")
        return "Please provide a username, e.g., ?username=Domisnnet", 400

    theme = THEMES.get(theme_name.lower(), THEMES["tokyonight"])
    stats = fetch_github_stats(username)
    svg_content = create_stats_svg(stats, theme)
    
    response = make_response(svg_content)
    response.headers['Content-Type'] = 'image/svg+xml'
    response.headers['Cache-Control'] = 's-maxage=3600, stale-while-revalidate'
    
    return response

@app.route("/api/top-langs")
def api_top_langs():
    username = request.args.get('username')
    theme_name = request.args.get('theme', 'tokyonight')
    logging.info(f"Received request for top-langs for username: {username} with theme: {theme_name}")
    if not username:
        logging.warning("Username not provided for top-langs.")
        return "Please provide a username, e.g., ?username=Domisnnet", 400
        
    theme = THEMES.get(theme_name.lower(), THEMES["tokyonight"])
    langs = fetch_top_languages(username)
    svg_content = create_language_donut_chart_svg(langs, theme)
    
    response = make_response(svg_content)
    response.headers['Content-Type'] = 'image/svg+xml'
    response.headers['Cache-Control'] = 's-maxage=3600, stale-while-revalidate'
    
    return response

def main():
    app.run(port=int(os.environ.get('PORT', 8080)), host='0.0.0.0', debug=True)

if __name__ == "__main__":
    main()
