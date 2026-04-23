import urllib.request
import re

try:
    req = urllib.request.Request(
        'https://hospital-billing-system-vd3o.vercel.app/', 
        headers={'User-Agent': 'Mozilla/5.0'}
    )
    html = urllib.request.urlopen(req).read().decode('utf-8')
    m = re.search(r'assets/index-[^\.]+\.js', html)
    if not m:
        print("Could not find JS file in HTML")
        exit()
        
    js_url = 'https://hospital-billing-system-vd3o.vercel.app/' + m.group(0)
    print("Fetching:", js_url)
    
    req_js = urllib.request.Request(js_url, headers={'User-Agent': 'Mozilla/5.0'})
    js = urllib.request.urlopen(req_js).read().decode('utf-8')
    
    match = re.search(r'let (\w+)="([^"]+)"\|\|', js)
    if match:
        print("BASE_URL hardcoded by Vite:", match.group(2))
    else:
        print("Could not find BASE_URL pattern.")
        
    # Check if api.post('/auth/login') or similar is intact
    if 'endsWith("/api/v1")' in js or "endsWith('/api/v1')" in js:
        print("Success! /api/v1 auto-append logic IS present in Vercel JS.")
    else:
        print("WARNING: Auto-append logic is MISSING in Vercel JS!")
        
except Exception as e:
    print("Error:", e)
