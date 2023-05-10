import os, json, re
import openai
import shutil
from dotenv import load_dotenv
from langchain.llms import AzureOpenAI
from langchain.chat_models import AzureChatOpenAI


class OpenAIAzure():
    def __init__(self):
        super().__init__()

        self.WORK_ENV_DIR = './'
        self.ENV_FILE = 'key.txt'
        self.config_details = {}
    def setup_env(self):
        # Load OpenAI key
        if os.path.exists(os.path.join(self.WORK_ENV_DIR, self.ENV_FILE)):
            shutil.copyfile(os.path.join(self.WORK_ENV_DIR, self.ENV_FILE), ".env")
            load_dotenv()
        else:
            raise APIKeyNotFoundError("key.txt with OpenAI API is required")

        # Load config values
        if os.path.exists(os.path.join(r'config.json')):
            with open(r'config.json') as config_file:
                self.config_details = json.load(config_file)

            # Setting up the embedding model
            embedding_model_name = self.config_details['EMBEDDING_MODEL']
            openai.api_type = "azure"
            openai.api_base = self.config_details['OPENAI_API_BASE']
            openai.api_version = self.config_details['EMBEDDING_MODEL_VERSION']
            openai.api_key = os.getenv("OPENAI_API_KEY")
        else:
            raise AzureConfigNotFoundError("config.json with Azure OpenAI config is required")

    def create_chat_model(self):
        # max LLM token input size
        max_input_size = 3900  # 4096
        # set number of output tokens
        num_output = 1024  # 512
        # set maximum chunk overlap
        max_chunk_overlap = 20
        return AzureChatOpenAI(deployment_name=self.config_details['CHATGPT_MODEL'],
                               openai_api_key=openai.api_key,
                               openai_api_base=openai.api_base,
                               openai_api_type=openai.api_type,
                               openai_api_version=self.config_details['OPENAI_API_VERSION'],
                               max_tokens=num_output,
                               temperature=0.5,
                               )


class APIKeyNotFoundError(Exception):
    """
    Raised when the API key is not defined/declared.

    Args:
        Exception (Exception): APIKeyNotFoundError
    """

class AzureConfigNotFoundError(Exception):
    """
    Raised when the API key is not defined/declared.

    Args:
        Exception (Exception): APIKeyNotFoundError
    """