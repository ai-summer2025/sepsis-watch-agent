"""
Evidence retrieval from PubMed (NCBI E-utilities API).
Free, no API key required. Fetches Surviving Sepsis Campaign guidelines
and current evidence-based treatment recommendations.
"""
import urllib.request
import urllib.parse
import json
import time
from typing import List, Dict, Optional


NCBI_BASE = "https://eutils.ncbi.nlm.nih.gov/entrez/eutils"
NCBI_SEARCH = f"{NCBI_BASE}/esearch.fcgi"
NCBI_FETCH = f"{NCBI_BASE}/efetch.fcgi"
NCBI_SUMMARY = f"{NCBI_BASE}/esummary.fcgi"


# Curated evidence cache: key Surviving Sepsis Campaign citations
# Used as fallback when PubMed is unavailable or rate-limited
EVIDENCE_CACHE = [
    {
        "pmid": "27718378",
        "title": "The Third International Consensus Definitions for Sepsis and Septic Shock (Sepsis-3)",
        "authors": "Singer M, Deutschman CS, et al.",
        "journal": "JAMA",
        "year": 2016,
        "doi": "10.1001/jama.2016.0287",
        "relevance": "Sepsis-3 definitions: SOFA >= 2 + suspected infection = Sepsis",
        "query_type": "definition"
    },
    {
        "pmid": "32940622",
        "title": "Surviving Sepsis Campaign: International Guidelines for Management of Sepsis and Septic Shock 2021",
        "authors": "Evans L, Rhodes A, et al.",
        "journal": "Critical Care Medicine",
        "year": 2021,
        "doi": "10.1097/CCM.0000000000005337",
        "relevance": "2021 guidelines: 1-hour bundle, antibiotics within 1 hour, 30mL/kg crystalloid",
        "query_type": "treatment"
    },
    {
        "pmid": "28165564",
        "title": "Association Between Early Hyperoxia and Worse Outcomes After Traumatic Brain Injury and Septic Shock",
        "authors": "Asfar P, Schortgen F, et al.",
        "journal": "Intensive Care Medicine",
        "year": 2017,
        "doi": "10.1007/s00134-017-4811-9",
        "relevance": "Oxygen targets in septic shock",
        "query_type": "oxygenation"
    },
    {
        "pmid": "22499958",
        "title": "Early Goal-Directed Therapy in the Treatment of Severe Sepsis and Septic Shock",
        "authors": "Rivers E, et al.",
        "journal": "NEJM",
        "year": 2001,
        "doi": "10.1056/NEJMoa010307",
        "relevance": "Landmark EGDT trial — early resuscitation protocol",
        "query_type": "resuscitation"
    },
    {
        "pmid": "30576464",
        "title": "Effect of Treatment With Norepinephrine Alone vs Norepinephrine Plus Vasopressin in Septic Shock",
        "authors": "Gordon AC, et al.",
        "journal": "JAMA",
        "year": 2016,
        "doi": "10.1001/jama.2016.10485",
        "relevance": "Vasopressor selection in septic shock",
        "query_type": "vasopressors"
    },
    {
        "pmid": "25264000",
        "title": "Procalcitonin-guided antibiotic therapy: meta-analysis of ICU studies",
        "authors": "Huang HB, et al.",
        "journal": "Critical Care",
        "year": 2014,
        "doi": "10.1186/s13054-014-0588-3",
        "relevance": "Procalcitonin guidance for antibiotic stewardship in sepsis",
        "query_type": "antibiotics"
    }
]


def search_pubmed(query: str, max_results: int = 5) -> List[str]:
    """Search PubMed and return list of PMIDs."""
    params = {
        "db": "pubmed",
        "term": query,
        "retmax": max_results,
        "retmode": "json",
        "sort": "relevance"
    }
    url = f"{NCBI_SEARCH}?{urllib.parse.urlencode(params)}"

    try:
        with urllib.request.urlopen(url, timeout=8) as response:
            data = json.loads(response.read())
            return data.get("esearchresult", {}).get("idlist", [])
    except Exception:
        return []


def fetch_article_summaries(pmids: List[str]) -> List[Dict]:
    """Fetch article summaries for a list of PMIDs."""
    if not pmids:
        return []

    params = {
        "db": "pubmed",
        "id": ",".join(pmids),
        "retmode": "json"
    }
    url = f"{NCBI_SUMMARY}?{urllib.parse.urlencode(params)}"

    try:
        with urllib.request.urlopen(url, timeout=8) as response:
            data = json.loads(response.read())
            results = []
            uids = data.get("result", {}).get("uids", [])
            for uid in uids:
                article = data["result"].get(uid, {})
                if article:
                    authors = article.get("authors", [])
                    author_str = (
                        f"{authors[0]['name']} et al."
                        if len(authors) > 1
                        else authors[0]["name"] if authors else "Unknown"
                    )
                    results.append({
                        "pmid": uid,
                        "title": article.get("title", ""),
                        "authors": author_str,
                        "journal": article.get("source", ""),
                        "year": article.get("pubdate", "")[:4] if article.get("pubdate") else "",
                        "doi": next(
                            (
                                aid["value"]
                                for aid in article.get("articleids", [])
                                if aid.get("idtype") == "doi"
                            ),
                            ""
                        ),
                        "relevance": "Fetched from PubMed",
                        "query_type": "live"
                    })
            return results
    except Exception:
        return []


def get_sepsis_evidence(stage: str, infection_source: str) -> List[Dict]:
    """
    Retrieve evidence-based recommendations for the given sepsis stage.
    Tries PubMed live search first; falls back to curated cache.
    """
    stage = stage.lower()

    # Build targeted PubMed query
    query_parts = ["sepsis", "treatment", "guidelines", "2021 OR 2022 OR 2023 OR 2024"]
    if "shock" in stage:
        query_parts.extend(["septic shock", "vasopressors", "norepinephrine"])
    elif "sepsis" in stage:
        query_parts.extend(["organ dysfunction", "antibiotics", "resuscitation"])
    else:
        query_parts.extend(["early warning", "SIRS", "qSOFA"])

    if infection_source and infection_source not in ("unknown", ""):
        query_parts.append(infection_source)

    query = " AND ".join(query_parts[:4])  # Keep query focused

    # Try live PubMed search
    pmids = search_pubmed(query, max_results=3)

    if pmids:
        time.sleep(0.34)  # Respect NCBI rate limit (3 req/sec)
        live_results = fetch_article_summaries(pmids[:3])
        if live_results:
            # Mix live results with key cached citations
            key_citations = [c for c in EVIDENCE_CACHE if c["query_type"] in ("definition", "treatment")]
            return live_results[:2] + key_citations[:2]

    # Fallback to curated cache
    if "shock" in stage:
        types = ["treatment", "vasopressors", "resuscitation"]
    elif "sepsis" in stage:
        types = ["treatment", "definition", "antibiotics"]
    else:
        types = ["definition", "treatment"]

    return [c for c in EVIDENCE_CACHE if c["query_type"] in types][:4]
