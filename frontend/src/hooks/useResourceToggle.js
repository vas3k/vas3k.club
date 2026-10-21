import { useRef, useState } from "react";
import ClubApi from "../lib/api.service";

export default function useResourceToggle(url, initialActive, inverted = false) {
    const [active, setActive] = useState(initialActive);
    const [busy, setBusy] = useState(false);
    const [error, setError] = useState("");
    const pending = useRef(false);

    async function toggle() {
        if (pending.current) return;
        pending.current = true;
        setBusy(true);
        setError("");
        try {
            const exists = inverted ? !active : active;
            const data = await ClubApi[exists ? "delete" : "post"](url);
            if (data.status === "created") setActive(!inverted);
            if (data.status === "deleted") setActive(inverted);
        } catch (failure) {
            setError(failure.message);
        } finally {
            pending.current = false;
            setBusy(false);
        }
    }

    return { active, busy, error, toggle };
}
