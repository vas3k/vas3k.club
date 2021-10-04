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
            const oldHash = document.location.hash;
            const newHash = `#${el.id}`;
            if (oldHash === newHash) {
                // zero the hash so that there is no sticking if we are already on this element
                document.location.hash = '';
            }

            document.documentElement.style.scrollBehavior = "smooth";

            const offset = el.getBoundingClientRect().top - this.getBodyTop() - this.getElementMargin(el);

            const onScroll = () => {
                if (Math.abs(offset - window.pageYOffset) < 1) {
                    window.removeEventListener('scroll', onScroll);

                    document.documentElement.style.scrollBehavior = "auto";

                    if (callback) {
                        callback();
                    }
                }
            };

            window.addEventListener('scroll', onScroll);
            onScroll();

            document.location.hash = `#${el.id}`;
        },
        scrollExtreme(direction) {
            // zero the hash so that there is no sticking if we are already on this element
            document.location.hash = '';

            if (direction === "Down") {
                this.arrowDirection = "Up";

                const postCommentsForm = document.getElementById("post-comments-form");
                const footer = document.getElementById("footer");

                const downTarget = postCommentsForm || footer;
                this.scrollToElement(downTarget);
            } else {
                this.arrowDirection = "Down";

                window.scrollTo({
                    top: 0,
                    behavior: 'smooth'
                });
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
                // take comments header
                const commentBlock = document.getElementById("comments");
                const commentBlockArray = commentBlock ? [commentBlock] : [];

                // Новых нет, перебираем прочтённые комментарии
                const oldComments = document.querySelectorAll(".comment");

                comments = oldComments.length > 0 ? [...commentBlockArray, ...document.querySelectorAll(".comment")] : [];
            }

            if (comments.length < 1) {
                // Then post without comments
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
