# Changelog

## [Unreleased](https://github.com/vas3k/vas3k.club/tree/HEAD)

[Full Changelog](https://github.com/vas3k/vas3k.club/compare/c3f7a94bc5e34f4a175bb95202f7b6a8278752db...HEAD)

**Implemented enhancements:**

- Сделать, чтобы даже у закрытых постов был виден title и первое предложение наружу в og-тегах. А то люди с покетом страдают [\#251](https://github.com/vas3k/vas3k.club/issues/251)
- После смены порядка комментариев перекидывать к комментариеям [\#192](https://github.com/vas3k/vas3k.club/issues/192)
- Написать кастомную регулярку для парсинга Medium, как уже сделано для Github и YouTube [\#143](https://github.com/vas3k/vas3k.club/issues/143)
- Научить всратый AI присылать комментарии из батлов с указанием выбранной стороны [\#131](https://github.com/vas3k/vas3k.club/issues/131)
- Отображать время написания комментариев [\#115](https://github.com/vas3k/vas3k.club/issues/115)
- Сортировка комментариев в посте [\#110](https://github.com/vas3k/vas3k.club/issues/110)
- Не разворачивать ссылки на YouTube/Twitter/картинки если они сделаны через тег [\#107](https://github.com/vas3k/vas3k.club/issues/107)
- Принудительно конвертировать загружаемые в комментах картинки в JPG [\#102](https://github.com/vas3k/vas3k.club/issues/102)
- В мобильной версии при открытии вопроса нет кнопки "войти"  [\#87](https://github.com/vas3k/vas3k.club/issues/87)
- Кликабельные интересы в профилях участников [\#80](https://github.com/vas3k/vas3k.club/issues/80)
- Кастомизировать редактирование интро [\#78](https://github.com/vas3k/vas3k.club/issues/78)
- Отправка комментария на Ctrl+Enter [\#70](https://github.com/vas3k/vas3k.club/issues/70)
- Вернуть выбор топика в батлы [\#69](https://github.com/vas3k/vas3k.club/issues/69)
- Добавить кнопку редактирования интро прям в профиль пользователя [\#62](https://github.com/vas3k/vas3k.club/issues/62)
- Поиск по сайту [\#61](https://github.com/vas3k/vas3k.club/issues/61)
- Не получается удалить свой ответ к баттл-посту [\#58](https://github.com/vas3k/vas3k.club/issues/58)
- Постить тематические посты по соответствующим чатам [\#52](https://github.com/vas3k/vas3k.club/issues/52)
- Реплай к новому комменту налезает на его фон [\#46](https://github.com/vas3k/vas3k.club/issues/46)
- Выделять меншены в комментах [\#40](https://github.com/vas3k/vas3k.club/issues/40)
- Сменить стиль выделения комментария по ссылке? [\#31](https://github.com/vas3k/vas3k.club/issues/31)
- Возможность подписаться на обновления в чужих постах [\#23](https://github.com/vas3k/vas3k.club/issues/23)
- Отображение моих комментариев в личном кабинете [\#22](https://github.com/vas3k/vas3k.club/issues/22)
- Выделять непрочитанные комментарии внутри поста [\#20](https://github.com/vas3k/vas3k.club/issues/20)
- Markdown-парсер должен поддерживать одинарный перевод строки как \<br\> [\#18](https://github.com/vas3k/vas3k.club/issues/18)
- Запретить в интерфейсе голосовать за свои посты и комменты [\#17](https://github.com/vas3k/vas3k.club/issues/17)
- Профиль - ссылки [\#13](https://github.com/vas3k/vas3k.club/issues/13)
- Придумать как должны кликаться посты в фиде [\#7](https://github.com/vas3k/vas3k.club/issues/7)

**Fixed bugs:**

- В комментах отвалились шоткаты редактора. Например, Cmd+B для жирного текста и другие [\#226](https://github.com/vas3k/vas3k.club/issues/226)
- Убрать перенос на новую строку в счетчиках комментариев [\#212](https://github.com/vas3k/vas3k.club/issues/212)
- Текст внутри тэга pre вылезает за пределы блока [\#196](https://github.com/vas3k/vas3k.club/issues/196)
- Дата поста вылазит за границы поста в мобильной версии если указана длинная должность [\#195](https://github.com/vas3k/vas3k.club/issues/195)
- Мобильная версия клуба | Элемент счетчика плюсов в \#intro перекрывает текст  [\#188](https://github.com/vas3k/vas3k.club/issues/188)
- Встратый AI пишет "Новый коммент к вашему посту", про любой подписанный пост [\#173](https://github.com/vas3k/vas3k.club/issues/173)
- В выдаваемых в поиске комментариях нет ссылки на оригинальный пост [\#164](https://github.com/vas3k/vas3k.club/issues/164)
- Рендеринг страницы ломается если в тексте использовать {{variable}} [\#160](https://github.com/vas3k/vas3k.club/issues/160)
- Draft-посты попадают в поиск [\#135](https://github.com/vas3k/vas3k.club/issues/135)
- Проблемы с вёрсткой  на мобильном [\#133](https://github.com/vas3k/vas3k.club/issues/133)
- Бездушная машина - ошибка кодировки [\#127](https://github.com/vas3k/vas3k.club/issues/127)
- При реплае пользователю на iOS курсор оказывается в начале строки [\#124](https://github.com/vas3k/vas3k.club/issues/124)
- Непоследовательное использование шрифтов в профиле [\#120](https://github.com/vas3k/vas3k.club/issues/120)
- Не работает кнопка-рейтинг интро для ширины экрана \< 1024px [\#118](https://github.com/vas3k/vas3k.club/issues/118)
- Блокировать кнопку «ответить» при отправке комментария [\#114](https://github.com/vas3k/vas3k.club/issues/114)
- Не отображается превью твитов в лисичке [\#99](https://github.com/vas3k/vas3k.club/issues/99)
- Search pagination has broken links [\#92](https://github.com/vas3k/vas3k.club/issues/92)
- Форма комментариев едет от длинных ссылок [\#56](https://github.com/vas3k/vas3k.club/issues/56)
- Вместе с никами регулярочка выделяет еще и остальные надписи [\#51](https://github.com/vas3k/vas3k.club/issues/51)
- Менять свитчер мобильной версии на ночную если пользователь предпочитает ночную версию [\#44](https://github.com/vas3k/vas3k.club/issues/44)
- При публикации черновика пост падает вниз в истории к дате создания черновика [\#29](https://github.com/vas3k/vas3k.club/issues/29)
- Шрифт на кнопке "Черновик" остается белым в тёмной теме  [\#25](https://github.com/vas3k/vas3k.club/issues/25)
- У интро маленькая кликабельная зона [\#9](https://github.com/vas3k/vas3k.club/issues/9)
- Не могу смотреть закрытые посты [\#5](https://github.com/vas3k/vas3k.club/issues/5)

**Closed issues:**

- Хотет в ежедневном дайджесте ежедневный дайджест [\#217](https://github.com/vas3k/vas3k.club/issues/217)
- Автоматический дамп текущей базы для dev-окружения [\#213](https://github.com/vas3k/vas3k.club/issues/213)
- Каждый день как и вчера [\#211](https://github.com/vas3k/vas3k.club/issues/211)
- Визуализировать результаты батлов [\#129](https://github.com/vas3k/vas3k.club/issues/129)
- Сортировка по дате добавления поста [\#76](https://github.com/vas3k/vas3k.club/issues/76)
- Добавить поддержку InstantView для постов клуба [\#66](https://github.com/vas3k/vas3k.club/issues/66)
- Карта мира с аватарками членов клуба [\#60](https://github.com/vas3k/vas3k.club/issues/60)
- Использовать системную тему [\#47](https://github.com/vas3k/vas3k.club/issues/47)
- Нельзя редактировать заголовки у комментариев [\#42](https://github.com/vas3k/vas3k.club/issues/42)
- Оптимизировать размер фронтенда [\#33](https://github.com/vas3k/vas3k.club/issues/33)
- Профиль - что за "Экспертиза" [\#15](https://github.com/vas3k/vas3k.club/issues/15)
- Профиль - альтернативная активация бота [\#14](https://github.com/vas3k/vas3k.club/issues/14)



\* *This Changelog was automatically generated by [github_changelog_generator](https://github.com/github-changelog-generator/github-changelog-generator)*
