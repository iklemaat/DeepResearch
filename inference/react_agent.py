import json
import json5
import os
from typing import Dict, Iterator, List, Literal, Optional, Tuple, Union
from qwen_agent.llm.schema import Message
from qwen_agent.utils.utils import build_text_completion_prompt
from openai import OpenAI, APIError, APIConnectionError, APITimeoutError
from transformers import AutoTokenizer 
from datetime import datetime
from qwen_agent.agents.fncall_agent import FnCallAgent
from qwen_agent.llm import BaseChatModel
from qwen_agent.llm.schema import ASSISTANT, DEFAULT_SYSTEM_MESSAGE, Message
from qwen_agent.settings import MAX_LLM_CALL_PER_RUN
from qwen_agent.tools import BaseTool
from qwen_agent.utils.utils import format_as_text_message, merge_generate_cfgs
from prompt import *
import time
import asyncio

from tool_file import *
from tool_scholar import *
from tool_python import *
from tool_search import *
from tool_visit import *
from tool_brave_search import *
from tool_brave_image_search import *

OBS_START = '<tool_response>'
OBS_END = '\n</tool_response>'

MAX_LLM_CALL_PER_RUN = int(os.getenv('MAX_LLM_CALL_PER_RUN', 100))

TOOL_CLASS = [
    FileParser(),
    Scholar(),
    Visit(),
    Search(),
    PythonInterpreter(),
    BraveSearch(),
    BraveImageSearch(),
]
TOOL_MAP = {tool.name: tool for tool in TOOL_CLASS}

import random
import datetime


def today_date():
    return datetime.date.today().strftime("%Y-%m-%d")

class MultiTurnReactAgent(FnCallAgent):
    def __init__(self,
                 function_list: Optional[List[Union[str, Dict, BaseTool]]] = None,
                 llm: Optional[Union[Dict, BaseChatModel]] = None,
                 **kwargs):

        self.llm_generate_cfg = llm.get("generate_cfg", {})
        self.llm_local_path = llm.get("model")

    def sanity_check_output(self, content):
        return "<think>" in content and "</think>" in content
    
    def call_server(self, msgs, model_name, api_key, api_base, stop_sequences, max_tries=10):
        client = OpenAI(
            api_key=api_key,
            base_url=api_base,
            timeout=600.0,
        )

        base_sleep_time = 1 
        for attempt in range(max_tries):
            try:
                print(f"--- Attempting to call the service, try {attempt + 1}/{max_tries} ---")
                chat_response = client.chat.completions.create(
                    model=model_name,
                    messages=msgs,
                    stop=stop_sequences,
                    temperature=self.llm_generate_cfg.get('temperature', 0.6),
                    top_p=self.llm_generate_cfg.get('top_p', 0.95),
                    logprobs=True,
                    max_tokens=10000,
                    presence_penalty=self.llm_generate_cfg.get('presence_penalty', 1.1)
                )
                content = chat_response.choices[0].message.content

                if content and content.strip():
                    print("--- Service call successful, received a valid response ---")
                    return content.strip()
                else:
                    print(f"Warning: Attempt {attempt + 1} received an empty response.")

            except (APIError, APIConnectionError, APITimeoutError) as e:
                print(f"Error: Attempt {attempt + 1} failed with an API or network error: {e}")
            except Exception as e:
                print(f"Error: Attempt {attempt + 1} failed with an unexpected error: {e}")

            if attempt < max_tries - 1:
                sleep_time = base_sleep_time * (2 ** attempt) + random.uniform(0, 1)
                sleep_time = min(sleep_time, 30) 
                
                print(f"Retrying in {sleep_time:.2f} seconds...")
                time.sleep(sleep_time)
            else:
                print("Error: All retry attempts have been exhausted. The call has failed.")
        
        return "LLM server error!!!"

    def count_tokens(self, messages):
        if not self.llm_local_path:
            # Cannot count tokens without a tokenizer path
            return 0
        tokenizer = AutoTokenizer.from_pretrained(self.llm_local_path) 
        full_prompt = tokenizer.apply_chat_template(messages, tokenize=False)
        tokens = tokenizer(full_prompt, return_tensors="pt")
        token_count = len(tokens["input_ids"][0])
        
        return token_count

    def _run(self, data: str, api_keys: Dict[str, str], **kwargs) -> List[List[Message]]:
        try:
            question = data['item']['question']
        except: 
            raw_msg = data['item']['messages'][1]["content"] 
            question = raw_msg.split("User:")[1].strip() if "User:" in raw_msg else raw_msg 

        start_time = time.time()
        answer = data['item']['answer']
        self.user_prompt = question

        # Step 1: Call the planner LLM
        planner_model_name = os.getenv('PLANNER_MODEL_NAME', 'deepseek/deepseek-coder')
        deepseek_api_key = api_keys.get('deepseek')
        deepseek_api_base = os.getenv('DEEPSEEK_API_BASE', 'https://api.deepseek.com')

        planner_messages = [{"role": "system", "content": PLANNER_PROMPT}, {"role": "user", "content": question}]

        research_plan = self.call_server(
            planner_messages,
            planner_model_name,
            deepseek_api_key,
            deepseek_api_base,
            stop_sequences=None
        )

        if "LLM server error!!!" in research_plan:
             return {
                "question": question,
                "answer": answer,
                "messages": planner_messages,
                "prediction": "Failed to generate a research plan.",
                "termination": "Planner LLM failed."
            }

        # Step 2: Call the execution LLM with the research plan
        execution_model_name = os.getenv('EXECUTION_MODEL_NAME', 'alibaba/tongyi-deepresearch-30b-a3b')
        openrouter_api_key = api_keys.get('openrouter')
        openrouter_api_base = os.getenv('OPENROUTER_API_BASE', 'https://openrouter.ai/api/v1')
        brave_api_key = api_keys.get('brave')

        execution_system_prompt = EXECUTION_PROMPT.format(plan_from_planner=research_plan)
        execution_system_prompt += str(today_date())

        messages = [{"role": "system", "content": execution_system_prompt}, {"role": "user", "content": question}]

        num_llm_calls_available = MAX_LLM_CALL_PER_RUN
        round = 0
        while num_llm_calls_available > 0:
            if time.time() - start_time > 150 * 60:
                return {
                    "question": question,
                    "answer": answer,
                    "messages": messages,
                    "prediction": "No answer found after 2h30mins",
                    "termination": "Timeout"
                }

            round += 1
            num_llm_calls_available -= 1

            content = self.call_server(
                messages,
                execution_model_name,
                openrouter_api_key,
                openrouter_api_base,
                stop_sequences=["\n<tool_response>", "<tool_response>"]
            )

            print(f'Round {round}: {content}')
            if '<tool_response>' in content:
                pos = content.find('<tool_response>')
                content = content[:pos]
            messages.append({"role": "assistant", "content": content.strip()})

            if '<tool_call>' in content and '</tool_call>' in content:
                tool_call = content.split('<tool_call>')[1].split('</tool_call>')[0]
                try:
                    if "python" in tool_call.lower():
                        try:
                            code_raw=content.split('<tool_call>')[1].split('</tool_call>')[0].split('<code>')[1].split('</code>')[0].strip()
                            result = TOOL_MAP['PythonInterpreter'].call(code_raw)
                        except:
                            result = "[Python Interpreter Error]: Formatting error."
                    else:
                        tool_call = json5.loads(tool_call)
                        tool_name = tool_call.get('name', '')
                        tool_args = tool_call.get('arguments', {})
                        result = self.custom_call_tool(tool_name, tool_args, brave_api_key=brave_api_key)
                except:
                    result = 'Error: Tool call is not a valid JSON. Tool call must contain a valid "name" and "arguments" field.'

                result = "<tool_response>\n" + result + "\n</tool_response>"
                messages.append({"role": "user", "content": result})

            if '<answer>' in content and '</answer>' in content:
                break

        if '<answer>' in messages[-1]['content']:
            prediction = messages[-1]['content'].split('<answer>')[1].split('</answer>')[0]
            termination = 'answer'
        else:
            prediction = 'No answer found.'
            termination = 'answer not found'

        result = {
            "question": question,
            "answer": answer,
            "messages": messages,
            "prediction": prediction,
            "termination": termination
        }
        return result

    def custom_call_tool(self, tool_name: str, tool_args: dict, **kwargs):
        if tool_name in TOOL_MAP:
            tool_args["params"] = tool_args
            # Pass kwargs (which includes brave_api_key) to all tools
            raw_result = TOOL_MAP[tool_name].call(tool_args, **kwargs)
            result = raw_result
            if not isinstance(raw_result, str):
                result = str(raw_result)
            return result
        else:
            return f"Error: Tool {tool_name} not found"
