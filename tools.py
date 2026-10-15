from langchain.tools import tool
from tavily import TavilyClient
import os
import requests
from bs4 import BeautifulSoup
from dotenv import load_dotenv
from rich import print


# Load environment variables
load_dotenv()

print("hello")


# Initialize Tavily
tavily = TavilyClient(
    api_key=os.getenv("TAVILY_API_KEY")
)


# -----------------------------
# Tool 1: Web Search
# -----------------------------
@tool
def web_scraper(query: str) -> str:
    """
    Searches the web using Tavily and returns titles,
    URLs, and snippets.
    """

    result = tavily.search(
        query=query,
        max_results=5
    )

    out = []

    for r in result["results"]:
        out.append(
            f"Title: {r['title']}\n"
            f"URL: {r['url']}\n"
            f"Snippet: {r['content'][:300]}"
        )

    return "\n-----\n".join(out)


# Call web search tool
#result = web_scraper.invoke(
 #   "What is the latest news on AI?"
#)

#print(result)


# -----------------------------
# Tool 2: URL Scraper
# -----------------------------
@tool
def scrape_url(url: str) -> str:
    """
    Scrape and return clean text content
    from a given URL for deeper reading.
    """

    try:
        resp = requests.get(
            url,
            timeout=8,
            headers={
                "User-Agent": "Mozilla/5.0"
            }
        )

        resp.raise_for_status()

        soup = BeautifulSoup(
            resp.text,
            "html.parser"
        )

        # Remove unnecessary HTML elements
        for tag in soup([
            "script",
            "style",
            "nav",
            "footer",
            "header",
            "aside"
        ]):
            tag.decompose()

        # Extract clean text
        text = soup.get_text(
            separator=" ",
            strip=True
        )

        return text[:3000]

    except Exception as e:
        return f"Could not scrape URL: {str(e)}"


# Call URL scraper
result = scrape_url.invoke(
    "https://newspulse.com.pk/en/"
)

print(result)