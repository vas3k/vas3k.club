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
            return parseInt(style.marginTop, 10);
        },
        scrollToElement(el, callback) {
            const offset = el.getBoundingClientRect().top - this.getBodyTop() - this.getElementMargin(el);
            const onScroll = () => {
                if (Math.abs(offset - window.pageYOffset) < 1) {
                    window.removeEventListener('scroll', onScroll);
                    if (callback) {
                        callback();
                    }
                }
            };
            window.addEventListener('scroll', onScroll);
            onScroll();
            if (el.id.length < 1) {
                window.scrollTo({
                    top: offset,
                    behavior: 'smooth'
                });
            } else {
                location.replace("#" + el.id);
            }
        },
        scrollExtreme(direction) {
            if (direction === "Down") {
                this.arrowDirection = "Up";
                const downTarget = document.querySelector(".post-comments-form");
                this.scrollToElement(downTarget);
            } else {
                this.arrowDirection = "Down";
                const upTarget = document.querySelector(".content");
                this.scrollToElement(upTarget);
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
                ].join()
            );
            const bodyTop = this.getBodyTop();

            if (comments.length < 1) {
                // Новых нет, перебираем прочтённые комментарии
                comments = document.querySelectorAll(".comment");
            }

            if (comments.length < 1) {
                // Без комментариев
                return this.scrollExtreme(direction);
            }

            const position = window.scrollY + this.getElementMargin(comments[0]);

            // Убираем комментарии ниже или выше направления поиска
            const filteredComments = [...comments].filter((el) => {
                const elBCR = el.getBoundingClientRect();
                const eltop = elBCR.top - bodyTop;
                return (direction === "Down") ?
                    eltop - elBCR.height / 2 > position
                    : eltop + elBCR.height / 2 < position;
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

            const highlightComment = () => {
                nearest.classList.add("comment-scroll-selected");
                window.setTimeout(() => {
                    nearest.classList.remove("comment-scroll-selected");
                }, 500);
            };

            this.scrollToElement(nearest, highlightComment);
        },
        onArrowClickHandler() {
            if (this.arrowDirection == "Up") {
                this.scrollExtreme(this.arrowDirection);
            } else {
                this.scrollToComment(this.arrowDirection);
            }
        },
        initOnPageScroll() {
            this.onPageScrollHandler = throttle(() => {
                const scrollPosition = Math.max(
                    window.pageYOffset,
                    document.documentElement.scrollTop,
                    document.body.scrollTop
                );
                const bottomOfWindow = scrollPosition + window.innerHeight === document.documentElement.offsetHeight;
                const topOfWindow = scrollPosition === 0;

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
                // ctrl-up/down для всех, а в macos - ⇧⌃↑/↓
                if (!e.ctrlKey || ["ArrowDown", "ArrowUp", "Down", "Up"].indexOf(e.key) < 0) {
                    return;
                }

                e.preventDefault();
                this.arrowDirection = e.key.replace(/^Arrow/, "");
                this.scrollToComment(this.arrowDirection);
            };
            document.addEventListener("keyup", this.keyUpHandler);
        },
        init() {
            this.initOnKeyUp();
            this.initOnPageScroll();
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
