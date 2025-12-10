#decider_agent.py

import json
from agents.llm_main import llm  # Assuming this is your initialized LLM instance
from textwrap import dedent
from typing import List

# --- MODIFIED: Added rag_agent ---
AGENT_DEFINITIONS = {
    "create_data_analysis_agent": "Analyzes the user's financial data to find stats, trends, and anomalies. This should almost always be the first step.",
    "create_research_agent": "Performs external research online for information not in the user's data (e.g., flight costs, product prices, investment tips).",
    "planner": "Synthesizes all gathered information into a final, actionable plan or roadmap. This should usually be the last step.",
    "investment_agent": "Analyzes investment options and suggests the best investment or loan schemes based on the user's financial data and requirements."
}
# --- END MODIFICATION ---

def deciding_agent(query: str) -> List[str]:
    """
    Uses an LLM to decide which agents to run in what order.
    Returns a proper Python list of agent names.
    """
    
    tools_description = "\n".join(f"- {name}: {desc}" for name, desc in AGENT_DEFINITIONS.items())
    
    # List valid agent names explicitly
    valid_agents = list(AGENT_DEFINITIONS.keys())
    valid_agents_str = json.dumps(valid_agents)

    # --- MODIFIED: Added a new example for rag_agent ---
    prompt = dedent(f"""
        You are an expert router agent. Your job is to analyze a user's query and decide which tools (agents) need to be run in a specific sequence to answer it.

        *User Query:* "{query}"

        *Available Tools:*
        {tools_description}

        *Valid Agent Names (use ONLY these):*
        {valid_agents_str}

        *Your Task:*
        Return ONLY a JSON array of agent names (strings) to be executed in order. Do not include any markdown formatting, explanations, or other text.

        *Rules:*
        1. Use only agent names from the valid list above
        2. Return pure JSON array format: ["agent1", "agent2"]
        3. If data analysis is needed, include "create_data_analysis_agent" first
        4. If a plan is needed, include "planner" last
        5. Do not wrap in markdown code blocks


        *Example 2:*
        Query: "How much would a trip to Goa cost, and can you create a savings plan?"
        Response: ["create_data_analysis_agent", "create_research_agent", "planner"]

        *Example 3:*
        Query: "What are the best investment options for me?"
        Response: ["create_data_analysis_agent", "investment_agent"]
        
        
        Now analyze this query and return ONLY the JSON array:
    """)
    # --- END MODIFICATION ---

    try:
        response = llm.invoke(prompt)
        
        # Extract content
        if hasattr(response, 'content'):
            response_str = response.content
        else:
            response_str = str(response)

        # Clean up the response more aggressively
        clean_str = response_str.strip()
        
        # Remove markdown code blocks
        clean_str = clean_str.replace("json", "").replace("`", "").strip() # Fixed typo: `` to `
        
        # If response has extra text, try to extract just the JSON array
        if not clean_str.startswith('['):
            # Try to find JSON array in the response
            start_idx = clean_str.find('[')
            end_idx = clean_str.rfind(']') + 1
            if start_idx != -1 and end_idx > start_idx:
                clean_str = clean_str[start_idx:end_idx]
            else:
                raise ValueError(f"No JSON array found in response: {response_str[:100]}...")
        
        # Parse JSON
        agent_list = json.loads(clean_str)
        
        # Validate it's a list
        if not isinstance(agent_list, list):
            raise ValueError(f"Expected list, got {type(agent_list)}: {agent_list}")
        
        # Validate all agents exist
        invalid_agents = [a for a in agent_list if a not in AGENT_DEFINITIONS]
        if invalid_agents:
            print(f"⚠  Warning: Unknown agents will be skipped: {invalid_agents}")
            # Filter out invalid agents
            agent_list = [a for a in agent_list if a in AGENT_DEFINITIONS]
        
        if not agent_list:
            print("⚠  Warning: No valid agents selected. Defaulting to data analysis.")
            return ["create_data_analysis_agent"]
        
        print(f"✓ Selected agents: {agent_list}")
        return agent_list

    except json.JSONDecodeError as e:
        print(f"❌ Error: Failed to parse JSON from LLM output.")
        print(f"   Raw response: '{response_str[:200]}...'")
        print(f"   JSON Error: {e}")
        # Fallback to safe default
        print("   Defaulting to: ['create_data_analysis_agent']")
        return ["create_data_analysis_agent"]
    
    except Exception as e:
        print(f"❌ Unexpected error in deciding_agent: {e}")
        print(f"   Raw response: '{response_str[:200] if 'response_str' in locals() else 'N/A'}...'")
        print("   Defaulting to: ['create_data_analysis_agent']")
        return ["create_data_analysis_agent"]

# ---------------------------------------------------------
# LOCAL TESTING (run: python decider_agent.py)
# ---------------------------------------------------------
if __name__ == "__main__":
    print("\n===== TESTING DECIDER AGENT =====\n")

    test_queries = [
        "Analyze my spending",
        "Show me a chart of my expenses",
        "Plan a trip to Goa and create a budget",
        "What are the best investment options?",
        "I want to buy a car, help me plan my finances",
        "Summarize this document"  # For future RAG if added again
    ]
    
    for query in test_queries:
        print(f"\n🔍 Query: {query}")
        try:
            agents = deciding_agent(query)
            print(f"📋 Selected Agents: {agents}")
        except Exception as e:
            print(f"❌ Error running deciding_agent: {e}")
        print("-" * 60)

    print("\n===== TEST COMPLETE =====\n")
