import json
import logging

from openai.types.responses import Response, ResponseFunctionToolCall

from ai.openai import openai
from ai.tools import TOOLS_DESCRIPTION, TOOLS_MAP
from ai.config import USER_INPUT_MAX_LEN, OPENAI_CHAT_MODEL

log = logging.getLogger(__name__)

ASSISTANT_TEMPERATURE = 0.7
ASSISTANT_MAX_OUTPUT_TOKENS = 1000

RAG_BOT_PROMPT = """Ты чат-бот помощник для нашего коммьюнити под названием Вастрик Клуб.
Ты отвечаешь на вопросы пользователей в разных чатах, можешь искать посты, людей в коммьюнити, комментарии,
 тематические чаты, отвечать на вопросы новичков о Клубе и просто поддерживать весёлое общение на любые темы как собеседник.
- Отвечай коротко, ровно сколько нужно и НЕ повторяйся!
- Обращайся на "ты", отвечай прямо, пиши короткими предложениями, избегай сложных формулировок, говори как русский.
- Не обращайся к пользователю по имени. Пытайся скопировать стиль общения пользователя.
- Не пытайся быть вежливым со всеми. Веди себя как типичный живой интернет-пользователь с форумов. Подстраивайся под ситуацию.
- Возвращай полные ссылки на найденные посты, комменты, чаты и людей. Используй списки если результатов больше 2-х.
- Суммаризируй информацию если это необходимо, но ссылки бери только правильные из JSON и не придумывай URL.
- Выводи ответы без заключительного текста, не задавай вопросов и не предлагай помощи.
- Не выдумывай информацию о Вастрик Клубе, его основателях или членах, которую ты не знаешь.
- Если в Клубе информации нет, скажи об этом, но потом всё равно предложить свой вариант ответа на основе личного опыта.
- Всегда возвращай ответ в Markdown."""


def ask_assistant(user_input: str) -> str:
    input_messages = [
        {"role": "user", "content": user_input[:USER_INPUT_MAX_LEN]}
    ]

    response: Response = openai.responses.create(
        model=OPENAI_CHAT_MODEL,
        instructions=RAG_BOT_PROMPT,
        input=input_messages,
        tools=TOOLS_DESCRIPTION,
        tool_choice="auto",
        temperature=ASSISTANT_TEMPERATURE,
        max_output_tokens=ASSISTANT_MAX_OUTPUT_TOKENS,
        truncation="auto",
        store=False,
    )

    log.info(f"CHATGPT: {response}")

    # собираем все tool calls из ответа перед выполнением
    tool_calls = [o for o in response.output if isinstance(o, ResponseFunctionToolCall)]

    if not tool_calls:
        return response.output_text

    # выполняем все tool calls и добавляем результаты в контекст
    for tool_call in tool_calls:
        log.info(f"Tool called: {tool_call.name}")
        tool = TOOLS_MAP.get(tool_call.name)

        if not tool:
            log.warning(f"Tool {tool_call.name} not found")
            input_messages.append(tool_call)
            input_messages.append({
                "type": "function_call_output",
                "call_id": tool_call.call_id,
                "output": f"Unknown tool: {tool_call.name}",
            })
            continue

        try:
            tool_args = json.loads(tool_call.arguments)
            result = tool(**tool_args)
        except Exception as e:
            log.exception(f"Error calling tool {tool_call.name}")
            input_messages.append(tool_call)
            input_messages.append({
                "type": "function_call_output",
                "call_id": tool_call.call_id,
                "output": "Ошибка при выполнении поиска",
            })
            continue

        input_messages.append(tool_call)
        input_messages.append({
            "type": "function_call_output",
            "call_id": tool_call.call_id,
            "output": str(result),
        })

    # один follow-up вызов со всеми результатами tool calls
    follow_up: Response = openai.responses.create(
        model=OPENAI_CHAT_MODEL,
        instructions=RAG_BOT_PROMPT,
        input=input_messages,
        temperature=ASSISTANT_TEMPERATURE,
        max_output_tokens=ASSISTANT_MAX_OUTPUT_TOKENS,
        truncation="auto",
        store=False,
    )

    log.info(f"CHATGPT follow-up: {follow_up}")
    return follow_up.output_text
