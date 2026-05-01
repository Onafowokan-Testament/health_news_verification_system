import time
from typing import Any, Dict, List, Optional

from Bio import Entrez

from logger import logger


class PubMedSearcher:
    """Real PubMed API searcher using BioPython."""

    def __init__(
        self,
        *,
        email: Optional[str] = None,
        api_key: Optional[str] = None,
        tool: Optional[str] = "MedVer",
        enabled: bool = False,
    ):
        """
        Initialize PubMed searcher.

        Args:
            email: Contact email for NCBI Entrez (recommended when enabled).
            api_key: Optional NCBI API key (raises Entrez rate limits).
            tool: Short application name reported to NCBI (recommended).
            enabled: When False, search() returns no results without calling Entrez.
        """
        has_email = bool((email or "").strip())
        self.enabled = bool(enabled) and has_email
        self.rate_limit_delay = 0.34  # ~3 requests per second

        if self.enabled:
            Entrez.email = (email or "").strip()
            if api_key:
                Entrez.api_key = api_key
            if tool:
                Entrez.tool = tool
            logger.info("PubMedSearcher initialized (Entrez email set, tool={})", tool)
        else:
            logger.info("PubMedSearcher disabled — skipping Entrez / PubMed calls.")

    def search(self, query: str, max_results: int = 3) -> List[Dict[str, Any]]:
        """
        Search PubMed and return formatted results.

        Args:
            query: Search query
            max_results: Maximum number of results to return

        Returns:
            List of paper dictionaries with title, abstract, etc.
        """
        if not self.enabled:
            logger.info("PubMed skipped (disabled or no email): %s", query)
            return []

        try:
            logger.info("PubMed search: %s (max_results=%d)", query, max_results)
            # Step 1: Search for article IDs
            search_handle = Entrez.esearch(
                db="pubmed", term=query, retmax=max_results, sort="relevance"
            )
            search_results = Entrez.read(search_handle)
            search_handle.close()

            id_list = search_results.get("IdList", [])

            if not id_list:
                logger.info("PubMed returned no results for: %s", query)
                return []

            # Rate limiting
            time.sleep(self.rate_limit_delay)

            # Step 2: Fetch full article details
            fetch_handle = Entrez.efetch(
                db="pubmed", id=id_list, rettype="abstract", retmode="xml"
            )
            articles = Entrez.read(fetch_handle)
            fetch_handle.close()

            # Step 3: Parse and format results
            results = []
            for article in articles["PubmedArticle"]:
                try:
                    medline = article["MedlineCitation"]
                    article_data = medline["Article"]

                    # Extract authors
                    authors = []
                    if "AuthorList" in article_data:
                        for author in article_data["AuthorList"][:3]:  # First 3 authors
                            if "LastName" in author and "Initials" in author:
                                authors.append(
                                    f"{author['LastName']} {author['Initials']}"
                                )

                    authors_str = ", ".join(authors)
                    if len(article_data.get("AuthorList", [])) > 3:
                        authors_str += ", et al."

                    # Extract abstract
                    abstract = ""
                    if "Abstract" in article_data:
                        abstract_texts = article_data["Abstract"].get(
                            "AbstractText", []
                        )
                        if isinstance(abstract_texts, list):
                            abstract = " ".join(str(text) for text in abstract_texts)
                        else:
                            abstract = str(abstract_texts)

                    # Extract journal info
                    journal = article_data.get("Journal", {}).get(
                        "Title", "Unknown Journal"
                    )
                    year = (
                        article_data.get("Journal", {})
                        .get("JournalIssue", {})
                        .get("PubDate", {})
                        .get("Year", "N/A")
                    )

                    # Extract PMID
                    pmid = str(medline["PMID"])

                    results.append(
                        {
                            "title": article_data.get("ArticleTitle", "No title"),
                            "abstract": (
                                abstract[:500] + "..."
                                if len(abstract) > 500
                                else abstract
                            ),
                            "authors": authors_str or "Unknown authors",
                            "journal": journal,
                            "year": year,
                            "pmid": pmid,
                            "url": f"https://pubmed.ncbi.nlm.nih.gov/{pmid}/",
                        }
                    )

                except Exception as e:
                    logger.exception("Error parsing article: %s", e)
                    continue

            logger.info("PubMed returned %d results for: %s", len(results), query)
            return results

        except Exception as e:
            logger.exception("PubMed search error: %s", e)
            return []
