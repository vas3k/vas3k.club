const ClubApi = {
    ajaxify(href, callback) {
        const params = {
            method: "POST",
            credentials: "include",
        };

        fetch(href + "?is_ajax=true", params)
            .then((response) => response.json())
            .then((data) => callback(data));
    },
};

export default ClubApi;
