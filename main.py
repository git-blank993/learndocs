import hashlib
import os
import time
from typing import List, Set, TypedDict
from urllib.parse import urljoin

import requests
import typer
from bs4 import BeautifulSoup
from chromadb import Metadata
from langchain_experimental.text_splitter import SemanticChunker
from langchain_huggingface import HuggingFaceEmbeddings
from markdownify import markdownify as md

from vectordb import add_data, create_collection

app = typer.Typer()


class LinkInfo(TypedDict):
    link: str
    depth: int


CLEAR_LINE = "\x1b[2K"


def create_folder(name: str) -> None:
    print(f"Creating folder {name}")
    try:
        os.mkdir(name)
    except FileExistsError:
        print(f"-> Folder {name} already exists")


def write_cache(project: str, name: str, txt: str) -> None:
    file_name = os.path.join("cache", project, f"{name}.txt")
    try:
        with open(file_name, "w") as file:
            file.write(txt)
    except Exception as e:
        print("Error while writing to the file: ")
        print(e)


def get_cache(project: str, name: str) -> str | None:
    file_name = os.path.join("cache", project, f"{name}.txt")
    try:
        with open(file_name, "r") as file:
            return file.read()
    except Exception:
        return None


def check_cache(project: str, name: str | None) -> bool:
    if not name:
        file_name = os.path.join("cache", project)
        return os.path.exists(file_name)
    file_name = os.path.join("cache", project, f"{name}.txt")
    return os.path.exists(file_name)


def url_to_filename(url: str) -> str:
    """Creates a safe and unique filename from a URL using SHA256 hashing."""

    return hashlib.sha256(url.encode("utf-8")).hexdigest()


@app.command()
def fetch(
    project: str,
    original: str,
    force_recache: bool = typer.Option(
        False, "--force-recache", "-f", help="Recache even if already exists"
    ),
):
    start = time.time()
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
    links: List[LinkInfo] = [{"link": original, "depth": 0}]
    visited = set([original])
    links_not_downloaded: Set[str] = set()
    max_links = 10
    max_depth = 1
    n = 0
    collection = create_collection(project)
    embeddings = HuggingFaceEmbeddings(model_name="all-MiniLM-L6-v2")
    text_splitter = SemanticChunker(embeddings=embeddings)
    while n < max_links and n < len(links):
        current = links[n]
        current_url = current["link"]
        current_depth = current["depth"]
        if current_depth < max_depth:
            n = n + 1
        else:
            print("\n")
            print(5 * "-", "Exceeded Maximum Depth: Stopping the service", 5 * "-")
            print(f"Processed {len(visited)} unique pages.")
            if len(links_not_downloaded) > 0:
                print(f"{len(links_not_downloaded)} links not downloaded/processed")
            raise typer.Exit()

        filename = url_to_filename(current_url)
        print(
            f"{CLEAR_LINE}Processing: {current_url} (Depth: {current_depth})", end="\r"
        )
        html_content = None

        if not force_recache and check_cache(project, filename):
            html_content = get_cache(project, filename)

        if not html_content:
            try:
                print(
                    f"{CLEAR_LINE} {current_url} Not in cache. Downloading...", end="\r"
                )
                response = requests.get(current_url)
                response.raise_for_status()
                html_content = response.text
                time.sleep(2)
            except requests.RequestException as e:
                links_not_downloaded.add(current_url)
                print(
                    f"{CLEAR_LINE}Error while trying to fetch {current_url}", end="\r"
                )
                print(f"{e}")
        else:
            print(f"{CLEAR_LINE}{current_url} found in cache.", end="\r")
        if html_content:
            soup = BeautifulSoup(html_content, "html.parser")

            # remove unnecessary tags keeping the content of the page clean
            for tag in [
                "nav",
                "footer",
                "header",
                "aside",
                "script",
                "style",
                "svg",
                "img",
            ]:
                for element in soup.find_all(tag):
                    element.decompose()
            write_cache(project, filename, str(soup))
            title = str(soup.title)
            llm_md = md(str(soup))

            docs = text_splitter.create_documents([llm_md])
            metadatas: List[Metadata] = []
            documents: List[str] = []
            ids: List[str] = []
            for i, line in enumerate(docs):
                metadatas.append(
                    {
                        "source_url": current_url,
                        "title": title,
                        "id": f"url_crawler_{title}_{n}_{i}",
                    }
                )
                documents.append(line.page_content)
                ids.append(f"url_crawler_{title}_{n}_{i}")
            add_data(collection, documents=documents, ids=ids, metadatas=metadatas)
            all_links = soup.find_all("a")

            for link in all_links:
                href = link.get("href")
                if href:
                    if "/cdn-cgi" in href:
                        continue
                    if "#" in href:
                        continue
                    complete_url = urljoin(original, str(href))
                    if original in complete_url and complete_url not in visited:
                        new_link: LinkInfo = {
                            "link": complete_url,
                            "depth": current_depth + 1,
                        }
                        visited.add(complete_url)
                        links.append(new_link)
        else:
            print(f"No HTML Content {current_url}", end="\r")
    end = time.time()
    print("\n--- Crawl Complete ---")
    print(
        f"Processed {len(visited)} unique pages. It took {end - start} seconds to complete."
    )


@app.command()
def ask(
    project: str,
    question: str,
    force_question: bool = typer.Option(
        False,
        "--force-question",
        "-f",
        help="Force use this question instead of using LLM generated ones",
    ),
):
    if not project:
        print("Project name is required")
        raise typer.Exit()
    if not check_cache(project, None):
        print("No such project exists")
        raise typer.Exit()
    print(f"Processing your question for {project} project")
    collection = create_collection(project)
    results = collection.query(query_texts=[question], n_results=2)
    print(results)


# Small Change to test GPG Key

if __name__ == "__main__":
    app()
