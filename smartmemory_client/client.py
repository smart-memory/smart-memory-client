"""
SmartMemory HTTP Client Wrapper

A wrapper around the auto-generated SmartMemory client that provides:
- Simplified authentication (JWT token handling)
- Backward compatibility with existing code
- Convenient helper methods
- Better error handling

This wrapper uses the auto-generated client from smartmemory_client.generated
which is generated from the OpenAPI schema.

For more information, see: https://github.com/smartmemory/smart-memory-client
"""

import logging
import os
from typing import Any, Dict, List, Optional, Union

from smartmemory.models.memory_item import MemoryItem

# Import generated client
from smartmemory_client.generated.client import (
    AuthenticatedClient,
    Client,
)
from smartmemory_client.generated.api.memory_crud import (
    add_memory_memory_add_post,
    delete_memory_memory_item_id_delete,
    get_memory_memory_item_id_get,
    get_memory_summary_memory_summary_get,
    list_memories_memory_list_get,
    search_memory_memory_search_post,
    update_memory_memory_item_id_put,
)
from smartmemory_client.generated.api.ingestion import (
    enrich_memory_memory_item_id_enrich_post,
    ingest_content_memory_ingest_post,
    personalize_memory_memory_personalize_post,
    update_from_feedback_memory_feedback_post,
)
from smartmemory_client.generated.api.links import (
    link_memories_memory_link_post,
    get_memory_neighbors_memory_item_id_neighbors_get,
)
from smartmemory_client.generated.api.health import (
    health_check_health_get,
)

logger = logging.getLogger(__name__)


class SmartMemoryClientError(Exception):
    """Base exception for SmartMemory client errors"""

    pass


class SmartMemoryClient:
    """
    SmartMemory HTTP Client Wrapper

    A simplified wrapper around the auto-generated client that provides:
    - Easy authentication with JWT tokens
    - Backward-compatible API
    - Type-safe operations using generated models
    - Better error handling

    Usage:
        ```python
        from service_common.clients import SmartMemoryClient

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

    Note:
        This wrapper uses the auto-generated client. To regenerate after API changes:
        ```bash
        ./scripts/generate_client.sh
        ```
    """

    def __init__(
        self,
        base_url: str = "http://localhost:9001",
        api_key: Optional[str] = None,
        timeout: float = 30.0,
        verify_ssl: bool = True,
    ):
        """
        Initialize SmartMemory client wrapper.

        Args:
            base_url: Base URL of the SmartMemory service
            api_key: JWT token for authentication (or set SMARTMEMORY_API_KEY env var)
            timeout: Request timeout in seconds
            verify_ssl: Whether to verify SSL certificates
        """
        # Get API key from parameter or environment
        self.api_key = api_key or os.getenv("SMARTMEMORY_API_KEY")

        # Create underlying client
        if self.api_key:
            # Use authenticated client for endpoints requiring auth
            self._client = AuthenticatedClient(
                base_url=base_url,
                token=self.api_key,
                timeout=timeout,
                verify_ssl=verify_ssl,
            )
            logger.info("SmartMemoryClient initialized with authentication")
        else:
            # Use unauthenticated client (limited functionality)
            self._client = Client(
                base_url=base_url, timeout=timeout, verify_ssl=verify_ssl
            )
            logger.warning(
                "SmartMemoryClient initialized WITHOUT authentication - "
                "most endpoints will fail. Set SMARTMEMORY_API_KEY environment variable."
            )

        self.base_url = base_url

    def _handle_response(self, response, error_msg="Request failed"):
        """Helper to handle generated client responses"""
        if response is None:
            raise SmartMemoryClientError(error_msg)
        
        # Generated client returns Response object with .parsed attribute
        if hasattr(response, "parsed"):
            result = response.parsed
        else:
            result = response
        
        # Convert to dict if possible
        if result is None:
            return {}
        elif hasattr(result, "to_dict"):
            return result.to_dict()
        elif isinstance(result, dict):
            return result
        else:
            return result

    def health_check(self) -> Dict[str, Any]:
        """
        Check the health status of the SmartMemory service.

        Returns:
            Health status information

        Example:
            ```python
            status = client.health_check()
            print(status)  # {'status': 'healthy', 'timestamp': '...'}
            ```
        """
        response = health_check_health_get.sync_detailed(client=self._client)
        # Health endpoint returns 200 with empty body, so we return success status
        if response.status_code == 200:
            return {"status": "healthy"}
        else:
            raise SmartMemoryClientError(f"Health check failed with status {response.status_code}")

    def add(
        self,
        item: Union[str, MemoryItem, Dict[str, Any]],
        memory_type: str = "semantic",
        metadata: Optional[Dict[str, Any]] = None,
        use_pipeline: bool = True,
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

        # Call generated API
        response = add_memory_memory_add_post.sync_detailed(
            client=self._client,
            body={
                "content": content,
                "memory_type": memory_type,
                "metadata": metadata or {},
                "use_pipeline": use_pipeline,
            },
        )

        if response.parsed is None:
            raise SmartMemoryClientError("Failed to add memory")

        # Extract ID from response
        result = response.parsed
        if hasattr(result, "id"):
            return result.id
        elif isinstance(result, dict):
            return result.get("id")
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
            response = get_memory_memory_item_id_get.sync_detailed(
                item_id=item_id, client=self._client
            )

            if response is None:
                return None

            # Convert response to MemoryItem
            return MemoryItem(
                item_id=response.item_id if hasattr(response, "item_id") else item_id,
                content=response.content if hasattr(response, "content") else "",
                memory_type=(
                    response.memory_type
                    if hasattr(response, "memory_type")
                    else "semantic"
                ),
                metadata=response.metadata if hasattr(response, "metadata") else {},
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
        body = {"query": query, "top_k": top_k, "memory_type": memory_type}
        if use_ssg is not None:
            body["use_ssg"] = use_ssg
            
        response = search_memory_memory_search_post.sync_detailed(
            client=self._client,
            body=body,
        )

        if response is None:
            return []

        # Convert response to MemoryItem objects
        results = []
        response_list = response if isinstance(response, list) else [response]

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
        # Use httpx directly for the new endpoint
        import httpx
        
        url = f"{self.base_url}/memory/search/advanced"
        headers = {}
        if self.api_key:
            headers["Authorization"] = f"Bearer {self.api_key}"
        
        payload = {
            "query": query,
            "algorithm": algorithm,
            "max_results": max_results,
            "use_ssg": use_ssg
        }
        
        try:
            with httpx.Client(timeout=self._client.timeout) as http_client:
                response = http_client.post(url, json=payload, headers=headers)
                response.raise_for_status()
                data = response.json()
            
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
            
        except httpx.HTTPStatusError as e:
            raise SmartMemoryClientError(f"Advanced search failed: {e.response.text}")
        except Exception as e:
            raise SmartMemoryClientError(f"Advanced search failed: {str(e)}")

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

        response = update_memory_memory_item_id_put.sync_detailed(
            item_id=item_id, client=self._client, body=body
        )

        return response is not None

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
        response = delete_memory_memory_item_id_delete.sync_detailed(
            item_id=item_id, client=self._client
        )
        return response is not None

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
        response = ingest_content_memory_ingest_post.sync_detailed(
            client=self._client,
            body={
                "content": content,
                "extractor_name": extractor_name,
                "context": context or {},
            },
        )

        if response is None:
            raise SmartMemoryClientError("Failed to ingest content")

        # Convert response to dict
        if hasattr(response, "to_dict"):
            return response.to_dict()
        elif isinstance(response, dict):
            return response
        else:
            return {"status": "success"}

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
        response = link_memories_memory_link_post.sync_detailed(
            client=self._client,
            body={
                "source_id": source_id,
                "target_id": target_id,
                "link_type": link_type,
            },
        )
        return response is not None

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
        response = get_memory_neighbors_memory_item_id_neighbors_get.sync_detailed(
            item_id=item_id, client=self._client
        )

        if response is None:
            return []

        if hasattr(response, "to_dict"):
            result = response.to_dict()
        elif isinstance(response, dict):
            result = response
        else:
            return []

        return result.get("neighbors", [])

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
        response = get_memory_summary_memory_summary_get.sync_detailed(client=self._client)

        if response is None:
            return {}

        if hasattr(response, "to_dict"):
            return response.to_dict()
        elif isinstance(response, dict):
            return response
        else:
            return {}

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
        response = enrich_memory_memory_item_id_enrich_post.sync_detailed(
            item_id=item_id,
            client=self._client,
            body={"item_id": item_id, "routines": routines or []},
        )

        if response is None:
            return {}

        if hasattr(response, "to_dict"):
            return response.to_dict()
        elif isinstance(response, dict):
            return response
        else:
            return {}

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
        response = personalize_memory_memory_personalize_post.sync_detailed(
            client=self._client,
            body={"traits": traits or {}, "preferences": preferences or {}},
        )

        if response is None:
            return {}

        if hasattr(response, "to_dict"):
            return response.to_dict()
        elif isinstance(response, dict):
            return response
        else:
            return {}

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
            result = client.provide_feedback(
                feedback={"item_id": "123", "rating": 5, "comment": "Very helpful"},
                memory_type="semantic"
            )
            ```
        """
        response = update_from_feedback_memory_feedback_post.sync_detailed(
            client=self._client,
            body={"feedback": feedback, "memory_type": memory_type},
        )

        if response is None:
            return {}

        if hasattr(response, "to_dict"):
            return response.to_dict()
        elif isinstance(response, dict):
            return response
        else:
            return {}

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
