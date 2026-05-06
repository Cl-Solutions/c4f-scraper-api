from flask import Flask, request, jsonify
from flask_cors import CORS
import requests
from bs4 import BeautifulSoup
import re
import os

app = Flask(__name__)
CORS(app, origins="*")

HEADERS = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"}
PATHS = ["/impressum", "/kontakt", "/impressum.html", "/contact"]

def normalize(url):
    if not url: return None
    url = url.strip()
    if not url.startswith('http'): url = 'https://' + url
    return url

def get_text(url):
    url = normalize(url)
    if not url: return None
    try:
        r = requests.get(url, headers=HEADERS, timeout=8, allow_redirects=True)
        soup = BeautifulSoup(r.text, 'html.parser')
        for link in soup.find_all('a', href=True):
            href = str(link.get('href','')).lower()
            if 'impressum' in href or 'kontakt' in href:
                full = href if href.startswith('http') else '/'.join(url.split('/')[:3]) + '/' + href.lstrip('/')
                try:
                    r2 = requests.get(full, headers=HEADERS, timeout=8)
                    if r2.status_code == 200:
                        return BeautifulSoup(r2.text,'html.parser').get_text()
                except: continue
        base = '/'.join(url.split('/')[:3])
        for p in PATHS:
            try:
                r3 = requests.get(base+p, headers=HEADERS, timeout=6)
                if r3.status_code == 200:
                    t = BeautifulSoup(r3.text,'html.parser').get_text()
                    if len(t) > 100: return t
            except: continue
    except: pass
    return None

def get_emails(text):
    if not text: return []
    emails = list(dict.fromkeys([e.lower() for e in 
        re.findall(r'[a-zA-Z0-9._%+\-]+@[a-zA-Z0-9.\-]+\.[a-zA-Z]{2,}', text)
        if not any(x in e.lower() for x in ['example','muster','noreply','.png','.jpg','.gif'])]))
    emails.sort(key=lambda e: 0 if e.startswith('info@') else 1 if e.startswith('kontakt@') else 2)
    return emails

def get_owner(text):
    if not text: return None
    lines = [l.strip() for l in text.split('\n') if l.strip()]
    for i, line in enumerate(lines):
        if any(k in line.lower() for k in ['inhaber:','geschäftsführer:','vertreten durch:']):
            if ':' in line:
                after = line.split(':',1)[1].strip()
                if 3 < len(after) < 60: return after
            if i+1 < len(lines):
                nxt = lines[i+1]
                if 2 <= len(nxt.split()) <= 4: return nxt
    return None

@app.route('/')
def index():
    return jsonify({'status': 'C4F Scraper API running'})

@app.route('/health')
def health():
    return jsonify({'status': 'ok'})

@app.route('/scrape')
def scrape():
    url = request.args.get('url','')
    if not url: return jsonify({'error':'No URL'}), 400
    text = get_text(url)
    emails = get_emails(text)
    return jsonify({
        'email': emails[0] if emails else None,
        'alle_emails': emails,
        'inhaber': get_owner(text),
        'success': len(emails) > 0
    })

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=int(os.environ.get('PORT', 5000)))
