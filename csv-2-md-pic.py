import csv
import sys
import socket
import ssl
import os
import io
import time
from PIL import Image
from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.chrome.options import Options

# --- CONFIGURATION ---
REMOTE_PATH = "https://raw.githubusercontent.com/iraposeiro39/md-pics-repo/main/media"

def get_nslookup(domain):
    socket.setdefaulttimeout(2.0)
    try:
        results = socket.getaddrinfo(domain, None)
        ips = list(set([res[4][0] for res in results]))
        return "Non-authoritative answer:\n" + "\n".join([f"Name: {domain}\nAddress: {ip}" for ip in ips])
    except Exception:
        return "Nslookup Timed Out"

def get_ssl_info(domain):
    context = ssl.create_default_context()
    try:
        with socket.create_connection((domain, 443), timeout=2.0) as sock:
            with context.wrap_socket(sock, server_hostname=domain) as ssock:
                cert = ssock.getpeercert()
                issuer = dict(x[0] for x in cert['issuer'])
                org = issuer.get('organizationName', 'Unknown')
                return f"Issued by {org}"
    except Exception:
        return "No valid SSL/HTTPS found."

def take_screenshot(domain, ingested_at, folder="media"):
    clean_date = ingested_at.replace('/', '-').replace(':', '').replace(' ', '_')
    filename = f"{domain}_{clean_date}.jpg"
    filepath = os.path.join(folder, filename)
    
    options = Options()
    options.add_argument("--headless=new")
    options.add_argument("--no-sandbox")
    options.add_argument("--disable-dev-shm-usage")
    options.add_argument("--window-size=1280,720")
    options.add_argument("user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36")
    
    options.binary_location = "/usr/bin/chromium"
    service = Service(executable_path="/usr/bin/chromedriver")
    
    driver = None
    try:
        driver = webdriver.Chrome(service=service, options=options)
        driver.set_page_load_timeout(10) # More generous for GitHub hosting
        driver.get(f"http://{domain}")
        time.sleep(2) # Brief pause to allow content to render
        
        png_data = driver.get_screenshot_as_png()
        img = Image.open(io.BytesIO(png_data)).convert("RGB")
        img.save(filepath, "JPEG", quality=75)
        
        # Markdown points to the public GitHub Raw URL
        return f"![Screenshot]({REMOTE_PATH}/{filename})"
    except Exception:
        return "`Page not found.`"
    finally:
        if driver:
            driver.quit()

def csv_to_markdown(input_file, output_file):
    if not os.path.exists("media"):
        os.makedirs("media")

    try:
        with open(input_file, mode='r', encoding='utf-8') as f:
            reader = csv.DictReader(f, delimiter=';')
            with open(output_file, mode='w', encoding='utf-8') as out:
                for row in reader:
                    domain = row.get('domain_clean', '').strip()
                    ing = row.get('ingested_at', '').strip()
                    if not domain: continue

                    print(f"Analyzing {domain}...")
                    
                    ns_result = get_nslookup(domain)
                    ssl_result = get_ssl_info(domain)
                    screenshot_result = take_screenshot(domain, ing)

                    out.write(f"## Ingested_at\n`{ing}`\n\n")
                    out.write(f"## Domain_Clean\n`{domain}`\n\n")
                    out.write(f"## Web Site\n{screenshot_result}\n\n") 
                    out.write(f"## Certificate HTTPS\n```\n{ssl_result}\n```\n\n")
                    out.write(f"## IP (nslookup)\n```\n{ns_result}\n```\n\n")
                    out.write("---\n\n")
        
        print(f"\n1. Report saved to {output_file}")
        print(f"2. IMPORTANT: Push your 'media' folder to GitHub now.")
        print(f"3. Then paste the content of {output_file} into Outline.")

    except Exception as e:
        print(f"Error: {e}")

if __name__ == "__main__":
    if len(sys.argv) < 3:
        print("Usage: python3 csv-2-md.py <input.csv> <output.md>")
    else:
        csv_to_markdown(sys.argv[1], sys.argv[2])