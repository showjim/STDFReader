import os, json, re
from langchain.schema import HumanMessage, AIMessage
import pandas as pd
from llm.llm_setup import LLM

START_CODE_TAG = "<CODE_START>"
END_CODE_TAG = "</CODE_END>"
model = LLM()
llm = model.create_chat_model()

class ChatBot():
    def __init__(self, df:pd.DataFrame):
        super().__init__()
        self.df = df
        self.header_list = self.df.columns.tolist()
        self.task_instruction: str = """
        There is a dataframe in pandas (python).
        The name of the dataframe is `self.df`.
        The column name of the dataframe is `self.header_list`.
        ONLY use the data in 'df', do not make up new data. If there is no relavent data then just print "Cannot found data!"
        Return the python code (do not import anything) ONLY. 
        If question is not about plot then make sure add print code to output the result.
        For example, the non-plot code should be like:
        print(df.nlargest(3, 'happiness_index')['country'])

        And make sure to prefix the python code with {START_CODE_TAG} exactly and suffix the code with {END_CODE_TAG} exactly 
        to get the answer to the following question :
        '''
        {QUESTION}
        '''
        """

        self.response_instruction: str = """
        Question: {question}
        Answer: {answer}
    
        Rewrite the answer to the question in a conversational way.
        """

        self._error_correct_instruction: str = """
        For the task defined below:
        {orig_task}
        you generated this python code:
        {code}
        and this fails with the following error:
        {error_returned}
        Correct the python code and return a new python code (do not import anything) that fixes the above mentioned error.
        Make sure to prefix the python code with {START_CODE_TAG} exactly and suffix the code with {END_CODE_TAG} exactly.
        """
    def merge_instruction(self, prompt):
        full_instruction = self.task_instruction.format(START_CODE_TAG=START_CODE_TAG,
                                                    END_CODE_TAG=END_CODE_TAG,
                                                    QUESTION=prompt)
        return full_instruction
    def chat(self, full_instruction):
        resp = llm([HumanMessage(content=full_instruction)])
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