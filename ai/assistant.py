import json
import logging

from django.conf import settings
from openai.types.responses import ResponseFunctionToolCall, ResponseOutputMessage

from ai.openai import openai
from ai.tools import TOOLS_DESCRIPTION, TOOLS_MAP
from ai.config import PROMPT, USER_INPUT_MAX_LEN, OPENAI_CHAT_MODEL

log = logging.getLogger(__name__)


def ask_assistant(user_input):
    input_messages = [
        {"role": "system", "content": PROMPT},
        {"role": "user", "content": user_input[:USER_INPUT_MAX_LEN]}
    ]

    chat_response = openai.responses.create(
        model=OPENAI_CHAT_MODEL,
        input=input_messages,
        tools=TOOLS_DESCRIPTION,
        tool_choice="auto"
    )

    log.info(f"CHATGPT: {chat_response}")
    answer = []

    for output in chat_response.output:
        if isinstance(output, ResponseFunctionToolCall):
            log.info(f"Tool called: {output.name}")
            tool = TOOLS_MAP.get(output.name)
            tool_args = json.loads(output.arguments)

            if not tool:
                log.info(f"Tool {output.name} not found")
                answer.append(f"Tool {output.function.name} not found")
                continue

            try:
                tool_output = tool(**tool_args)
            except Exception as e:
                log.info(f"Error calling tool {output.name}: {e}")
                answer.append(f"Error calling tool {output.name}: {e}")
                continue

            input_messages.append(output)
            input_messages.append({
                "type": "function_call_output",
                "call_id": output.call_id,
                "output": str(tool_output)
            })

            chat_response_after_tool = openai.responses.create(
                model=OPENAI_CHAT_MODEL,
                input=input_messages,
            )
            log.info(f"Output 2: {chat_response_after_tool}")

            for tool_output in chat_response_after_tool.output:
                log.info(f"Message: {tool_output}")
                answer += [c.text for c in tool_output.content]

        elif isinstance(output, ResponseOutputMessage):
            log.info(f"Simple text returned: {output}")
            answer += [c.text for c in output.content]

    return answer
