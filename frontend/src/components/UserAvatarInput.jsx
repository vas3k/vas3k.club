import { useEffect, useState } from "react";

export default function UserAvatarInput({ inputId, currentAvatar }) {
    const [preview, setPreview] = useState(currentAvatar);
    useEffect(() => {
        const input = document.getElementById(inputId);
        let url;
        const change = () => {
            if (url) URL.revokeObjectURL(url);
            url = input.files[0] ? URL.createObjectURL(input.files[0]) : null;
            setPreview(url || currentAvatar);
        };
        input?.addEventListener("change", change);
        return () => {
            input?.removeEventListener("change", change);
            if (url) URL.revokeObjectURL(url);
        };
    }, [inputId, currentAvatar]);
    return (
        <label className="user-avatar-input" htmlFor={inputId}>
            <div
                className="avatar profile-user-avatar"
                style={{ backgroundImage: preview ? `url(${JSON.stringify(preview)})` : undefined }}
            />
        </label>
    );
}
