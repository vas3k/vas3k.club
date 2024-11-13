<template>
    <span
        class="comment-scroll-arrow"
        :class="{
            'arrow-up': arrowDirection === 'Up'
        }"
        @click.prevent="onArrowClickHandler"
    >
    </span>
</template>

<script>
import { throttle } from "../common/utils.js";

export default {
    name: "CommentScrollArrow",
    data() {
        return {
            arrowDirection: "Down",
            scrollThrottleDelay: 150,
        };
    },
    methods: {
        getBodyTop() {
            return document.body.getBoundingClientRect().top;
        },
        getElementMargin(el) {
             const style = window.getComputedStyle(el);
             return parseInt(style.scrollMarginTop, 10);
         },
        scrollToElement(el, callback) {
            const oldHash = document.location.hash;
            const newHash = `#${el.id}`;
            if (oldHash === newHash) {
                // zero the hash so that there is no sticking if we are already on this element
                history.pushState(null, null, '');
            }

            document.documentElement.style.scrollBehavior = "smooth";

            const offset = el.getBoundingClientRect().top - this.getBodyTop() - this.getElementMargin(el);

            const onScroll = () => {
                const scrolledToElement = Math.abs(offset - window.pageYOffset) < 1;
                const scrolledToBottom = Math.abs(document.body.getBoundingClientRect().height - window.pageYOffset - window.innerHeight) < 1;
                if (scrolledToElement || (this.arrowDirection === "Down" && scrolledToBottom)) {
                    window.removeEventListener('scroll', onScroll);

                    document.documentElement.style.scrollBehavior = "auto";

                    if (callback) {
                        callback();
                    }
                }
            };

            window.addEventListener("scroll", onScroll);
            onScroll();

            document.location.replace(`#${el.id}`);
        },
        scrollExtreme(direction) {
            if (direction === "Down") {
                const postCommentsForm = document.getElementById("post-comments-form");
                const footer = document.getElementById("footer");

                const downTarget = postCommentsForm || footer;
                this.scrollToElement(downTarget);

                this.arrowDirection = "Up";
            } else {
                const topTarget = document.getElementById("app");
                this.scrollToElement(topTarget);

                this.arrowDirection = "Down";
            }
        },
        scrollToComment(direction) {
            let comments = document.querySelectorAll(
                 [
                     // Просто новые комментарии
                     ".comment.comment-is-new",
                     // Новые реплаи к старым комментариям
                     ".comment:not(.comment-is-new) > .comment-replies > .replies > .reply.comment-is-new",
                     // Новые реплаи на втором уровне к старым реплаям старых комментариев
                     ".comment:not(.comment-is-new) > .comment-replies > .replies > .reply:not(.comment-is-new) > .reply-replies > .replies > .reply.comment-is-new",
                     // Новые реплаи без родительского комментария
                     ".post-comments-list > .replies > .reply.comment-is-new",
                     // Новые реплаи на втором уровне к старым реплаям без родительского комментария
                     ".post-comments-list > .replies > .reply:not(.comment-is-new) > .reply.comment-is-new",
                     // Новые реплаи бэтлов
                     ".battle-comments-list .comment-replies > .replies > .reply.comment-is-new",
                     // Новые реплаи на втором уровне бэтлов
                     ".battle-comments-list .comment-replies > .replies > .reply:not(.comment-is-new) > .reply-replies >.replies > .reply.comment-is-new",
                 ].join()
             );

            const bodyTop = this.getBodyTop();

            if (comments.length < 1) {
                // Новых нет, ищем начало блока комментариев и перебираем прочтённые комментарии
                comments = document.querySelectorAll("#post-comments-title, .comment");
            }

            if (comments.length < 1) {
                // Then post without comments
                return this.scrollExtreme(direction);
            }

            const position = window.scrollY + this.getElementMargin(comments[0]);

            // Убираем комментарии ниже или выше направления поиска
            const filteredComments = [...comments].filter((el) => {
                const elTop = el.getBoundingClientRect().top;
                const elTopMargin = this.getElementMargin(el);

                return (direction === "Down") ? elTop - elTopMargin > 2 : elTop < 0;
            });

            if (filteredComments.length < 1) {
                return this.scrollExtreme(direction);
            }

            // Находим ближайший комментарий
            const nearest = [...filteredComments].reduce((a, b) => {
                const atop = a.getBoundingClientRect().top - bodyTop;
                const btop = b.getBoundingClientRect().top - bodyTop;
                return Math.abs(btop - position) < Math.abs(atop - position) ? b : a;
            });

            /**
             * remove selected class from previous selected comment
             * do not delete immediately comment-scroll-selected class for override the target comment style
             */
            const alreadySelected = document.querySelector(".comment-scroll-selected");
            if (alreadySelected) {
                alreadySelected.classList.remove("comment-scroll-selected");
            }
            nearest.classList.add("comment-scroll-selected");

            const highlightComment = () => {
                nearest.classList.add("comment-scroll-animation");

                window.setTimeout(() => {
                     nearest.classList.remove("comment-scroll-animation");
                }, 500);
            };

            this.scrollToElement(nearest, highlightComment);
        },
        onArrowClickHandler() {
            if (event.shiftKey) {
                const direction = this.arrowDirection == "Up" ? "Down" : "Up";
                this.scrollToComment(direction);
            } else if (this.arrowDirection == "Up") {
                this.scrollExtreme(this.arrowDirection);
            } else {
                this.scrollToComment(this.arrowDirection);
            }
        },
        initOnPageScroll() {
            this.onPageScrollHandler = throttle(() => {
                const bottomOfWindow = Math.abs(document.body.getBoundingClientRect().height - window.pageYOffset - window.innerHeight) < 1;
                const topOfWindow = window.pageYOffset === 0;

                if (bottomOfWindow) {
                    this.arrowDirection = "Up";
                }

                if (topOfWindow) {
                    this.arrowDirection = "Down";
                }
            }, this.scrollThrottleDelay);

            window.addEventListener("scroll", this.onPageScrollHandler);
        },
        initOnKeyUp() {
             this.keyUpHandler = (e) => {
                // ctrl-up/down для всех, а в macos и FF - ⇧⌃↑/↓
                const isFirefox = ("netscape" in window) && / rv:/.test(navigator.userAgent);
                if (!e.ctrlKey || (isFirefox && !e.shiftKey)
                    || ["ArrowDown", "ArrowUp", "Down", "Up"].indexOf(e.key) < 0) {
                    return;
                }

                e.preventDefault();
                this.arrowDirection = e.key.replace(/^Arrow/, "");
                this.scrollToComment(this.arrowDirection);
            };

            document.addEventListener("keyup", this.keyUpHandler);
        },
        initSelectedClassCleanerListener() {
            document.querySelector('#comments').addEventListener("click", (event) => {
                if (event.target.classList.contains("comment-header-date")) {
                    const selectedComment = event.target.closest(".comment-scroll-selected");
                    if (selectedComment) {
                        selectedComment.classList.remove("comment-scroll-selected");
                    }
                }
            }, false);
        },
        init() {
            this.initOnKeyUp();
            this.initOnPageScroll();
            this.initSelectedClassCleanerListener();
        }
    },
    mounted() {
        this.init();
    },
    beforeDestroy() {
        document.removeEventListener("keyup", this.keyUpHandler);
        window.removeEventListener("scroll", this.onPageScrollHandler);
    },
};
</script>
