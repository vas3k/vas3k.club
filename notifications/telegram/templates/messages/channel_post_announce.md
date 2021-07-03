{% if post.emoji %}{{ post.emoji }} {% endif %}*{% if post.prefix %}{{ post.prefix }} {% endif %}[{{ post.title }}]({{ settings.APP_HOST }}{% url "show_post" post.type post.slug %}) {% if post.topic %} [{{ post.topic.name }}]{% endif %}*

{% load posts %}{% render_plain post 350 %}

➜ {{ settings.APP_HOST }}{% url "show_post" post.type post.slug %}
