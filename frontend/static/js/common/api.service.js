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
