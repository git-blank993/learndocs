import hashlib
import os
import time
from typing import List, Set, TypedDict
import typer
from bs4 import BeautifulSoup
import requests
from urllib.parse import urljoin



app = typer.Typer()

class LinkInfo(TypedDict):
    link:str
    depth:int

CLEAR_LINE = "\x1b[2K"
def create_folder(name:str):
    print(f"Creating folder {name}")
    try:
        os.mkdir(name)
    except FileExistsError:
        print(f"-> Folder {name} already exists")

def write_cache(project:str, name:str, txt:str):
    file_name =  os.path.join("cache", project, f"{name}.txt")
    try:
        with open(file_name, "w") as file:
            file.write(txt)
    except Exception as e:
        print("Error while writing to the file: ")
        print(e)

def get_cache(project:str, name:str) -> str | None:
    file_name =  os.path.join("cache", project, f"{name}.txt")
    try:
        with open(file_name, "r") as file:
            return file.read()
    except Exception:
        return None

def check_cache(project:str, name:str):
    file_name =  os.path.join("cache", project, f"{name}.txt")
    return os.path.exists(file_name)

def url_to_filename(url: str) -> str:
    """Creates a safe and unique filename from a URL using SHA256 hashing."""

    return hashlib.sha256(url.encode("utf-8")).hexdigest()

@app.command()
def fetch(project:str, original:str, force_recache:bool = typer.Option(False, "--force-recache", "-f", help="Recache even if already exists")):
    if not project:
        print("Name is required")
        raise typer.Exit()
    if not original:
        print("Original is required")
        raise typer.Exit()
    
    print("Setting up cache folders")
    create_folder("cache")
    create_folder(os.path.join("cache", project))

    print("Setting up the required environment")
    links: List[LinkInfo] = [
        {
            'link':original,
            'depth':0
        }
    ]
    visited = set([original])
    links_not_downloaded:Set[str] = set()
    max_links = 1000
    max_depth = 5
    n = 0

    while n < max_links and n < len(links):
        current = links[n]
        current_url = current['link']
        current_depth = current['depth']
        if current_depth < max_depth:
            n=n+1
        else:
            print("\n")
            print(5*"-", "Exceeded Maximum Depth: Stopping the service",5*"-")
            print(f"Processed {len(visited)} unique pages.")
            if len(links_not_downloaded) > 0:
                print(f"{links_not_downloaded} links not downloaded/processed")
            raise typer.Exit()
        filename = url_to_filename(current_url)
        print(f"{CLEAR_LINE}Processing: {current_url} (Depth: {current_depth})",end="\r")
        html_content = None

        if not force_recache and check_cache(project,filename):
            html_content = get_cache(project,filename)

        if not html_content:
            try:
                print(f"{CLEAR_LINE}Not in cache. Downloading...",end="\r")
                response = requests.get(current_url)
                response.raise_for_status()
                html_content = response.text
                write_cache(project,filename, str(html_content))
                time.sleep(2)
            except requests.RequestException as e:
                links_not_downloaded.add("abc")
                print(f"{CLEAR_LINE}Error while trying to fetch {current_url}",end="\r")
                print(f"{e}")
        else:
            print(f"{CLEAR_LINE}{current_url} found in cache.",end="\r")
        if html_content:
            soup = BeautifulSoup(html_content, 'html.parser')
            all_links = soup.find_all('a')
            
            for link in all_links:
                href = link.get('href')
                if href:
                    if "/cdn-cgi" in href:
                        continue
                    if "#" in href:
                        continue
                    complete_url = urljoin(original, str(href))
                    if original in complete_url and complete_url not in visited:
                        new_link:LinkInfo = {
                            'link': complete_url,
                            'depth': current_depth + 1
                        }
                        visited.add(complete_url)
                        links.append(new_link)
        else:
            print(f"No HTML Content {current_url}",end="\r")

    print("\n--- Crawl Complete ---")
    print(f"Processed {len(visited)} unique pages.")


if __name__ == "__main__":
    app()
