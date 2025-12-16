from typing import List, Dict, Optional, Any
from Bio import Entrez
import time

class PubMedSearcher:
    """Real PubMed API searcher using BioPython."""
    
    def __init__(self, email: str):
        """
        Initialize PubMed searcher.
        
        Args:
            email: Your email (required by NCBI)
        """
        Entrez.email = email
        self.rate_limit_delay = 0.34  # ~3 requests per second
    
    def search(self, query: str, max_results: int = 3) -> List[Dict[str, Any]]:
        """
        Search PubMed and return formatted results.
        
        Args:
            query: Search query
            max_results: Maximum number of results to return
            
        Returns:
            List of paper dictionaries with title, abstract, etc.
        """
        try:
            # Step 1: Search for article IDs
            search_handle = Entrez.esearch(
                db="pubmed",
                term=query,
                retmax=max_results,
                sort="relevance"
            )
            search_results = Entrez.read(search_handle)
            search_handle.close()
            
            id_list = search_results.get("IdList", [])
            
            if not id_list:
                return []
            
            # Rate limiting
            time.sleep(self.rate_limit_delay)
            
            # Step 2: Fetch full article details
            fetch_handle = Entrez.efetch(
                db="pubmed",
                id=id_list,
                rettype="abstract",
                retmode="xml"
            )
            articles = Entrez.read(fetch_handle)
            fetch_handle.close()
            
            # Step 3: Parse and format results
            results = []
            for article in articles['PubmedArticle']:
                try:
                    medline = article['MedlineCitation']
                    article_data = medline['Article']
                    
                    # Extract authors
                    authors = []
                    if 'AuthorList' in article_data:
                        for author in article_data['AuthorList'][:3]:  # First 3 authors
                            if 'LastName' in author and 'Initials' in author:
                                authors.append(f"{author['LastName']} {author['Initials']}")
                    
                    authors_str = ", ".join(authors)
                    if len(article_data.get('AuthorList', [])) > 3:
                        authors_str += ", et al."
                    
                    # Extract abstract
                    abstract = ""
                    if 'Abstract' in article_data:
                        abstract_texts = article_data['Abstract'].get('AbstractText', [])
                        if isinstance(abstract_texts, list):
                            abstract = " ".join(str(text) for text in abstract_texts)
                        else:
                            abstract = str(abstract_texts)
                    
                    # Extract journal info
                    journal = article_data.get('Journal', {}).get('Title', 'Unknown Journal')
                    year = article_data.get('Journal', {}).get('JournalIssue', {}).get('PubDate', {}).get('Year', 'N/A')
                    
                    # Extract PMID
                    pmid = str(medline['PMID'])
                    
                    results.append({
                        'title': article_data.get('ArticleTitle', 'No title'),
                        'abstract': abstract[:500] + "..." if len(abstract) > 500 else abstract,
                        'authors': authors_str or 'Unknown authors',
                        'journal': journal,
                        'year': year,
                        'pmid': pmid,
                        'url': f"https://pubmed.ncbi.nlm.nih.gov/{pmid}/"
                    })
                    
                except Exception as e:
                    print(f"Error parsing article: {e}")
                    continue
            
            return results
            
        except Exception as e:
            print(f"PubMed search error: {e}")
            return []
