const ClubApi = {
    _request(method, href, callback) {
        fetch(href, {
            method,
            credentials: "include",
            headers: { "Accept": "application/json" },
        })
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

    post(href, callback) {
        this._request("POST", href, callback);
    },

    get(href, callback) {
        this._request("GET", href, callback);
    },
};

export default ClubApi;
