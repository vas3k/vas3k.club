const ClubApi = {
    post(href, callback) {
        const params = {
            method: "POST",
            credentials: "include",
        };

        fetch(href + "?is_ajax=true", params)
            .then((response) => {
                if (!response.ok) {
                    throw new Error(`HTTP error! status: ${response.status}`);
                }
                return response.json();
            })
            .then((data) => callback(data))
            .catch((error) => {
                callback({ error: error.message });
            });
    },

    postForm(href, data, callback) {
        const params = {
            method: "POST",
            credentials: "include",
            headers: { "Content-Type": "application/x-www-form-urlencoded; charset=UTF-8" },
            body: new URLSearchParams(data).toString(),
        };

        fetch(href + "?is_ajax=true", params)
            .then((response) => response.json().then((json) => ({ ok: response.ok, json })))
            .then(({ ok, json }) => {
                if (ok) {
                    callback(json);
                    return;
                }
                // club api errors come back as {"error": {"title": ..., "message": ...}}
                const error = json.error || {};
                callback({ error: error.message || error.title || "Что-то пошло не так" });
            })
            .catch((error) => {
                callback({ error: error.message });
            });
    },

    get(href, callback) {
        const params = {
            method: "GET",
            credentials: "include",
        };

        fetch(href + "?is_ajax=true", params)
            .then((response) => {
                if (!response.ok) {
                    throw new Error(`HTTP error! status: ${response.status}`);
                }
                return response.json();
            })
            .then((data) => callback(data))
            .catch((error) => {
                callback({ error: error.message });
            });
    },
};

export default ClubApi;
