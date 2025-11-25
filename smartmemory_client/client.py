"""
SmartMemory HTTP Client

A clean, manually-maintained HTTP client for the SmartMemory Service API.

Features:
- JWT authentication with automatic token handling
- Type-safe operations with Pydantic models
- Comprehensive error handling
- Full API coverage (CRUD, search, ingestion, links, etc.)

For more information, see: https://github.com/smartmemory/smart-memory-client
"""

import logging
import os
from typing import Any, Dict, List, Optional, Union
import httpx
from datetime import datetime

# Use local model instead of core dependency
from smartmemory_client.models.memory_item import MemoryItem
from smartmemory_client.models.conversation import ConversationContextModel

logger = logging.getLogger(__name__)


class SmartMemoryClientError(Exception):
    """Base exception for SmartMemory client errors"""

    pass


class SmartMemoryClient:
    """
    SmartMemory HTTP Client

    A clean, manually-maintained HTTP client for the SmartMemory Service API.

    Features:
    - JWT authentication with automatic token handling
    - Type-safe operations with Pydantic models
    - Comprehensive error handling
    - Full API coverage

    Usage:
        ```python
        from smartmemory_client import SmartMemoryClient

        # With API key (JWT token)
        client = SmartMemoryClient(
            base_url="http://localhost:9001",
            api_key="your_jwt_token"
        )

        # Add memory
        item_id = client.add("This is a test memory")

        # Search
        results = client.search("test", top_k=5)

        # Ingest with full pipeline
        result = client.ingest(
            content="Complex content",
            extractor_name="llm",
            context={"key": "value"}
        )
        ```
    """
    def __init__(
        self,
        base_url: Optional[str] = None,
        api_key: Optional[str] = None,
        timeout: float = 30.0,
        verify_ssl: bool = True,
        team_id: Optional[str] = None,
    ):
        """
        Initialize SmartMemory client wrapper.

        Args:
            base_url: Base URL of the SmartMemory service
            api_key: JWT token for authentication (or set SMARTMEMORY_API_KEY env var)
            timeout: Request timeout in seconds
            verify_ssl: Whether to verify SSL certificates
        """
        # Determine base URL from parameter or environment
        if base_url is None:
            host = os.getenv("SMARTMEMORY_CLIENT_HOST") or os.getenv(
                "SMARTMEMORY_SERVER_HOST", "localhost"
            )
            if host in ("0.0.0.0", "::"):
                host = "localhost"
            try:
                port = int(os.getenv("SMARTMEMORY_SERVICES_PORT", "9001"))
            except Exception:
                port = 9001
            base_url = f"http://{host}:{port}"

        self.base_url = base_url
        self.timeout = timeout

        # Get API key from parameter or environment
        self.api_key = api_key or os.getenv("SMARTMEMORY_API_KEY")

        if self.api_key:
            logger.info(
                f"Found API key: {self.api_key[:20]}... (length: {len(self.api_key)})"
            )
        else:
            logger.warning("No API key found in environment or parameters")

        # Determine team ID from parameter or environment (default dev team)
        self.team_id = team_id or os.getenv("SMARTMEMORY_TEAM_ID") or "team_default_demo"
        self.verify_ssl = verify_ssl

        # Build default headers
        self.headers = {
            "Content-Type": "application/json",
            "X-Team-Id": self.team_id,
        }

        if self.api_key:
            self.headers["Authorization"] = f"Bearer {self.api_key}"
            logger.info(
                f"SmartMemoryClient initialized with authentication. "
                f"Base URL: {self.base_url}, Team ID: {self.team_id}"
            )
        else:
            logger.warning(
                "SmartMemoryClient initialized WITHOUT authentication - "
                "most endpoints will fail. Set SMARTMEMORY_API_KEY environment variable."
            )

    def health_check(self) -> Dict[str, Any]:
        """
        Check the health status of the SmartMemory service.

        Returns:
            Health status information

        Example:
            ```python
            status = client.health_check()
            print(status)  # {'status': 'healthy'}
            ```
        """
        try:
            response = httpx.get(
                f"{self.base_url}/health",
                headers=self.headers,
                timeout=self.timeout
            )
            response.raise_for_status()
            return {"status": "healthy"}
        except httpx.HTTPStatusError as e:
            raise SmartMemoryClientError(f"Health check failed: {e}")
        except Exception as e:
            raise SmartMemoryClientError(f"Health check failed: {str(e)}")

    def add(
        self,
        item: Union[str, MemoryItem, Dict[str, Any]],
        memory_type: str = "semantic",
        metadata: Optional[Dict[str, Any]] = None,
        use_pipeline: bool = True,
        conversation_context: Optional[Union[ConversationContextModel, Dict[str, Any]]] = None,
    ) -> str:
        """
        Add a memory item to the system.

        Args:
            item: Memory content (string) or MemoryItem object
            memory_type: Type of memory (semantic, episodic, procedural, working)
            metadata: Additional metadata for the memory
            use_pipeline: Whether to run full extraction pipeline (default: True)

        Returns:
            Memory item ID

        Example:
            ```python
            # Simple add
            item_id = client.add("Remember this")

            # With pipeline disabled (faster)
            item_id = client.add("Quick note", use_pipeline=False)

            # With metadata
            item_id = client.add(
                "Important fact",
                metadata={"source": "user", "priority": "high"},
                use_pipeline=True
            )
            ```
        """
        # Handle different input types
        if isinstance(item, str):
            content = item
        elif isinstance(item, MemoryItem):
            content = item.content
            memory_type = item.memory_type or memory_type
            metadata = metadata or item.metadata
        elif isinstance(item, dict):
            content = item.get("content", str(item))
            memory_type = item.get("memory_type", memory_type)
            metadata = metadata or item.get("metadata")
        else:
            content = str(item)

        body_dict = {
            "content": content,
            "memory_type": memory_type,
            "metadata": metadata or {},
            "use_pipeline": use_pipeline,
        }

        if conversation_context:
            if isinstance(conversation_context, ConversationContextModel):
                # Convert dataclass to dict
                from dataclasses import asdict
                body_dict["conversation_context"] = asdict(conversation_context)
            else:
                body_dict["conversation_context"] = conversation_context
        
        try:
            result = self._request("POST", "/memory/add", json_body=body_dict)
        except SmartMemoryClientError as e:
            if "401" in str(e):
                 logger.warning("Authentication required for add. Set SMARTMEMORY_API_KEY environment variable.")
            raise
        
        if not result:
            raise SmartMemoryClientError("Failed to add memory")
            
        if isinstance(result, dict):
            return result.get("id")
        elif hasattr(result, "id"):
            return result.id
        else:
            raise SmartMemoryClientError(f"Unexpected response format: {result}")

    def get(self, item_id: str) -> Optional[MemoryItem]:
        """
        Retrieve a memory item by ID.

        Args:
            item_id: Memory item ID

        Returns:
            MemoryItem object or None if not found

        Example:
            ```python
            memory = client.get("item_123")
            if memory:
                print(memory.content)
            ```
        """
        try:
            response = self._request("GET", f"/memory/{item_id}")

            if response is None:
                return None

            # Convert response to MemoryItem
            return MemoryItem(
                item_id=response.get("item_id", item_id),
                content=response.get("content", ""),
                memory_type=response.get("memory_type", "semantic"),
                metadata=response.get("metadata", {}),
            )
        except Exception as e:
            logger.error(f"Error getting memory {item_id}: {e}")
            return None

    def search(
        self,
        query: str,
        top_k: int = 5,
        memory_type: Optional[str] = None,
        use_ssg: Optional[bool] = None,
    ) -> List[MemoryItem]:
        """
        Search for memory items using semantic matching.

        Args:
            query: Search query
            top_k: Maximum number of results
            memory_type: Type of memory to search (optional)
            use_ssg: Use Similarity Graph Traversal for better multi-hop reasoning (optional)
                    If None, uses config default. If True, uses SSG. If False, uses basic vector search.

        Returns:
            List of MemoryItem objects

        Example:
            ```python
            # Simple search
            results = client.search("AI concepts", top_k=10)

            # Search with SSG for better multi-hop reasoning
            results = client.search("AI concepts", top_k=10, use_ssg=True)

            # Search specific memory type
            results = client.search("conversation", memory_type="episodic")

            for item in results:
                print(f"{item.item_id}: {item.content}")
            ```

        Note:
            user_id is automatically determined from the JWT token.
            No need to pass it as a parameter.
        """
        # The FastAPI route expects a top-level SearchRequest body
        body_dict: Dict[str, Any] = {
            "query": query,
            "top_k": top_k,
        }
        if memory_type is not None:
            body_dict["memory_type"] = memory_type
        if use_ssg is not None:
            body_dict["use_ssg"] = use_ssg

        response_data = self._request("POST", "/memory/search", json_body=body_dict)

        if not response_data:
            return []

        # Convert response to MemoryItem objects
        results: List[MemoryItem] = []
        response_list = (
            response_data if isinstance(response_data, list) else [response_data]
        )

        for item_data in response_list:
            if hasattr(item_data, "to_dict"):
                item_dict = item_data.to_dict()
            elif isinstance(item_data, dict):
                item_dict = item_data
            else:
                continue

            memory_item = MemoryItem(
                item_id=item_dict.get("item_id", ""),
                content=item_dict.get("content", ""),
                memory_type=item_dict.get("memory_type", "semantic"),
                metadata=item_dict.get("metadata", {}),
            )

            # Add score if available
            if "score" in item_dict:
                memory_item.score = item_dict["score"]

            results.append(memory_item)

        return results
    
    def search_advanced(
        self,
        query: str,
        algorithm: str = "query_traversal",
        max_results: int = 15,
        use_ssg: bool = True,
    ) -> List[MemoryItem]:
        """
        Advanced search using Similarity Graph Traversal (SSG) algorithms.
        
        SSG provides superior multi-hop reasoning and contextual retrieval compared to basic vector search.
        
        Args:
            query: Search query
            algorithm: SSG algorithm to use:
                      - "query_traversal": Best for general queries (100% test pass, 0.91 precision/recall)
                      - "triangulation_fulldim": Best for high precision (highest faithfulness)
            max_results: Maximum number of results to return
            use_ssg: Enable SSG traversal (vs basic vector search)
        
        Returns:
            List of MemoryItem objects
        
        Example:
            ```python
            # Best for general queries
            results = client.search_advanced("AI concepts", algorithm="query_traversal")
            
            # Best for high precision factual queries
            results = client.search_advanced("specific fact", algorithm="triangulation_fulldim")
            
            # Disable SSG (fallback to basic search)
            results = client.search_advanced("query", use_ssg=False)
            
            for item in results:
                print(f"{item.item_id}: {item.content}")
            ```
        
        Note:
            Based on research: github.com/glacier-creative-git/similarity-graph-traversal-semantic-rag-research
        """
        payload = {
            "query": query,
            "algorithm": algorithm,
            "max_results": max_results,
            "use_ssg": use_ssg
        }
        
        data = self._request("POST", "/memory/search/advanced", json_body=payload)
        
        # Parse response
        results = []
        for item_dict in data.get("results", []):
            memory_item = MemoryItem(
                item_id=item_dict.get("item_id", ""),
                content=item_dict.get("content", ""),
                memory_type=item_dict.get("memory_type", "semantic"),
                metadata=item_dict.get("metadata", {}),
            )
            results.append(memory_item)
        
        return results

    def update(
        self, item_id: str, content: Optional[str] = None, metadata: Optional[Dict[str, Any]] = None
    ) -> bool:
        """
        Update a memory item.

        Args:
            item_id: Memory item ID
            content: New content (optional)
            metadata: New metadata (optional)

        Returns:
            True if successful

        Example:
            ```python
            # Update content
            client.update("item_123", content="Updated content")

            # Update metadata
            client.update("item_123", metadata={"updated": True})

            # Update both
            client.update("item_123", content="New content", metadata={"version": 2})
            ```
        """
        body = {}
        if content is not None:
            body["content"] = content
        if metadata is not None:
            body["metadata"] = metadata

        try:
            self._request("PUT", f"/memory/{item_id}", json_body=body)
            return True
        except Exception:
            return False

    def delete(self, item_id: str) -> bool:
        """
        Delete a memory item.

        Args:
            item_id: Memory item ID

        Returns:
            True if successful

        Example:
            ```python
            if client.delete("item_123"):
                print("Memory deleted")
            ```
        """
        try:
            self._request("DELETE", f"/memory/{item_id}")
            return True
        except Exception:
            return False

    def ingest(
        self,
        content: str,
        extractor_name: str = "llm",
        context: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        """
        Ingest content with full extraction and enrichment pipeline.

        Args:
            content: Content to ingest
            extractor_name: Name of the extractor to use (default: "llm")
            context: Additional context information

        Returns:
            Ingestion result with item_id, user_id, tenant_id, queued status

        Example:
            ```python
            # Ingest conversation
            result = client.ingest(
                content="User: Hello\nAssistant: Hi there!",
                extractor_name="llm",
                context={"conversation_id": "123", "timestamp": "2025-11-07"}
            )

            print(f"Ingested: {result['item_id']}")
            ```

        Note:
            user_id is automatically determined from the JWT token.
        """
        body_dict = {
            "content": content,
            "extractor_name": extractor_name,
            "context": context or {},
        }
        
        try:
            return self._request("POST", "/memory/ingest", json_body=body_dict)
        except Exception as e:
            raise SmartMemoryClientError(f"Failed to ingest content: {str(e)}")

    def link(
        self, source_id: str, target_id: str, link_type: str = "RELATED"
    ) -> bool:
        """
        Create a link between two memory items.

        Args:
            source_id: Source memory item ID
            target_id: Target memory item ID
            link_type: Type of link (RELATED, CAUSES, FOLLOWS, etc.)

        Returns:
            True if successful

        Example:
            ```python
            # Create relationship
            client.link("concept_1", "concept_2", link_type="RELATED")
            client.link("cause_id", "effect_id", link_type="CAUSES")
            ```
        """
        body_dict = {
            "source_id": source_id,
            "target_id": target_id,
            "link_type": link_type,
        }
        
        try:
            self._request("POST", "/memory/link", json_body=body_dict)
            return True
        except Exception as e:
            # Link endpoint may not exist or be disabled - fail gracefully
            logger.debug(f"Link operation not supported or failed: {e}")
            return False

    def add_edge(
        self,
        source_id: str,
        target_id: str,
        relation_type: str,
        properties: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """
        Add a direct edge between two nodes in the graph.

        This is a lower-level operation than link() - it creates a raw edge
        with custom properties. Use link() for standard memory linking.

        Args:
            source_id: Source node ID
            target_id: Target node ID
            relation_type: Type of relation/edge
            properties: Optional edge properties

        Returns:
            Dict with edge creation result

        Example:
            ```python
            result = client.add_edge(
                source_id="node_1",
                target_id="node_2",
                relation_type="INFLUENCES",
                properties={"weight": 0.8, "confidence": 0.95}
            )
            ```
        """
        body = {
            "source_id": source_id,
            "target_id": target_id,
            "relation_type": relation_type,
            "properties": properties or {}
        }
        return self._request("POST", "/memory/edge", json_body=body)

    def get_neighbors(self, item_id: str) -> List[Dict[str, Any]]:
        """
        Get neighboring memory items (linked items).

        Args:
            item_id: Memory item ID

        Returns:
            List of neighbor information

        Example:
            ```python
            neighbors = client.get_neighbors("item_123")
            for neighbor in neighbors:
                print(f"{neighbor['id']}: {neighbor['relation']}")
            ```
        """
        # Make direct HTTP request
        import httpx
        url = f"{self._client._base_url}/memory/{item_id}/neighbors"
        headers = {"X-Team-Id": self.team_id}
        
        # Add auth token if available
        if hasattr(self._client, 'token') and self._client.token:
            prefix = getattr(self._client, 'prefix', 'Bearer')
            headers["Authorization"] = f"{prefix} {self._client.token}"
        
        try:
            http_response = httpx.get(url, headers=headers, timeout=30.0)
            http_response.raise_for_status()
            result = http_response.json()
            return result.get("neighbors", [])
        except httpx.HTTPStatusError as e:
            logger.warning(f"Failed to get neighbors: {e}")
            return []
        except Exception as e:
            logger.warning(f"Error getting neighbors: {e}")
            return []

    def get_summary(self) -> Dict[str, Any]:
        """
        Get summary statistics about the memory system.

        Returns:
            Summary statistics

        Example:
            ```python
            summary = client.get_summary()
            print(f"Total memories: {summary.get('total_count', 0)}")
            ```
        """
        return self._request("GET", "/memory/summary")

    def enrich(
        self, item_id: str, routines: Optional[List[str]] = None
    ) -> Dict[str, Any]:
        """
        Enrich a memory item with additional processing.

        Args:
            item_id: Memory item ID
            routines: List of enrichment routines to run

        Returns:
            Enrichment result

        Example:
            ```python
            result = client.enrich("item_123", routines=["sentiment", "keywords"])
            ```
        """
        body = {"item_id": item_id, "routines": routines or []}
        return self._request("POST", f"/memory/{item_id}/enrich", json_body=body)

    def personalize(
        self,
        traits: Optional[Dict[str, Any]] = None,
        preferences: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        """
        Update personalization settings for the authenticated user.

        Args:
            traits: User traits
            preferences: User preferences

        Returns:
            Personalization result

        Example:
            ```python
            result = client.personalize(
                traits={"learning_style": "visual"},
                preferences={"language": "en", "complexity": "advanced"}
            )
            ```

        Note:
            user_id is automatically determined from the JWT token.
        """
        body = {"traits": traits or {}, "preferences": preferences or {}}
        return self._request("POST", "/memory/personalize", json_body=body)

    def provide_feedback(
        self, feedback: Dict[str, Any], memory_type: str = "semantic"
    ) -> Dict[str, Any]:
        """
        Provide feedback to improve the memory system.

        Args:
            feedback: Feedback information
            memory_type: Type of memory to update

        Returns:
            Feedback processing result

        Example:
            ```python
            client.provide_feedback(
                feedback={"rating": 5, "comment": "Great result"},
                memory_type="semantic"
            )
            ```
        """
        body = {"feedback": feedback, "memory_type": memory_type}
        return self._request("POST", "/memory/feedback", json_body=body)

    def cluster(
        self,
        distance_threshold: float = 0.1,
        dry_run: bool = False
    ) -> Dict[str, Any]:
        """
        Run entity clustering/deduplication for the workspace.
        
        Args:
            distance_threshold: Similarity threshold (0.0-1.0, default 0.1)
            dry_run: If true, preview clusters without merging
            
        Returns:
            Clustering results (merged_count, clusters_found, etc.)
        """
        # Make direct HTTP request
        import httpx
        url = f"{self.base_url}/clustering/run"
        headers = {"X-Team-Id": self.team_id}
        
        if self.api_key:
            headers["Authorization"] = f"Bearer {self.api_key}"
            
        params = {
            "distance_threshold": distance_threshold,
            "dry_run": dry_run
        }
        
        try:
            http_response = httpx.post(url, params=params, headers=headers, timeout=60.0)
            http_response.raise_for_status()
            return http_response.json()
        except httpx.HTTPStatusError as e:
            raise SmartMemoryClientError(f"Clustering failed: {e}")
        except Exception as e:
            raise SmartMemoryClientError(f"Clustering failed: {str(e)}")

    def get_clustering_stats(self) -> Dict[str, Any]:
        """
        Get clustering statistics for the workspace.
        
        Returns:
            Clustering statistics
        """
        # Make direct HTTP request
        import httpx
        url = f"{self.base_url}/clustering/stats"
        headers = {"X-Team-Id": self.team_id}
        
        if self.api_key:
            headers["Authorization"] = f"Bearer {self.api_key}"
            
        try:
            http_response = httpx.get(url, headers=headers, timeout=30.0)
            http_response.raise_for_status()
            return http_response.json()
        except httpx.HTTPStatusError as e:
            raise SmartMemoryClientError(f"Failed to get clustering stats: {e}")
        except Exception as e:
            raise SmartMemoryClientError(f"Failed to get clustering stats: {str(e)}")

    def ground(
        self,
        item_id: str,
        source_url: str,
        validation: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """
        Ground a memory item to an external source for provenance.
        
        Args:
            item_id: Memory item ID
            source_url: URL of the source
            validation: Optional validation data
            
        Returns:
            Result message
        """
        # Make direct HTTP request
        import httpx
        url = f"{self.base_url}/memory/{item_id}/ground"
        headers = {
            "Content-Type": "application/json",
            "X-Team-Id": self.team_id
        }
        
        if self.api_key:
            headers["Authorization"] = f"Bearer {self.api_key}"
            
        body = {
            "item_id": item_id,
            "source_url": source_url,
            "validation": validation
        }
        
        try:
            http_response = httpx.post(url, json=body, headers=headers, timeout=30.0)
            http_response.raise_for_status()
            return http_response.json()
        except httpx.HTTPStatusError as e:
            raise SmartMemoryClientError(f"Grounding failed: {e}")
        except Exception as e:
            raise SmartMemoryClientError(f"Grounding failed: {str(e)}")

    def get_summarize_prompt(self, item_id: str) -> Dict[str, Any]:
        """
        Generate a prompt template for summarizing a memory item.
        
        Args:
            item_id: Memory item ID
            
        Returns:
            Prompt template and metadata
        """
        # Make direct HTTP request
        import httpx
        url = f"{self.base_url}/memory/{item_id}/prompt/summarize"
        headers = {"X-Team-Id": self.team_id}
        
        if self.api_key:
            headers["Authorization"] = f"Bearer {self.api_key}"
            
        try:
            http_response = httpx.get(url, headers=headers, timeout=30.0)
            http_response.raise_for_status()
            return http_response.json()
        except httpx.HTTPStatusError as e:
            raise SmartMemoryClientError(f"Failed to get summarize prompt: {e}")
        except Exception as e:
            raise SmartMemoryClientError(f"Failed to get summarize prompt: {str(e)}")

    def get_analyze_prompt(self, item_id: str) -> Dict[str, Any]:
        """
        Generate a prompt template for analyzing memory connections.
        
        Args:
            item_id: Memory item ID
            
        Returns:
            Prompt template and metadata
        """
        # Make direct HTTP request
        import httpx
        url = f"{self.base_url}/memory/{item_id}/prompt/analyze"
        headers = {"X-Team-Id": self.team_id}
        
        if self.api_key:
            headers["Authorization"] = f"Bearer {self.api_key}"
            
        try:
            http_response = httpx.get(url, headers=headers, timeout=30.0)
            http_response.raise_for_status()
            return http_response.json()
        except httpx.HTTPStatusError as e:
            raise SmartMemoryClientError(f"Failed to get analyze prompt: {e}")
        except Exception as e:
            raise SmartMemoryClientError(f"Failed to get analyze prompt: {str(e)}")

    def ingest_full(
        self,
        content: str,
        extractor_name: str = "llm",
        context: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        """
        Ingest content with full synchronous entity/relation extraction pipeline.
        
        Args:
            content: Content to ingest
            extractor_name: Name of the extractor to use (default: "llm")
            context: Additional context information
            
        Returns:
            Full ingestion result with entities and relations
        """
        # Make direct HTTP request
        import httpx
        url = f"{self.base_url}/memory/ingest/full"
        headers = {
            "Content-Type": "application/json",
            "X-Team-Id": self.team_id,
        }
        
        if self.api_key:
            headers["Authorization"] = f"Bearer {self.api_key}"
        
        body_dict = {
            "content": content,
            "extractor_name": extractor_name,
            "context": context or {},
        }
        
        try:
            http_response = httpx.post(url, json=body_dict, headers=headers, timeout=60.0)
            http_response.raise_for_status()
            return http_response.json()
        except httpx.HTTPStatusError as e:
            raise SmartMemoryClientError(f"Failed to ingest content: {e}")
        except Exception as e:
            raise SmartMemoryClientError(f"Failed to ingest content: {str(e)}")

    # ============================================================================
    # Admin & Monitoring
    # ============================================================================

    def get_orphaned_notes(self) -> Dict[str, Any]:
        """Find orphaned notes (notes with no connections)."""
        return self._request("GET", "/memory/admin/orphaned-notes")

    def prune_memories(
        self, strategy: str = "old", days: int = 365, dry_run: bool = True
    ) -> Dict[str, Any]:
        """Prune old or unused memories."""
        params = {"strategy": strategy, "days": days, "dry_run": dry_run}
        return self._request("POST", "/memory/admin/prune", params=params)

    def find_old_notes(self, days: int = 365) -> Dict[str, Any]:
        """Find notes older than N days."""
        return self._request("GET", "/memory/admin/old-notes", params={"days": days})

    def self_monitor(self) -> Dict[str, Any]:
        """Get self-monitoring metrics."""
        return self._request("GET", "/memory/admin/self-monitor")

    def get_system_stats(self) -> Dict[str, Any]:
        """Get comprehensive system statistics."""
        return self._request("GET", "/memory/admin/stats")

    def reflect(self, top_k: int = 5) -> Dict[str, Any]:
        """
        Reflect on memory patterns and insights.

        Analyzes memory content to identify patterns, themes,
        and potential connections.

        Args:
            top_k: Number of top items to reflect on

        Returns:
            Dict with reflection results including themes, patterns, suggestions

        Example:
            ```python
            reflection = client.reflect(top_k=10)
            print(reflection["reflection"]["themes"])
            ```
        """
        return self._request("GET", "/memory/admin/reflect", params={"top_k": top_k})

    def summarize_memories(self, max_items: int = 10) -> Dict[str, Any]:
        """
        Generate a summary of memory contents.

        Creates a high-level overview of stored memories,
        including key topics, recent additions, and knowledge distribution.

        Args:
            max_items: Maximum items to include in summary

        Returns:
            Dict with summary including topic distribution, memory type breakdown

        Example:
            ```python
            summary = client.summarize_memories(max_items=20)
            print(summary["summary"]["topic_distribution"])
            ```
        """
        return self._request("GET", "/memory/admin/summarize", params={"max_items": max_items})

    # ============================================================================
    # Agents
    # ============================================================================

    def create_agent(
        self,
        name: str,
        description: Optional[str] = None,
        agent_config: Optional[Dict[str, Any]] = None,
        roles: Optional[List[str]] = None
    ) -> Dict[str, Any]:
        """Create a new AI agent."""
        body = {
            "name": name,
            "description": description,
            "agent_config": agent_config or {},
            "roles": roles or ["user"]
        }
        return self._request("POST", "/agents", json_body=body)

    def list_agents(self) -> List[Dict[str, Any]]:
        """List all agents in the current tenant."""
        return self._request("GET", "/agents")

    def get_agent(self, agent_id: str) -> Dict[str, Any]:
        """Get details of a specific agent."""
        return self._request("GET", f"/memory/agents/{agent_id}")

    def delete_agent(self, agent_id: str) -> None:
        """Delete (deactivate) an agent."""
        self._request("DELETE", f"/agents/{agent_id}")

    # ============================================================================
    # Analytics
    # ============================================================================

    def get_analytics_status(self) -> Dict[str, Any]:
        """Return analytics feature status."""
        return self._request("GET", "/memory/analytics/status")

    def detect_drift(self, time_window_days: int = 30) -> Dict[str, Any]:
        """Run concept drift detection."""
        return self._request("GET", "/analytics/drift", params={"time_window_days": time_window_days})

    def detect_bias(
        self,
        protected_attributes: Optional[List[str]] = None,
        sentiment_analysis: Optional[bool] = None,
        topic_analysis: Optional[bool] = None
    ) -> Dict[str, Any]:
        """Run bias detection."""
        body = {
            "protected_attributes": protected_attributes,
            "sentiment_analysis": sentiment_analysis,
            "topic_analysis": topic_analysis
        }
        return self._request("POST", "/analytics/bias", json_body=body)

    # ============================================================================
    # API Keys
    # ============================================================================

    def create_api_key(
        self,
        name: str,
        scopes: Optional[List[str]] = None,
        expires_in_days: Optional[int] = None
    ) -> Dict[str, Any]:
        """Create a new API key."""
        body = {
            "name": name,
            "scopes": scopes or ["read:memories"],
            "expires_in_days": expires_in_days
        }
        return self._request("POST", "/api-keys", json_body=body)

    def list_api_keys(self) -> List[Dict[str, Any]]:
        """List all API keys."""
        return self._request("GET", "/api-keys")

    def revoke_api_key(self, key_id: str) -> None:
        """Revoke (delete) an API key."""
        self._request("DELETE", f"/api-keys/{key_id}")

    # ============================================================================
    # Auth
    # ============================================================================

    def signup(self, email: str, password: str, full_name: Optional[str] = None) -> Dict[str, Any]:
        """Register a new user."""
        body = {"email": email, "password": password, "full_name": full_name}
        return self._request("POST", "/auth/signup", json_body=body)

    def login(self, username: str, password: str) -> Dict[str, Any]:
        """Login to get access token."""
        # Service expects 'email', so we map username to email
        data = {"email": username, "password": password}
        response = self._request("POST", "/auth/login", json_body=data)
        
        # Handle both flat and nested token responses
        if response:
            if "access_token" in response:
                self.api_key = response["access_token"]
            elif "tokens" in response and "access_token" in response["tokens"]:
                self.api_key = response["tokens"]["access_token"]
            
            # Update team_id if available in user info
            if "user" in response and "default_team_id" in response["user"]:
                self.team_id = response["user"]["default_team_id"]
                self.headers["X-Team-Id"] = self.team_id
                
        return response

    def refresh_token(self, refresh_token: str) -> Dict[str, Any]:
        """Refresh access token."""
        body = {"refresh_token": refresh_token}
        result = self._request("POST", "/auth/refresh", json_body=body)
        if "access_token" in result:
            self.api_key = result["access_token"]
        return result

    def logout(self) -> None:
        """Logout user."""
        self._request("POST", "/auth/logout")
        self.api_key = None

    def get_me(self) -> Dict[str, Any]:
        """Get current authenticated user info."""
        return self._request("GET", "/auth/me")

    def logout_all(self) -> None:
        """Logout from all devices."""
        self._request("POST", "/auth/logout-all")
        self.api_key = None

    def update_llm_keys(
        self,
        openai_key: Optional[str] = None,
        anthropic_key: Optional[str] = None,
        groq_key: Optional[str] = None
    ) -> Dict[str, Any]:
        """Update user's LLM provider API keys."""
        body = {
            "openai_key": openai_key,
            "anthropic_key": anthropic_key,
            "groq_key": groq_key
        }
        return self._request("PUT", "/auth/llm-keys", json_body=body)

    def get_llm_keys(self) -> Dict[str, Any]:
        """Get user's LLM provider API keys (masked)."""
        return self._request("GET", "/auth/llm-keys")

    def request_password_reset(self, email: str) -> Dict[str, Any]:
        """Request a password reset email."""
        return self._request("POST", "/auth/password-reset/request", json_body={"email": email})

    def confirm_password_reset(self, token: str, new_password: str) -> Dict[str, Any]:
        """Reset password using a valid reset token."""
        body = {"token": token, "new_password": new_password}
        return self._request("POST", "/auth/password-reset/confirm", json_body=body)

    # ============================================================================
    # Evolve
    # ============================================================================

    def trigger_evolution(self) -> Dict[str, Any]:
        """Manually trigger memory evolution processes."""
        return self._request("POST", "/evolution/trigger")

    def run_dream_phase(self) -> Dict[str, Any]:
        """Run a 'dream' phase: promote working memory to episodic/procedural."""
        return self._request("POST", "/evolution/dream")

    def get_evolution_status(self) -> Dict[str, Any]:
        """Get status of memory evolution processes."""
        return self._request("GET", "/evolution/status")

    # ============================================================================
    # Governance
    # ============================================================================

    def run_governance_analysis(
        self,
        query: str = "*",
        top_k: int = 100,
        memory_items: Optional[List[Dict[str, Any]]] = None
    ) -> Dict[str, Any]:
        """Run governance analysis."""
        body = {
            "query": query,
            "top_k": top_k,
            "memory_items": memory_items or []
        }
        return self._request("POST", "/governance/run_analysis", json_body=body)

    def list_violations(
        self,
        severity: Optional[str] = None,
        auto_fixable_only: bool = False
    ) -> Dict[str, Any]:
        """List violations available for review."""
        params = {"severity": severity, "auto_fixable_only": auto_fixable_only}
        return self._request("GET", "/governance/violations", params=params)

    def get_violation(self, violation_id: str) -> Dict[str, Any]:
        """Get a specific violation by ID."""
        return self._request("GET", f"/governance/violations/{violation_id}")

    def apply_governance_decision(
        self,
        violation_id: str,
        action: str = "approve",
        rationale: str = "",
        decided_by: str = "human"
    ) -> Dict[str, Any]:
        """Apply a governance decision for a violation."""
        body = {
            "violation_id": violation_id,
            "action": action,
            "rationale": rationale,
            "decided_by": decided_by
        }
        return self._request("POST", "/governance/apply_decision", json_body=body)

    def auto_fix_violations(self, confidence_threshold: float = 0.8) -> Dict[str, Any]:
        """Run auto-fix for high-confidence violations."""
        body = {"confidence_threshold": confidence_threshold}
        return self._request("POST", "/governance/auto_fix", json_body=body)

    def get_governance_summary(self) -> Dict[str, Any]:
        """Get a summary of governance state."""
        return self._request("GET", "/memory/governance/summary")

    # ============================================================================
    # Ontology
    # ============================================================================

    def run_inference(
        self,
        raw_chunks: List[Dict[str, str]],
        registry_id: str = "default",
        params: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """Run ontology inference over provided raw text chunks."""
        body = {
            "registry_id": registry_id,
            "raw_chunks": raw_chunks,
            "params": params or {}
        }
        return self._request("POST", "/memory/ontology/inference/run", json_body=body)

    def list_registries(self) -> Dict[str, Any]:
        """List all ontology registries."""
        return self._request("GET", "/memory/ontology/registries")

    def create_registry(
        self,
        name: str,
        description: str = "",
        domain: str = "general"
    ) -> Dict[str, Any]:
        """Create a new ontology registry."""
        body = {
            "name": name,
            "description": description,
            "domain": domain
        }
        return self._request("POST", "/memory/ontology/registries", json_body=body)

    def get_registry_snapshot(
        self,
        registry_id: str,
        version: Optional[str] = None
    ) -> Dict[str, Any]:
        """Get a snapshot of a registry (current or specific version)."""
        params = {"version": version} if version else None
        return self._request("GET", f"/memory/ontology/registry/{registry_id}/snapshot", params=params)

    def apply_changeset(
        self,
        registry_id: str,
        changeset: Dict[str, Any],
        base_version: str = "",
        message: str = ""
    ) -> Dict[str, Any]:
        """Apply a changeset to create a new version of the registry."""
        body = {
            "base_version": base_version,
            "changeset": changeset,
            "message": message
        }
        return self._request("POST", f"/memory/ontology/registry/{registry_id}/apply", json_body=body)

    def list_registry_snapshots(
        self,
        registry_id: str,
        limit: int = 50
    ) -> Dict[str, Any]:
        """List snapshots for a registry."""
        return self._request("GET", f"/memory/ontology/registry/{registry_id}/snapshots", params={"limit": limit})

    def get_registry_changelog(
        self,
        registry_id: str,
        limit: int = 50
    ) -> Dict[str, Any]:
        """Get change history for a registry."""
        return self._request("GET", f"/memory/ontology/registry/{registry_id}/changelog", params={"limit": limit})

    def rollback_registry(
        self,
        registry_id: str,
        target_version: str = "",
        message: str = ""
    ) -> Dict[str, Any]:
        """Rollback registry to a previous version."""
        body = {
            "target_version": target_version,
            "message": message
        }
        return self._request("POST", f"/memory/ontology/registry/{registry_id}/rollback", json_body=body)

    def export_registry(
        self,
        registry_id: str,
        version: Optional[str] = None,
        user_id: Optional[str] = None
    ) -> Dict[str, Any]:
        """Export a registry snapshot."""
        params = {}
        if version:
            params["version"] = version
        if user_id:
            params["user_id"] = user_id
        return self._request("GET", f"/memory/ontology/registry/{registry_id}/export", params=params)

    def import_registry(
        self,
        registry_id: str,
        data: Dict[str, Any],
        message: str = ""
    ) -> Dict[str, Any]:
        """Import data into a registry."""
        body = {
            "data": data,
            "message": message
        }
        return self._request("POST", f"/memory/ontology/registry/{registry_id}/import", json_body=body)

    def list_enrichment_providers(self) -> Dict[str, Any]:
        """List available enrichment providers."""
        return self._request("GET", "/memory/ontology/enrichment/providers")

    def run_enrichment(
        self,
        entities: List[str],
        provider: str = "wikipedia",
        user_id: Optional[str] = None
    ) -> Dict[str, Any]:
        """Run enrichment operation using specified provider."""
        body = {
            "provider": provider,
            "entities": entities,
            "user_id": user_id
        }
        return self._request("POST", "/memory/ontology/enrichment/run", json_body=body)

    def run_grounding_ontology(
        self,
        item_id: str,
        candidates: List[str],
        grounder: str = "wikipedia",
        user_id: Optional[str] = None
    ) -> Dict[str, Any]:
        """Run grounding operation using specified grounder."""
        body = {
            "grounder": grounder,
            "item_id": item_id,
            "candidates": candidates,
            "user_id": user_id
        }
        return self._request("POST", "/memory/ontology/grounding/run", json_body=body)

    # ============================================================================
    # Pipeline
    # ============================================================================

    def run_extraction_stage(
        self,
        content: str,
        extractor_name: str = "llm"
    ) -> Dict[str, Any]:
        """Run extraction pipeline stage."""
        body = {
            "content": content,
            "extractor_name": extractor_name
        }
        return self._request("POST", "/memory/pipeline/extraction", json_body=body)

    def run_storage_stage(
        self,
        extracted_data: Dict[str, Any],
        storage_strategy: str = "standard"
    ) -> Dict[str, Any]:
        """Run storage pipeline stage."""
        body = {
            "extracted_data": extracted_data,
            "storage_strategy": storage_strategy
        }
        return self._request("POST", "/memory/pipeline/storage", json_body=body)

    def run_linking_stage(
        self,
        stored_entities: List[Dict[str, Any]],
        linking_algorithm: str = "exact"
    ) -> Dict[str, Any]:
        """Run linking pipeline stage."""
        body = {
            "stored_entities": stored_entities,
            "linking_algorithm": linking_algorithm
        }
        return self._request("POST", "/memory/pipeline/linking", json_body=body)

    def run_enrichment_stage(
        self,
        linked_entities: List[Dict[str, Any]],
        enrichment_types: Optional[List[str]] = None
    ) -> Dict[str, Any]:
        """Run enrichment pipeline stage."""
        body = {
            "linked_entities": linked_entities,
            "enrichment_types": enrichment_types or ["sentiment", "topics"]
        }
        return self._request("POST", "/memory/pipeline/enrichment", json_body=body)

    def run_grounding_stage(
        self,
        enriched_entities: List[Dict[str, Any]],
        grounding_sources: Optional[List[str]] = None
    ) -> Dict[str, Any]:
        """Run grounding pipeline stage."""
        body = {
            "enriched_entities": enriched_entities,
            "grounding_sources": grounding_sources or ["wikipedia"]
        }
        return self._request("POST", "/memory/pipeline/grounding", json_body=body)

    def get_pipeline_state(
        self,
        pipeline_id: str,
        run_id: Optional[str] = None
    ) -> Dict[str, Any]:
        """Get pipeline state for a specific pipeline and run."""
        params = {"run_id": run_id} if run_id else None
        return self._request("GET", f"/memory/pipeline/{pipeline_id}/state", params=params)

    def reset_pipeline(self, pipeline_id: str) -> Dict[str, Any]:
        """Reset a pipeline, clearing its state."""
        return self._request("DELETE", f"/memory/pipeline/{pipeline_id}")

    def clear_run_state(self, pipeline_id: str, run_id: str) -> Dict[str, Any]:
        """Clear all stage states for a specific pipeline run."""
        return self._request("DELETE", f"/memory/pipeline/{pipeline_id}/run/{run_id}")

    # ============================================================================
    # Subscription
    # ============================================================================

    def create_checkout_session(
        self,
        tier: str,
        billing_period: str = "monthly",
        trial_days: Optional[int] = None
    ) -> Dict[str, Any]:
        """Create a Stripe Checkout session for subscription upgrade."""
        body = {
            "tier": tier,
            "billing_period": billing_period,
            "trial_days": trial_days
        }
        return self._request("POST", "/subscription/checkout", json_body=body)

    def upgrade_subscription(
        self,
        tier: str,
        billing_period: str = "monthly",
        payment_method_id: Optional[str] = None,
        use_checkout: bool = False
    ) -> Dict[str, Any]:
        """Upgrade subscription tier."""
        body = {
            "tier": tier,
            "billing_period": billing_period,
            "payment_method_id": payment_method_id,
            "use_checkout": use_checkout
        }
        return self._request("POST", "/subscription/upgrade", json_body=body)

    def get_subscription(self) -> Dict[str, Any]:
        """Get current subscription details."""
        return self._request("GET", "/subscription/current")

    def cancel_subscription(self, immediately: bool = False) -> Dict[str, Any]:
        """Cancel subscription."""
        return self._request("POST", "/subscription/cancel", params={"immediately": immediately})

    # ============================================================================
    # Teams
    # ============================================================================

    def create_team(
        self,
        name: str,
        description: Optional[str] = None,
        data_classification: str = "internal",
        cost_center: Optional[str] = None
    ) -> Dict[str, Any]:
        """Create a new team."""
        body = {
            "name": name,
            "description": description,
            "data_classification": data_classification,
            "cost_center": cost_center
        }
        return self._request("POST", "/memory/teams", json_body=body)

    def list_teams(self) -> List[Dict[str, Any]]:
        """List all teams the user has access to."""
        return self._request("GET", "/memory/teams")

    def get_team(self, team_id: str) -> Dict[str, Any]:
        """Get details of a specific team."""
        return self._request("GET", f"/memory/teams/{team_id}")

    def update_team(
        self,
        team_id: str,
        name: Optional[str] = None,
        description: Optional[str] = None,
        data_classification: Optional[str] = None,
        cost_center: Optional[str] = None
    ) -> Dict[str, Any]:
        """Update team details."""
        body = {}
        if name: body["name"] = name
        if description: body["description"] = description
        if data_classification: body["data_classification"] = data_classification
        if cost_center: body["cost_center"] = cost_center
        return self._request("PUT", f"/memory/teams/{team_id}", json_body=body)

    def delete_team(self, team_id: str) -> Dict[str, Any]:
        """Delete a team."""
        return self._request("DELETE", f"/memory/teams/{team_id}")

    def list_team_members(self, team_id: str) -> Dict[str, Any]:
        """List all members of a team."""
        return self._request("GET", f"/memory/teams/{team_id}/members")

    def add_team_member(
        self,
        team_id: str,
        user_id: str,
        role: str = "member"
    ) -> Dict[str, Any]:
        """Add a user to a team."""
        body = {"user_id": user_id, "role": role}
        return self._request("POST", f"/memory/teams/{team_id}/members", json_body=body)

    def update_team_member(
        self,
        team_id: str,
        member_user_id: str,
        role: str
    ) -> Dict[str, Any]:
        """Update a team member's role."""
        body = {"role": role}
        return self._request("PUT", f"/memory/teams/{team_id}/members/{member_user_id}", json_body=body)

    def remove_team_member(self, team_id: str, member_user_id: str) -> Dict[str, Any]:
        """Remove a user from a team."""
        return self._request("DELETE", f"/memory/teams/{team_id}/members/{member_user_id}")

    def get_team_permissions(self, team_id: str) -> Dict[str, Any]:
        """Get available permissions for a team."""
        return self._request("GET", f"/memory/teams/{team_id}/permissions")

    # ============================================================================
    # Temporal
    # ============================================================================

    def get_history(
        self,
        item_id: str,
        start_time: Optional[str] = None,
        end_time: Optional[str] = None,
        limit: int = 100
    ) -> Dict[str, Any]:
        """Get complete version history of a memory item."""
        params = {"limit": limit}
        if start_time: params["start_time"] = start_time
        if end_time: params["end_time"] = end_time
        return self._request("GET", f"/memory/temporal/{item_id}/history", params=params)

    def time_travel(
        self,
        timestamp: str,
        query: Optional[str] = None,
        limit: int = 100
    ) -> Dict[str, Any]:
        """Time-travel query - get state at specific time."""
        params = {"limit": limit}
        if query: params["query"] = query
        return self._request("GET", f"/memory/temporal/at/{timestamp}", params=params)

    def get_item_at_time(self, item_id: str, timestamp: str) -> Dict[str, Any]:
        """Get specific item as it existed at timestamp."""
        return self._request("GET", f"/memory/temporal/{item_id}/at/{timestamp}")

    def get_changes(
        self,
        item_id: str,
        since: Optional[str] = None,
        until: Optional[str] = None,
        change_type: Optional[str] = None
    ) -> Dict[str, Any]:
        """Get all changes to an item in time range."""
        params = {}
        if since: params["since"] = since
        if until: params["until"] = until
        if change_type: params["change_type"] = change_type
        return self._request("GET", f"/memory/temporal/{item_id}/changes", params=params)

    def compare_versions(
        self,
        item_id: str,
        v1: int,
        v2: int
    ) -> Dict[str, Any]:
        """Compare two versions of an item."""
        params = {"v1": v1, "v2": v2}
        return self._request("POST", f"/memory/temporal/{item_id}/compare", params=params)

    def rollback(
        self,
        item_id: str,
        to_version: Optional[int] = None,
        to_time: Optional[str] = None
    ) -> Dict[str, Any]:
        """Rollback item to previous version."""
        params = {}
        if to_version: params["to_version"] = to_version
        if to_time: params["to_time"] = to_time
        return self._request("POST", f"/memory/temporal/{item_id}/rollback", params=params)

    def get_audit_trail(
        self,
        item_id: str,
        change_type: Optional[str] = None,
        user_id: Optional[str] = None,
        start_time: Optional[str] = None,
        end_time: Optional[str] = None
    ) -> Dict[str, Any]:
        """Get complete audit trail for an item."""
        params = {}
        if change_type: params["change_type"] = change_type
        if user_id: params["user_id"] = user_id
        if start_time: params["start_time"] = start_time
        if end_time: params["end_time"] = end_time
        return self._request("GET", f"/memory/temporal/{item_id}/audit", params=params)

    def search_during_range(
        self,
        query: str,
        start_time: str,
        end_time: str,
        limit: int = 100
    ) -> Dict[str, Any]:
        """Search memories that existed during time range."""
        params = {
            "query": query,
            "start_time": start_time,
            "end_time": end_time,
            "limit": limit
        }
        return self._request("GET", "/memory/temporal/search/during", params=params)

    def generate_compliance_report(
        self,
        start_date: str,
        end_date: str,
        report_type: str = "HIPAA",
        item_ids: Optional[List[str]] = None
    ) -> Dict[str, Any]:
        """Generate compliance report (HIPAA, GDPR, SOC2)."""
        params = {
            "start_date": start_date,
            "end_date": end_date,
            "report_type": report_type
        }
        if item_ids: params["item_ids"] = item_ids
        return self._request("GET", "/memory/temporal/compliance/report", params=params)

    def get_relationship_history(self, rel_id: str) -> Dict[str, Any]:
        """Get history of a relationship."""
        return self._request("GET", f"/memory/temporal/relationships/{rel_id}/history")

    def get_relationships_at_time(
        self,
        timestamp: str,
        limit: int = 100
    ) -> Dict[str, Any]:
        """Get all relationships that existed at specific time."""
        params = {"limit": limit}
        return self._request("GET", f"/memory/temporal/relationships/at/{timestamp}", params=params)

    def get_relationship_valid_periods(self, rel_id: str) -> Dict[str, Any]:
        """Get valid time periods for a relationship."""
        return self._request("GET", f"/memory/temporal/relationships/{rel_id}/valid-periods")

    # ============================================================================
    # Usage
    # ============================================================================

    def get_usage_dashboard(self) -> Dict[str, Any]:
        """Get usage dashboard with current quotas and limits."""
        return self._request("GET", "/usage/dashboard")

    def get_system_stats(self) -> Dict[str, Any]:
        """Get comprehensive system statistics."""
        return self._request("GET", "/memory/admin/stats")

    def get_analytics_status(self) -> Dict[str, Any]:
        """Return analytics feature status."""
        return self._request("GET", "/memory/analytics/status")

    def get_governance_summary(self) -> Dict[str, Any]:
        """Get a summary of governance state."""
        return self._request("GET", "/memory/governance/summary")

    # ============================================================================
    # Webhooks
    # ============================================================================

    def trigger_stripe_webhook(
        self,
        payload: Dict[str, Any],
        signature: str
    ) -> Dict[str, Any]:
        """Trigger a Stripe webhook event (mostly for testing)."""
        # Note: This sends raw body, but our _request helper assumes JSON or params.
        # For webhooks, we might need to send raw bytes if we were simulating real Stripe calls.
        # However, the client is typically used to INTERACT with the API, not send webhooks TO it.
        # But if we need to simulate it:
        headers = {"stripe-signature": signature}
        # We'll use json_body for convenience, but real Stripe sends raw bytes.
        # This method might be limited by _request implementation if strict raw body is needed.
        return self._request("POST", "/webhooks/stripe", json_body=payload, headers=headers)

    # ============================================================================
    # Zettelkasten
    # ============================================================================

    def get_backlinks(self, note_id: str) -> Dict[str, Any]:
        """Get notes that link TO this note (backlinks)."""
        return self._request("GET", f"/memory/zettel/{note_id}/backlinks")

    def get_forward_links(self, note_id: str) -> Dict[str, Any]:
        """Get notes this note links TO (forward links)."""
        return self._request("GET", f"/memory/zettel/{note_id}/forward-links")

    def get_connections(self, note_id: str) -> Dict[str, Any]:
        """Get all connections (backlinks + forward links)."""
        return self._request("GET", f"/memory/zettel/{note_id}/connections")

    def get_clusters(
        self,
        min_size: int = 3,
        algorithm: str = "louvain"
    ) -> Dict[str, Any]:
        """Detect knowledge clusters in your Zettelkasten."""
        params = {"min_size": min_size, "algorithm": algorithm}
        return self._request("GET", "/memory/zettel/clusters", params=params)

    def get_hubs(
        self,
        min_connections: int = 5,
        limit: int = 20
    ) -> Dict[str, Any]:
        """Find hub notes (highly connected notes)."""
        params = {"min_connections": min_connections, "limit": limit}
        return self._request("GET", "/memory/zettel/hubs", params=params)

    def get_bridges(self, limit: int = 20) -> Dict[str, Any]:
        """Find bridge notes (notes connecting different clusters)."""
        params = {"limit": limit}
        return self._request("GET", "/memory/zettel/bridges", params=params)

    def get_discoveries(
        self,
        note_id: str,
        max_distance: int = 3,
        min_surprise: float = 0.5
    ) -> Dict[str, Any]:
        """Find unexpected connections (serendipitous discovery)."""
        params = {"max_distance": max_distance, "min_surprise": min_surprise}
        return self._request("GET", f"/memory/zettel/{note_id}/discoveries", params=params)

    def get_path(
        self,
        note_id: str,
        target_id: str,
        max_paths: int = 5
    ) -> Dict[str, Any]:
        """Find paths between two notes."""
        params = {"max_paths": max_paths}
        return self._request("GET", f"/memory/zettel/{note_id}/path/{target_id}", params=params)

    def parse_wikilinks(
        self,
        content: str,
        auto_create: bool = True
    ) -> Dict[str, Any]:
        """Parse [[wikilinks]] in content."""
        params = {"content": content, "auto_create": auto_create}
        return self._request("POST", "/memory/zettel/wikilink/parse", params=params)

    def resolve_wikilink(self, link: str) -> Dict[str, Any]:
        """Resolve a wikilink to a note."""
        params = {"link": link}
        return self._request("GET", "/memory/zettel/wikilink/resolve", params=params)

    def get_subgraph(
        self,
        note_id: str,
        depth: int = 2,
        include_metadata: bool = True
    ) -> Dict[str, Any]:
        """Get subgraph around a note (for visualization)."""
        params = {"depth": depth, "include_metadata": include_metadata}
        return self._request("GET", f"/memory/zettel/{note_id}/graph", params=params)

    def detect_concept_emergence(self, limit: int = 20) -> Dict[str, Any]:
        """Detect emerging concepts from connection patterns."""
        params = {"limit": limit}
        return self._request("GET", "/memory/zettel/concept-emergence", params=params)

    def suggest_related_notes(
        self,
        note_id: str,
        count: int = 5
    ) -> Dict[str, Any]:
        """Suggest related notes for serendipitous discovery."""
        params = {"count": count}
        return self._request("GET", f"/memory/zettel/{note_id}/suggestions", params=params)

    def random_walk_discovery(
        self,
        note_id: str,
        length: int = 5
    ) -> Dict[str, Any]:
        """Perform random walk for serendipitous discovery."""
        params = {"length": length}
        return self._request("GET", f"/memory/zettel/{note_id}/random-walk", params=params)

    def find_notes_by_tag(
        self,
        tag: str,
        limit: int = 100
    ) -> Dict[str, Any]:
        """Find notes by tag."""
        params = {"limit": limit}
        return self._request("GET", f"/memory/zettel/by-tag/{tag}", params=params)

    def find_notes_by_property(
        self,
        key: str,
        value: str,
        limit: int = 100
    ) -> Dict[str, Any]:
        """Find notes by property."""
        params = {"key": key, "value": value, "limit": limit}
        return self._request("GET", "/memory/zettel/by-property", params=params)

    def find_notes_mentioning(
        self,
        entity_id: str,
        limit: int = 100
    ) -> Dict[str, Any]:
        """Find notes mentioning an entity."""
        params = {"limit": limit}
        return self._request("GET", f"/memory/zettel/mentioning/{entity_id}", params=params)

    def query_by_dynamic_relation(
        self,
        source_id: str,
        relation_type: str,
        limit: int = 100
    ) -> Dict[str, Any]:
        """Query notes by dynamic relation type."""
        params = {"limit": limit}
        return self._request("GET", f"/memory/zettel/by-relation/{source_id}/{relation_type}", params=params)

    def _request(
        self,
        method: str,
        endpoint: str,
        params: Optional[Dict[str, Any]] = None,
        json_body: Optional[Dict[str, Any]] = None,
        data: Optional[Dict[str, Any]] = None,
        headers: Optional[Dict[str, str]] = None
    ) -> Any:
        """Internal helper for making HTTP requests."""
        import httpx
        url = f"{self.base_url}{endpoint}"
        req_headers = {"X-Team-Id": self.team_id}
        if headers:
            req_headers.update(headers)
        
        if self.api_key:
            req_headers["Authorization"] = f"Bearer {self.api_key}"
            
        try:
            response = httpx.request(
                method,
                url,
                params=params,
                json=json_body,
                data=data,
                headers=req_headers,
                timeout=self.timeout
            )
            response.raise_for_status()
            if response.status_code == 204:
                return None
            return response.json()
        except httpx.HTTPStatusError as e:
            error_detail = e.response.text if hasattr(e, 'response') else str(e)
            raise SmartMemoryClientError(f"Request failed: {e} - Detail: {error_detail}")
        except Exception as e:
            raise SmartMemoryClientError(f"Request failed: {str(e)}")

    def __repr__(self) -> str:
        auth_status = "authenticated" if self.api_key else "unauthenticated"
        return f"SmartMemoryClient(base_url='{self.base_url}', {auth_status})"

    def __enter__(self):
        """Context manager entry"""
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        """Context manager exit"""
        # Clean up underlying client if needed
        pass
