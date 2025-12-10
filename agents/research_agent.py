# research_agent.py
from langchain.agents import AgentExecutor, Tool, create_react_agent
from langchain_community.tools.tavily_search import TavilySearchResults
from langchain.prompts import PromptTemplate
from langchain_tavily import TavilySearch
from agents.llm_main import llm

# This function now correctly takes the user's query and the analysis context
def create_research_agent(query: str, analysis_context: str):
    """Creates a research agent that uses context from data analysis."""
    
    tavily_tool = TavilySearch(max_results=2)
    tools = [
        Tool(
            name="TavilySearch",
            func=tavily_tool.invoke,
            description="Use this tool to search the web for information about trip costs, product prices, deals, and suggestions."
        )
    ]

    # This is the PROPER ReAct prompt format, with your instructions added
    prompt_template = """
    Answer the following questions as best you can. You have access to the following tools:
    {tools}

    Use the following format:
    Question: the input question you must answer
    Thought: you should always think about what to do
    Action: the action to take, should be one of [{tool_names}]
    Action Input: the input to the action
    Observation: the result of the action
    ... (this Thought/Action/Action Input/Observation can repeat N times)
    Thought: I now know the final answer
    Final Answer: the final answer to the original input question

    Begin!

    HERE IS THE USER'S FINANCIAL CONTEXT:
    {analysis_context}

    IMPORTANT:
    • All monetary values coming from the Data Analytics Agent are in **paise**.
    • You MUST convert paise to rupees whenever you mention money.
    • Conversion: ₹1 = 100 paise → rupees = paise / 100.

    Based on the financial context above, provide a helpful and personalized answer to the user's question.
    Your suggestions for trips, products, or plans MUST be reasonable for someone with this financial background.
    
    Question: {input}
    Thought:{agent_scratchpad}
    """

    prompt = PromptTemplate(
        input_variables=["analysis_context", "input", "agent_scratchpad", "tool_names", "tools"],
        template=prompt_template
    )

    agent = create_react_agent(llm, tools, prompt)
    
    agent_executor = AgentExecutor(
        agent=agent, 
        tools=tools,
        verbose=True,
        handle_parsing_errors=True
    )
    
    # Pass the context to the prompt when invoking the agent
    return agent_executor.invoke({
        "input": query,
        "analysis_context": analysis_context
    })
