import wikipedia
from ddgs import DDGS
import arxiv


def wiki_search(query):
    try:
        return wikipedia.summary(query, sentences=3)
    except:
        return "No Wikipedia result found."


def duck_search(query):
    with DDGS() as ddgs:
        results = ddgs.text(query, max_results=3)
        return "\n".join([r["body"] for r in results])


def arxiv_search(query):
    search = arxiv.Search(query=query, max_results=2)
    results = []
    for result in search.results():
        results.append(f"{result.title}\n{result.summary}")
    return "\n\n".join(results)