import os, json, re
from langchain.schema import HumanMessage, AIMessage
import pandas as pd
from llm.llm_setup import OpenAIAzure, OllamaAI

START_CODE_TAG = "<CODE_START>"
END_CODE_TAG = "</CODE_END>"
# model = AzureOpenAI()
# llm = model.create_chat_model()

class ChatBot():
    def __init__(self, df:pd.DataFrame):
        super().__init__()
        self.model = OpenAIAzure() #OllamaAI() #OpenAIAzure()
        self.model.setup_env()
        self.llm = self.model.create_chat_model()
        self.df = df
        self.header_list = self.df.columns.tolist()
        self.bak_question = ""
        # Return the python code with essential library import.
        self.task_instruction: str = """
        You are a data scientist and code python for me. 
        Please provide a python script that can be executed directly to solve the following problem and produce results.
        DO NOT USE CLASS!!!
        There is a dataframe in pandas (python).
        The name of the dataframe is `self.df`.
        The column name of the dataframe is `self.header_list`.
        These 2 variables are in a class, so DO NOT use 'locals()' to check if the `self.df` and `self.header_list` exist.
        ONLY use the data in 'self.df', do not make up new data. If there is no relevant data then just print "Cannot found data!"
        Return the python code with library like pandas, numpy, pyqt5, pypdf2, xlsxwriter and scipy. DO NOT use other libraries.
        If question is not about plot then make sure add print code to output the result.
        For example, the non-plot code should be like:
        print(df.nlargest(3, 'happiness_index')['country'])
        If question ask to pop-out a message window, please use QMessageBox from pyqt5.

        And make sure to prefix the python code with {START_CODE_TAG} exactly and suffix the code with {END_CODE_TAG} exactly 
        to get the answer to the following question :
        '''
        {QUESTION}
        '''
        """

        self.response_instruction: str = """
        Question: {QUESTION}
        Answer: {ANSWER}
    
        Rewrite the answer to the question in a conversational way.
        """

        self.error_correct_instruction: str = """
        Here is the initial instruction and quesiton user asked:
        {QUESTION}
        you generated this python code:
        {CODE}
        and this fails with the following error:
        {ERROR_RETURNED}
        Correct the python code and return a new python code that fixes the above mentioned error.  Do not generate the same code again.
        Make sure to prefix the python code with {START_CODE_TAG} exactly and suffix the code with {END_CODE_TAG} exactly.
        """
    def merge_instruction(self, prompt):
        full_instruction = self.task_instruction.format(START_CODE_TAG=START_CODE_TAG,
                                                    END_CODE_TAG=END_CODE_TAG,
                                                    QUESTION=prompt)
        self.first_instruction = full_instruction
        return full_instruction

    def merge_error_instruction(self, promt:str, code:str, error_msg:str):
        new_instruction = self.error_correct_instruction.format(QUESTION=self.first_instruction,
                                                                CODE=code,
                                                                ERROR_RETURNED=error_msg,
                                                                START_CODE_TAG=START_CODE_TAG,
                                                                END_CODE_TAG=END_CODE_TAG)
        return new_instruction
    def chat(self, full_instruction):
        resp = self.llm.invoke([HumanMessage(content=full_instruction)])
        return resp.content
    def extract_code(self, input_str:str):
        match = re.search(rf"{START_CODE_TAG}(.*){END_CODE_TAG}", input_str, re.DOTALL)
        if match:
            code = match.group(1).strip()
        return code

    def run_code(self, code:str):
        exec(code)
#
# # Sample DataFrame
# df = pd.DataFrame({
#     "country": ["United States", "United Kingdom", "France", "Germany", "Italy", "Spain", "Canada", "Australia", "Japan", "China"],
#     "gdp": [19294482071552, 2891615567872, 2411255037952, 3435817336832, 1745433788416, 1181205135360, 1607402389504, 1490967855104, 4380756541440, 14631844184064],
#     "happiness_index": [6.94, 7.16, 6.66, 7.07, 6.38, 6.4, 7.23, 7.22, 5.87, 5.12]
# })
# header_list = df.columns.tolist()
#
# # prompt = "Plot the histogram of countries showing for each the happiness_index, using different colors for each bar" # # # #"Plot the histogram of countries showing for each the happiness_index, using different colors for each bar" # # #"Which are the 5 happiest countries?"
# # prompt = "Which are the 3 countries with highest score in column gdp ?"
# prompt = "Please first find out all the asia countries in column 'country', and then calculate the sum of the gdp." #north american
#
#
# chat = ChatBot(df)
# full_instruction = chat.merge_instruction(prompt)
# resp = chat.chat(full_instruction)
# print(resp)
# print("Execution result:")
# code =chat.extract_code(resp)
# chat.run_code(code)