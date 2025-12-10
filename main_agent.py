# main_agent.py

from agents.data_analytics_agent import create_data_analysis_agent
from agents.research_agent import create_research_agent
from agents.decider_agent import deciding_agent
from agents.planning_agent import planner
from agents.investment_agent import investment_agent
from agents.translation_agent import translate_to_hindi


import pandas as pd
import json
import traceback


class FinWellAgent:
    def __init__(self, userId,query,lang):
        """
        Orchestrates all financial intelligence agents.
        """
        self.userId = userId
        self.lang = lang
        self.query = query
        self.context = {}
        self.results = {}
        self.final_output = None
        self.errors = {}

    # ---------------------------------------------------------------
    # PIPELINE EXECUTION
    # ---------------------------------------------------------------
    def run_pipeline(self):
        try:
            agent_list = deciding_agent(self.query)
            print(f"\n{'='*60}")
            print(f"🎯 Agents to Run: {agent_list}")
            print(f"{'='*60}\n")

            if not agent_list:
                return {
                    "response": "No agents were selected to process your query."
                }

            for agent_name in agent_list:
                try:
                    # ------------------ AGENT : DATA ANALYSIS ------------------
                    if agent_name == "create_data_analysis_agent":
                        print("\n--- Step 1: Data Analysis ---")
                        
                        # 1) Get the analysis agent (we need USER ID here)
                        analysis_agent = create_data_analysis_agent(self.userId)

                        # 2) Ask the agent to summarize the analytics
                        analysis_response = analysis_agent("Summarize my financial analytics.")

                        # 3) Store response
                        self.context["data_analysis"] = analysis_response
                        self.results["data_analysis"] = analysis_response

                        print("✓ Data Analysis Complete")

                    # ------------------ AGENT : RESEARCH ------------------
                    elif agent_name == "create_research_agent":
                        print("\n--- Step 2: Research ---")
                        research = create_research_agent(self.query, self.context)
                        self.context["data_research"] = research
                        self.results["research"] = research
                        print("✓ Research Complete")

                    # ------------------ AGENT : INVESTMENT ------------------
                    elif agent_name == "investment_agent":
                        print("\n--- Step 3: Investment Analysis ---")
                        investment = investment_agent(self.query, self.context)
                        self.context["investment"] = investment
                        self.results["investment"] = investment
                        print("✓ Investment Analysis Complete")

                    # ------------------ AGENT : PLANNER ------------------
                    elif agent_name == "planner":
                        print("\n--- Step 4: Generating Plan ---")
                        plan = planner(self.query, self.context)
                        self.context["plan"] = plan
                        self.results["plan"] = plan
                        print("✓ Plan Generated")

                    else:
                        print(f"⚠ Unknown agent: {agent_name}")
                        self.errors[agent_name] = "Unknown agent"

                except Exception as e:
                    error_msg = f"Error in {agent_name}: {str(e)}"
                    print(f"❌ {error_msg}")
                    print(traceback.format_exc())
                    self.errors[agent_name] = error_msg
                    continue

            # Final structured output
            self.final_output = self._determine_final_output()

            if self.errors:
                self.final_output["errors"] = self.errors

            return self.final_output

        except Exception as e:
            print("❌ Critical error in pipeline:", e)
            return {
                "response": str(e),
                "errors": {"critical": str(e)}
            }

    # ---------------------------------------------------------------
    # FINAL OUTPUT SELECTION
    # ---------------------------------------------------------------
    def _determine_final_output(self):
        """
        Priority: plan > investment > research > data_analysis
        """
        if "plan" in self.results:
            main_response = self.results["plan"]
        elif "investment" in self.results:
            main_response = self.results["investment"]
        elif "research" in self.results:
            main_response = self.results["research"]
        elif "data_analysis" in self.results:
            main_response = self.results["data_analysis"]
        else:
            main_response = "No valid output generated."
        if self.lang=='hindi':
            main_response=translate_to_hindi(main_response)
        return {
            "response": main_response,
            "visualization": None
        }

    # ---------------------------------------------------------------
    # GETTERS
    # ---------------------------------------------------------------
    def get_all_results(self):
        return self.results

    def get_context(self):
        return self.context

    def get_errors(self):
        return self.errors


# ---------------------------------------------------------------
# EXTERNAL API FUNCTION
# ---------------------------------------------------------------
def run_agent_pipeline(userId,query: str,lang):
    """
    Loads CSV and runs the FinWellAgent pipeline.
    """
    

    pipeline = FinWellAgent(userId,query,lang)
    return pipeline.run_pipeline()
# ---------------------------------------------------------------
# LOCAL TESTING (run: python main_agent.py)
# ---------------------------------------------------------------
if __name__ == "__main__":
    print("\n===== TESTING MAIN AGENT PIPELINE =====\n")

    # Sample user query
    test_query = "Find me a good budget mobile phone affordable for me,Plan for buying the best amongst them with ideal timeline"

    try:
        print(f"Running pipeline for query: {test_query}\n")

        result = run_agent_pipeline('usr_rahul_001',test_query)

        print("\n===== FINAL OUTPUT =====")
        print(json.dumps(result, indent=4))
        print("========================\n")

    except Exception as e:
        print("\n❌ Error while running main agent pipeline:")
        print(e)
        print("========================\n")

    print("===== TEST COMPLETE =====\n")
