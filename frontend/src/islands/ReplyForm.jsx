import { useEffect, useRef, useState } from "react";
import { createPortal, flushSync } from "react-dom";
import MarkdownEditor from "../components/MarkdownEditor";

export default function ReplyForm({ commentOrder, avatarUrl, username, createCommentUrl }) {
    const [reply, setReply] = useState(null);
    const drafts = useRef({});
    const target = useRef(null);
    const sequence = useRef(0);

    useEffect(() => {
        const container = document.createElement("div");
        container.className = "reply-form-container";
        target.current = container;
        const open = (event) => {
            const button = event.target.closest("[data-reply-to]");
            if (!button) return;
            const comment = document.getElementById(`comment-${button.dataset.replyTo}`);
            if (!comment) return;
            event.preventDefault();
            comment.after(container);
            const draftKey = button.dataset.replyDraft || button.dataset.replyTo;
            flushSync(() =>
                setReply({
                    commentId: button.dataset.replyTo,
                    draftKey,
                    value:
                        drafts.current[draftKey] ??
                        (button.dataset.replyUsername ? `@${button.dataset.replyUsername}, ` : ""),
                    focusKey: ++sequence.current,
                }),
            );
            container.scrollIntoView({ block: "nearest" });
        };
        document.addEventListener("click", open);
        return () => {
            document.removeEventListener("click", open);
            container.remove();
        };
    }, []);

    if (!reply) return null;
    return createPortal(
        <form
            method="post"
            action={createCommentUrl}
            className="form reply-form-form"
            id="comment-reply-form"
            onSubmit={(event) => {
                event.currentTarget.querySelector('button[type="submit"]').disabled = true;
            }}
        >
            <input type="hidden" name="post_comment_order" value={commentOrder} />
            <input type="hidden" name="reply_to_id" value={reply.commentId} />
            <div className="reply-form">
                <div className="reply-form-avatar">
                    <div className="avatar">
                        <img src={avatarUrl} alt={`Аватар ${username}`} loading="lazy" />
                    </div>
                </div>
                <div className="reply-form-body comment-form-editor-container">
                    <MarkdownEditor
                        key={`${reply.draftKey}-${reply.focusKey}`}
                        value={reply.value}
                        focused
                        onChange={(text) => {
                            drafts.current[reply.draftKey] = text;
                        }}
                    />
                    <div className="reply-form-footer">
                        <label className="reply-form-attach-image">
                            <input type="file" name="attach-image" aria-label="Добавить картинку" />
                            <i className="fa fa-image" />
                        </label>
                    </div>
                </div>
                <div className="reply-form-button">
                    <button type="submit" className="button button-small">
                        Отправить
                    </button>
                </div>
            </div>
        </form>,
        target.current,
    );
}
