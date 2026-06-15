import time
import json
import os
from typing import Optional, Dict, Any
from dotenv import load_dotenv
load_dotenv()
from agent import BaseAgent
from utils import get_logger

logger = get_logger("summary_agent")

class SummaryAgent(BaseAgent):
    def __init__(self, agent_id: Optional[str] = None, message_bus = None):
        super().__init__(agent_id or f"summary_{int(time.time())}", message_bus)
        self.capabilities = ["summarization"]

    def initialize(self):
        super().initialize()
        self.logger.info("Summary agent initialized")
        # Advertise capabilities
        self.publish_state("agent_capabilities", {
            "agent_id": self.agent_id,
            "capabilities": self.capabilities,
            "timestamp": time.time()
        })

    def execute_task(self, payload: Dict[str, Any]):
        """Execute a summary task"""
        task_id = payload.get("task_id", "unknown")
        self.logger.info(f"Executing summary task {task_id}")

        # Read the blackboard to get research results
        blackboard_path = os.path.join(os.path.dirname(__file__), "blackboard.json")
        try:
            with open(blackboard_path, 'r', encoding='utf-8') as f:
                blackboard_data = json.load(f)
        except Exception as e:
            self.logger.error(f"Failed to read blackboard: {e}")
            blackboard_data = {"blackboard": {}, "logs": []}

        blackboard = blackboard_data.get("blackboard", {})

        # Collect all research results
        research_results = []
        for key, value in blackboard.items():
            if key.startswith("research_result_") and isinstance(value, dict):
                research_results.append(value)

        if not research_results:
            self.logger.error("No research data found on blackboard for summarization")
            result = {
                "task_id": task_id,
                "task_type": "summary",
                "description": payload.get("description", "Summarize research data"),
                "status": "failed",
                "error": "No research data found on blackboard",
                "_timestamp": time.time()
            }
        else:
            try:
                # Combine all research results into a single text for summarization
                combined_text = ""
                for i, res in enumerate(research_results, 1):
                    query = res.get("query", "Unknown query")
                    summary = res.get("summary", "No summary available")
                    results = res.get("results", [])
                    combined_text += f"Research #{i} - Query: {query}\n"
                    combined_text += f"Summary: {summary}\n"
                    if results:
                        combined_text += "Details:\n"
                        for j, r in enumerate(results[:5], 1):  # Top 5 results
                            title = r.get("title", "No title")
                            url = r.get("url", "#")
                            snippet = r.get("snippet", "No snippet available")
                            combined_text += f"  {j}. Title: {title}\n"
                            combined_text += f"     URL: {url}\n"
                            combined_text += f"     Snippet: {snippet}\n"
                    combined_text += "\n"

                # Use LLM for summarization
                summary_text = self._generate_summary_with_llm(combined_text)

                result = {
                    "task_id": task_id,
                    "task_type": "summary",
                    "description": payload.get("description", "Summarize research data"),
                    "status": "completed",
                    "summary": summary_text,
                    "_timestamp": time.time()
                }

                # Save the summary to blackboard
                self.publish_state("summary_results", {
                    "summary": summary_text,
                    "generated_at": time.time(),
                    "source_task_ids": [r.get("_timestamp") for r in research_results if "_timestamp" in r]
                })
            except Exception as e:
                self.logger.error(f"Error in summary task {task_id}: {e}", exc_info=True)
                result = {
                    "task_id": task_id,
                    "task_type": "summary",
                    "description": payload.get("description", "Summarize research data"),
                    "status": "failed",
                    "error": str(e),
                    "_timestamp": time.time()
                }

        # Publish result
        self.publish_state(f"summary_result_{task_id}", result)

        # Notify supervisor of completion
        completion_message = {
            "task_id": task_id,
            "agent_id": self.agent_id,
            "result": result,
            "timestamp": time.time()
        }
        self.message_bus.publish("task_completed", completion_message)

        self.logger.info(f"Summary task {task_id} completed with status: {result.get('status')}")

    def _generate_summary_with_llm(self, text: str) -> str:
        """Generate summary using Google GenAI with API key from environment"""
        self.logger.info("Attempting to call Google GenAI with API key from environment...")
        # Import the official Google GenAI SDK
        from google import genai
        api_key = os.getenv("GEMINI_API_KEY")
        if not api_key:
            raise ValueError("GEMINI_API_KEY environment variable is not set")
        client = genai.Client(api_key=api_key)
        prompt = f"Analyze these raw web search results: {text}. Extract and synthesize exactly 15 distinct, concrete breakthroughs, providing technical details for each in a bulleted list."
        response = client.models.generate_content(
            model='gemini-2.5-flash',
            contents=prompt
        )
        self.logger.info("Google GenAI call succeeded.")
        return response.text

    def handle_query(self, payload: Dict[str, Any]):
        """Handle direct queries"""
        pass