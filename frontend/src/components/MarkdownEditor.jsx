import { useEffect, useEffectEvent, useRef, useState } from "react";
import ClubApi from "../lib/api.service";
import { createMarkdownEditor, handleFormSubmissionShortcuts, imageUploadOptions } from "../lib/markdown-editor";
import { isMobile } from "../lib/utils";
import { initSettings, isFileAllowed, uploadFile } from "../vendor/inline-attachment";
import "../../static/css/components/markdown-editor.css";

export default function MarkdownEditor({ value = "", focused = false, onChange, className = "" }) {
    const textarea = useRef(null);
    const notifyChange = useEffectEvent((text) => onChange?.(text));
    const [suggestions, setSuggestions] = useState({ users: [], index: 0, top: 0, left: 0 });
    const suggest = useRef(null);
    const insertSuggestion = useRef(null);

    useEffect(() => {
        const input = textarea.current;
        const form = input.form;
        const fileInput = form?.querySelector('input[type="file"][name="attach-image"]');
        let disposed = false;
        let timer;
        let revision = 0;
        let detachUpload;
        let mde;
        const notify = () => notifyChange(input.value);
        const grow = () => {
            input.style.height = "auto";
            input.style.height = `${input.scrollHeight}px`;
        };
        const settings = initSettings(imageUploadOptions);
        if (fileInput) fileInput.accept = settings.allowedTypes.join();

        const upload = (event) => {
            for (const file of event.target.files) {
                if (!isFileAllowed(file, settings)) continue;
                input.value += `${input.value ? " " : ""}${settings.progressText}`;
                notify();
                grow();
                const complete = (replacement) => {
                    if (disposed) return;
                    input.value = input.value.includes(settings.progressText)
                        ? input.value.replace(settings.progressText, replacement)
                        : `${input.value} ${replacement}`;
                    notify();
                    grow();
                    input.focus();
                };
                uploadFile(
                    file,
                    settings,
                    (xhr) => {
                        try {
                            const filename = JSON.parse(xhr.responseText)[settings.jsonFieldName];
                            complete(
                                filename
                                    ? settings.urlText.replace(settings.filenameTag, filename)
                                    : settings.errorText,
                            );
                        } catch {
                            complete(settings.errorText);
                        }
                    },
                    () => complete(settings.errorText),
                );
            }
            event.target.value = "";
        };

        const authors = new Map();
        document.querySelectorAll(".comment-header-author-name[data-author-slug]").forEach((link) => {
            if (link.dataset.authorDeleted === "1") return;
            const slug = link.dataset.authorSlug;
            const avatar = link
                .closest(".reply, .comment")
                ?.querySelector(".reply-avatar img, .comment-side-avatar img")?.src;
            authors.set(slug, { slug, full_name: link.textContent.trim(), avatar });
        });

        insertSuggestion.current = (user) => {
            const current = suggest.current;
            if (!current || !user) return;
            if (mde) mde.codemirror.replaceRange(`${user.slug} `, current.from, current.to);
            else {
                input.setRangeText(`${user.slug} `, current.from, current.to, "end");
                notify();
                grow();
            }
            suggest.current = null;
            setSuggestions({ users: [], index: 0 });
            if (mde) mde.codemirror.focus();
            else input.focus();
        };
        const onEditorChange = () => {
            const cm = mde?.codemirror;
            if (cm) input.value = cm.getValue();
            else grow();
            notify();
            clearTimeout(timer);
            const request = ++revision;
            const cursor = cm ? cm.getCursor() : input.selectionStart;
            const beforeCursor = cm ? cm.getLine(cursor.line).slice(0, cursor.ch) : input.value.slice(0, cursor);
            const match = beforeCursor.match(/(?:^|\s)@([^\s@]*)$/);
            if (!match) {
                suggest.current = null;
                setSuggestions({ users: [], index: 0 });
                return;
            }
            const sample = match[1];
            const coords = cm ? cm.cursorCoords(cursor, "window") : input.getBoundingClientRect();
            suggest.current = {
                from: cm ? { line: cursor.line, ch: cursor.ch - sample.length } : cursor - sample.length,
                to: cursor,
            };
            const show = (users) => {
                if (!disposed && request === revision)
                    setSuggestions({
                        users,
                        index: 0,
                        top: Math.max(12, Math.min(coords.bottom, (window.visualViewport?.height || innerHeight) - 160)),
                        left: Math.max(12, Math.min(coords.left, innerWidth - 280)),
                    });
            };
            if (sample.length < 3) {
                show(
                    [...authors.values()]
                        .filter((user) => user.slug.includes(sample))
                        .sort((a, b) => a.full_name.localeCompare(b.full_name)),
                );
            } else {
                show([]);
                timer = setTimeout(async () => {
                    try {
                        const data = await ClubApi.get(`/search/users.json?q=${encodeURIComponent(sample)}`);
                        show(data.users || []);
                    } catch {
                        show([]);
                    }
                }, 500);
            }
        };
        if (isMobile()) {
            input.addEventListener("input", onEditorChange);
            fileInput?.addEventListener("change", upload);
            grow();
            if (focused) {
                input.focus();
                input.setSelectionRange(input.value.length, input.value.length);
            }
        } else {
            mde = createMarkdownEditor(input, { toolbar: false });
            detachUpload = window.inlineAttachment.editors.codemirror4.attach(mde.codemirror, {
                ...imageUploadOptions,
                fileInputEl: fileInput,
            });
            mde.codemirror.on("change", onEditorChange);
            if (focused) {
                mde.codemirror.focus();
                mde.codemirror.execCommand("goDocEnd");
            }
        }
        form?.addEventListener("keydown", handleFormSubmissionShortcuts);
        return () => {
            disposed = true;
            clearTimeout(timer);
            revision++;
            form?.removeEventListener("keydown", handleFormSubmissionShortcuts);
            fileInput?.removeEventListener("change", upload);
            input.removeEventListener("input", onEditorChange);
            detachUpload?.();
            mde?.toTextArea();
        };
    }, []);

    return (
        <div
            className={className}
            onBlurCapture={(event) => {
                if (!event.currentTarget.contains(event.relatedTarget)) setSuggestions({ users: [], index: 0 });
            }}
            onKeyDownCapture={(event) => {
                if (!suggestions.users.length || event.ctrlKey || event.metaKey || event.nativeEvent.isComposing)
                    return;
                if (!["ArrowDown", "ArrowUp", "Enter", "Tab", "Escape"].includes(event.key)) return;
                event.preventDefault();
                event.stopPropagation();
                if (event.key === "Enter" || event.key === "Tab") {
                    insertSuggestion.current(suggestions.users[suggestions.index]);
                } else if (event.key === "Escape") {
                    setSuggestions({ users: [], index: 0 });
                } else {
                    setSuggestions((current) => ({
                        ...current,
                        index: Math.max(
                            0,
                            Math.min(current.users.length - 1, current.index + (event.key === "ArrowDown" ? 1 : -1)),
                        ),
                    }));
                }
            }}
        >
            <div className="comment-markdown-editor">
                <textarea
                    ref={textarea}
                    name="text"
                    required
                    maxLength={20000}
                    placeholder="Напишите ответ..."
                    defaultValue={value}
                />
            </div>
            {suggestions.users.length > 0 && (
                <div
                    className="mention-autocomplete-hint"
                    style={{ position: "fixed", zIndex: 1000, top: suggestions.top, left: suggestions.left }}
                >
                    {suggestions.users.map((user, index) => (
                        <div
                            key={user.slug}
                            className={`mention-autocomplete-hint__option ${
                                index === suggestions.index ? "mention-autocomplete-hint__option--suggested" : ""
                            }`}
                            onPointerDown={(event) => event.preventDefault()}
                            onClick={() => insertSuggestion.current(user)}
                        >
                            <div className="mention-autocomplete-hint__option-row">
                                <img
                                    className="mention-autocomplete-hint__option-avatar"
                                    src={user.avatar || "https://i.vas3k.club/v.png"}
                                    alt=""
                                    width="22"
                                    height="22"
                                />
                                <span className="mention-autocomplete-hint__option-name">{user.full_name}</span>
                            </div>
                        </div>
                    ))}
                </div>
            )}
        </div>
    );
}
