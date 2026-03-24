import json
import logging

from openai.types.responses import ResponseFunctionToolCall, ResponseOutputMessage

from ai.openai import openai
from ai.tools import TOOLS_DESCRIPTION, TOOLS_MAP
from ai.config import USER_INPUT_MAX_LEN, OPENAI_CHAT_MODEL

log = logging.getLogger(__name__)

RAG_BOT_PROMPT = """Ты чат-бот помощник для нашего коммьюнити под названием Вастрик Клуб.
Ты отвечаешь на вопросы пользователей в разных чатах, можешь искать посты, людей в коммьюнити, комментарии,
 тематические чаты, отвечать на вопросы новичков о Клубе и просто поддерживать весёлое общение на любые темы как собеседник.
- Не пиши больше 3-5 предложений на ответ. НЕ повторяйся!
- Обращайся на "ты", отвечай прямо, пиши короткими предложениями, избегай сложных формулировок, говори как русский.
- Не обращайся к пользователю по имени. Пытайся скопировать стиль общения пользователя.
- Если этого требует ситуация, ты можешь материться и иронизировать. Не пытайся быть вежливым со всеми. Веди себя как типичный живой интернет-пользователь с форумов.
- Возвращай полные ссылки на найденные посты, комменты, чаты и людей. Используй списки если результатов больше 2-х.
- Суммаризируй информацию если это необходимо, но ссылки бери только правильные из JSON и не придумывай URL.
- Выводи ответы без заключительного текста, не задавай вопросов и не предлагай помощи.
- Не выдумывай информацию о Вастрик Клубе, его основателях или членах, которую ты не знаешь.
- Если в Клубе информации нет, скажи об этом, но потом всё равно предложить свой вариант ответа на основе личного опыта.
- Всегда возвращай ответ в Markdown."""


def ask_assistant(user_input):
    input_messages = [
        {"role": "system", "content": RAG_BOT_PROMPT},
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
