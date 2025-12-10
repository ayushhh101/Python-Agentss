from agents.llm_main import llm

def load_icici_data():
    """Reads ICICI bank schemes text file."""
    try:
        with open("icici_one.txt", "r", encoding="utf-8") as f:
            return f.read()
    except Exception as e:
        return f"Error reading ICICI data: {e}"

def investment_agent(query, context):
    """Returns the investment analysis using ICICI product data."""
    
    icici_data = load_icici_data()

    data_analysis = context.get('data_analysis', 'No analysis available.')
    data_research = context.get('data_research', 'No research available.')

    prompt = f"""
        You are a helpful financial investment assistant.

        User Query: {query}

        IMPORTANT:
        - All monetary values coming from the Data Analytics Agent are in **paise**.
        - Convert paise → rupees using: rupees = paise / 100.

        User's Bank Statement Analysis:
        {data_analysis}

        Product Research Information:
        {data_research}

        ICICI Bank Schemes and Policies:
        {icici_data}

        Your task:
        - Suggest the best investment or loan schemes for the user.
        - Use only the data provided above.
        - Consider the user's income, savings, and financial behavior.
        - Provide reasoning and final recommendations.
    """

    llm_response = llm.invoke(prompt)
    return llm_response.content if hasattr(llm_response, "content") else str(llm_response)
