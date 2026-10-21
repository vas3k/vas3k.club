Привет, {{ user.full_name }}!

Ваша подписка давно закончилась и сейчас мы удаляем вас из клубных Telegram-чатов. Аккаунт и профиль останутся на месте.
{% if rooms %}
Вот чаты, из которых вас удалят: {% for room in rooms|slice:":20" %}{% if room.icon %}{{ room.icon }} {% endif %}{{ room.chat_name }}{% if not forloop.last %}, {% endif %}{% endfor %}.
{% endif %}
Если хотите остаться — продлите подписку. Доступ восстановится, а в чаты можно будет зайти снова:

[.button.button-big Восстановить доступ]({{ settings.APP_HOST }}{% url "edit_payments" user.slug %})

Спасибо, что были с нами. Будем ждать вас обратно 🖤
