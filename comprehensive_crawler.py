#!/usr/bin/env python3
"""
Comprehensive Government Telecom Web Crawler & Extractor
--------------------------------------------------------
Crawls:
1. https://www.pta.gov.pk/sitemap (all 300+ sub-pages)
2. https://ntcert.pta.gov.pk
3. https://moitt.gov.pk
4. https://ignite.org.pk
5. https://fab.gov.pk

Extracts text, tables, and embedded JS data, and compiles exhaustive knowledge dossiers.
"""

import os
import re
import json
import time
import urllib.request
import urllib.parse
from concurrent.futures import ThreadPoolExecutor, as_completed
from bs4 import BeautifulSoup

HEADERS = {
    'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36'
}

def get_soup(url, timeout=12):
    try:
        req = urllib.request.Request(url, headers=HEADERS)
        html = urllib.request.urlopen(req, timeout=timeout).read().decode('utf-8', errors='ignore')
        return BeautifulSoup(html, 'html.parser'), html
    except Exception as e:
        return None, str(e)

def extract_page_data(url):
    soup, raw_html = get_soup(url)
    if not soup:
        return None
    
    title = soup.title.string.strip() if soup.title and soup.title.string else url
    
    # Extract any embedded JS data arrays (like const data = [...])
    embedded_data = []
    for m in re.finditer(r'const\s+(\w+)\s*=\s*(\[\s*\{.*?\}\s*\]);', raw_html, re.DOTALL):
        var_name = m.group(1)
        raw_arr = m.group(2)
        embedded_data.append(f"### Embedded Data ({var_name}):\n```javascript\n{raw_arr}\n```")
    
    # Extract tables
    tables_text = []
    for t in soup.find_all('table'):
        rows = []
        for tr in t.find_all('tr'):
            cols = [c.get_text(strip=True) for c in tr.find_all(['th', 'td'])]
            if cols:
                rows.append(" | ".join(cols))
        if rows:
            tables_text.append("\n".join(rows))
            
    # Clean scripts, styles, header, footer
    for s in soup(['script', 'style', 'header', 'footer', 'nav']):
        s.decompose()
        
    main_text = '\n'.join([line.strip() for line in soup.get_text().splitlines() if line.strip()])
    
    return {
        'url': url,
        'title': title,
        'text': main_text[:4000],  # keep top 4k characters per page
        'tables': tables_text,
        'embedded_data': embedded_data
    }

def collect_urls():
    urls = set()
    
    # 1. PTA Sitemap
    soup, _ = get_soup('https://www.pta.gov.pk/sitemap')
    if soup:
        for a in soup.find_all('a'):
            href = a.get('href')
            if href:
                if href.startswith('/'):
                    href = 'https://www.pta.gov.pk' + href
                if 'pta.gov.pk' in href and not any(ext in href.lower() for ext in ['.pdf', '.zip', '.jpg', '.png', '.mp4']):
                    urls.add(href.split('#')[0])
                    
    # 2. Key MoITT URLs
    moitt_urls = [
        'https://moitt.gov.pk/',
        'https://moitt.gov.pk/Policies',
        'https://moitt.gov.pk/Overview',
        'https://moitt.gov.pk/Detail/M2M4YWRkM2ItMjA1ZS00YTAxLTg4YjUtYzBmYTIyYmViZDUy',
        'https://moitt.gov.pk/Detail/NGI0NGJhYTUtMWM1Zi00YmU3LTlhN2YtZDZiNTFiYTkxYzU2'
    ]
    urls.update(moitt_urls)
    
    # 3. Key Ignite URLs
    ignite_urls = [
        'https://ignite.org.pk/',
        'https://ignite.org.pk/programs/',
        'https://ignite.org.pk/national-incubation-centers/',
        'https://ignite.org.pk/digiskills/',
        'https://ignite.org.pk/about-us/'
    ]
    urls.update(ignite_urls)

    # 4. Key FAB URLs
    fab_urls = [
        'https://fab.gov.pk/',
        'https://fab.gov.pk/about-us/',
        'https://fab.gov.pk/mandate-functions/',
        'https://fab.gov.pk/national-frequency-allocation-plan/',
        'https://fab.gov.pk/faqs/'
    ]
    urls.update(fab_urls)
    
    return list(urls)

def run_crawler():
    urls = collect_urls()
    print(f"Total target URLs to crawl: {len(urls)}")
    
    results = []
    with ThreadPoolExecutor(max_workers=6) as executor:
        future_to_url = {executor.submit(extract_page_data, u): u for u in urls}
        done_cnt = 0
        for future in as_completed(future_to_url):
            u = future_to_url[future]
            done_cnt += 1
            try:
                res = future.result()
                if res and len(res.get('text', '')) > 100:
                    results.append(res)
                    print(f"[{done_cnt}/{len(urls)}] Crawled: {res['title'][:50]} ({len(res['text'])} chars)")
            except Exception as e:
                print(f"[{done_cnt}/{len(urls)}] Failed {u}: {e}")
                
    print(f"\nSuccessfully extracted {len(results)} pages.")
    
    # Save raw dump
    out_dir = "/Users/anasmahmood/khanwco-repos/whatsapp-PTA/knowledge/01_Official_Government_Crawl"
    os.makedirs(out_dir, exist_ok=True)
    
    # Group results into thematic dossiers
    categorized = {
        'type_approval': [],
        'licensing_spectrum': [],
        'legislation_regulations': [],
        'stats_qos': [],
        'moitt_policies': [],
        'ignite_fab': [],
        'consumer_tariffs': []
    }
    
    for r in results:
        t = (r['title'] + " " + r['url']).lower()
        if 'type-approval' in t or 'type approval' in t or 'device' in t:
            categorized['type_approval'].append(r)
        elif 'license' in t or 'spectrum' in t or 'operator' in t or 'cmo' in t or 'ldi' in t:
            categorized['licensing_spectrum'].append(r)
        elif 'act' in t or 'regulation' in t or 'law' in t or 'tribunal' in t or 'determination' in t:
            categorized['legislation_regulations'].append(r)
        elif 'statistic' in t or 'indicator' in t or 'report' in t or 'qos' in t:
            categorized['stats_qos'].append(r)
        elif 'moitt' in t or 'policy' in t or 'digital pakistan' in t:
            categorized['moitt_policies'].append(r)
        elif 'ignite' in t or 'fab.gov.pk' in t or 'frequency' in t:
            categorized['ignite_fab'].append(r)
        else:
            categorized['consumer_tariffs'].append(r)
            
    # Write thematic dossiers
    def format_dossier(items, title):
        lines = [f"# {title}\n", f"> Comprehensive Official Government Extraction ({len(items)} official pages)\n\n"]
        for it in items:
            lines.append(f"## {it['title']}\n- **Source URL**: {it['url']}\n\n{it['text']}\n")
            if it['tables']:
                lines.append("\n### Official Tables:\n")
                for tb in it['tables']:
                    lines.append(tb + "\n")
            if it['embedded_data']:
                for ed in it['embedded_data']:
                    lines.append(ed + "\n")
            lines.append("\n---\n\n")
        return "".join(lines)
        
    dossier_map = [
        ('type_approval', 'PTA_TYPE_APPROVAL_AND_STANDARDS.md', 'PTA Type Approval, Technical Standards & Device Verification'),
        ('licensing_spectrum', 'PTA_OPERATOR_LICENSING_AND_SPECTRUM.md', 'PTA Operator Licensing Categories & Spectrum Management'),
        ('legislation_regulations', 'PTA_LEGISLATION_ACTS_AND_REGULATIONS.md', 'PTA Telecom Legislation, Statutory Acts & Regulatory Directives'),
        ('stats_qos', 'PTA_TELECOM_STATISTICS_AND_QOS.md', 'PTA Telecom Statistics, Quality of Service (QoS) & Industry Indicators'),
        ('moitt_policies', 'MOITT_POLICIES_AND_DIGITAL_PAKISTAN.md', 'Ministry of IT & Telecom (MoITT) National Policies & Initiatives'),
        ('ignite_fab', 'IGNITE_AND_FAB_TECHNOLOGY_SPECTRUM.md', 'Ignite National Technology Fund & Frequency Allocation Board (FAB)'),
        ('consumer_tariffs', 'PTA_CONSUMER_TARIFFS_AND_FACILITATION.md', 'PTA Consumer Tariffs, Complaint Resolution & Public Facilitation')
    ]
    
    for cat_key, fname, d_title in dossier_map:
        items = categorized.get(cat_key, [])
        if items:
            fpath = os.path.join(out_dir, fname)
            content = format_dossier(items, d_title)
            with open(fpath, 'w', encoding='utf-8') as f:
                f.write(content)
            print(f"Wrote {fname} ({len(items)} sections, {len(content)} bytes)")

if __name__ == "__main__":
    run_crawler()
