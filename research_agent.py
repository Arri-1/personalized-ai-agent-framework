import time
from typing import Optional, Dict, Any
from dotenv import load_dotenv
load_dotenv()
try:
    from tavily import TavilyClient
    HAS_TAVILY = True
except ImportError:
    HAS_TAVILY = False
from agent import BaseAgent
from utils import get_logger

logger = get_logger("research_agent")

class ResearchAgent(BaseAgent):
    def __init__(self, agent_id: Optional[str] = None, message_bus = None):
        super().__init__(agent_id or f"research_{int(time.time())}", message_bus)
        self.capabilities = ["web_search", "summarization"]

    def initialize(self):
        super().initialize()
        self.logger.info("Research agent initialized")
        # Advertise capabilities
        self.publish_state("agent_capabilities", {
            "agent_id": self.agent_id,
            "capabilities": self.capabilities,
            "timestamp": time.time()
        })

    def execute_task(self, payload: Dict[str, Any]):
        """Execute a research task"""
        task_id = payload.get("task_id", "unknown")
        query = payload.get("query", "")
        max_results = payload.get("max_results", 5)
        try:
            self.logger.info(f"Executing research task {task_id}: {query}")

            if not HAS_TAVILY:
                self.logger.warning("tavily-python not available, falling back to simulated results")
                # Simulated fallback
                time.sleep(2)  # Simulate work
                result = {
                    "query": query,
                    "results": [
                        {"title": f"Result {i} for {query}", "url": f"https://example.com/{i}", "snippet": f"This is a simulated result {i} for {query}."}
                        for i in range(1, max_results + 1)
                    ],
                    "summary": f"Found {max_results} results for query '{query}'. This is a simulated summary (fallback due to missing dependencies)."
                }
            else:
                try:
                    tavily_api_key = os.getenv("TAVILY_API_KEY")
                    if not tavily_api_key:
                        raise ValueError("TAVILY_API_KEY environment variable is not set")
                    client = TavilyClient(api_key=tavily_api_key)
                    response = client.search(query=query, search_depth="advanced", max_results=max_results)
                    # Format results to match the expected structure
                    formatted_results = []
                    for r in response.get('results', []):
                        title = r.get('title', 'No title')
                        url = r.get('url', '#')
                        snippet = r.get('content', 'No snippet available')
                        formatted_results.append({
                            "title": title,
                            "url": url,
                            "snippet": snippet
                        })
                    # Prepare summary
                    if formatted_results:
                        summary_lines = [f"Found {len(formatted_results)} results for query '{query}':"]
                        for i, r in enumerate(formatted_results, 1):
                            summary_lines.append(f"{i}. {r['title']} - {r['snippet']}")
                        summary = "\n".join(summary_lines)
                    else:
                        summary = f"No results found for query '{query}'."

                    result = {
                        "query": query,
                        "results": formatted_results,
                        "summary": summary
                    }

                except Exception as e:
                    self.logger.error(f"Error during Tavily search for query '{query}': {e}")
                    # Fallback to simulated results on error
                    time.sleep(1)
                    result = {
                        "query": query,
                        "results": [
                            {"title": f"Error result {i} for {query}", "url": f"https://example.com/error/{i}", "snippet": f"Search failed: {str(e)}. This is a placeholder."}
                            for i in range(1, min(3, max_results) + 1)
                        ],
                        "summary": f"Search for '{query}' failed due to: {str(e)}. Returning placeholder results."
                    }

            # Add timestamp to result
            result["_timestamp"] = time.time()

            # Publish result
            self.publish_state(f"research_result_{task_id}", result)

            # Notify supervisor of completion
            completion_message = {
                "task_id": task_id,
                "agent_id": self.agent_id,
                "result": result,
                "timestamp": time.time()
            }
            self.message_bus.publish("task_completed", completion_message)

            self.logger.info(f"Research task {task_id} completed")
        except Exception as e:
            self.logger.error(f"Unexpected error in research task {task_id}: {e}", exc_info=True)
            result = {
                "task_id": task_id,
                "query": query,
                "max_results": max_results,
                "status": "failed",
                "error": str(e),
                "_timestamp": time.time()
            }
            self.publish_state(f"research_result_{task_id}", result)
            completion_message = {
                "task_id": task_id,
                "agent_id": self.agent_id,
                "result": result,
                "timestamp": time.time()
            }
            self.message_bus.publish("task_completed", completion_message)

    def handle_query(self, payload: Dict[str, Any]):
        """Handle direct queries"""
        query = payload.get("query")
        if query:
            # Perform quick search and return result
            self.logger.info(f"Handling direct query: {query}")
            if not HAS_TAVILY:
                # Simulated quick search
                result = {"query": query, "answer": f"This is a simulated answer for {query}."}
            else:
                try:
                    tavily_api_key = os.getenv("TAVILY_API_KEY")
                    if not tavily_api_key:
                        raise ValueError("TAVILY_API_KEY environment variable is not set")
                    client = TavilyClient(api_key=tavily_api_key)
                    response = client.search(query=query, search_depth="advanced", max_results=1)
                    if response.get('results'):
                        # Extract the snippet from the first result
                        snippet = response['results'][0].get('content', 'No snippet available')
                        answer = snippet
                    else:
                        answer = "No answer found"
                    result = {"query": query, "answer": answer}
                except Exception as e:
                    self.logger.error(f"Error in direct query: {e}")
                    result = {"query": query, "answer": f"Error: {str(e)}"}
            # Send back to requester
            requester = payload.get("from")
            if requester:
                self.send_message(requester, "query_response", {"query": query, "result": result})