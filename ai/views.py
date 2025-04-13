from django.shortcuts import render

from ai.assistant import ask_assistant
from authn.decorators.auth import require_auth
from club.exceptions import AccessDenied
from ai.forms import LlmAgentForm


@require_auth
def llm_agent_playground(request):
    if not request.me.is_god:
        raise AccessDenied()

    if request.method == "POST":
        form = LlmAgentForm(request.POST)
        if form.is_valid():
            user_input = form.cleaned_data["input"]
            answer = ask_assistant(user_input)

            return render(request, "message.html", {
                "title": f"",
                "message": "\n\n".join(answer),
            })
    else:
        form = LlmAgentForm()

    return render(request, "admin/simple_form.html", {"form": form})
