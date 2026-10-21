import { useState } from "react";
import SearchSelect from "./SearchSelect";

export default function RoomSelect({ name, id, rooms = [], initialValue = "" }) {
    const options = rooms.map((room) => ({
        value: room.slug,
        label: room.title,
        image: room.image,
    }));
    const [selected, setSelected] = useState(() => options.find((room) => room.value === initialValue) || null);
    const [query, setQuery] = useState("");
    const items = options.filter((room) =>
        `${room.label} ${room.value}`.toLocaleLowerCase().includes(query.trim().toLocaleLowerCase()),
    );

    return (
        <SearchSelect
            className="search-select-room"
            name={name}
            id={id}
            label="Комната"
            placeholder="Найти комнату"
            selected={selected}
            onChange={setSelected}
            items={items}
            query={query}
            onQueryChange={setQuery}
        />
    );
}
