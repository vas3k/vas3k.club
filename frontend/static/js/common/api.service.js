const ClubApi = {
    ajaxify(href, callback) {
        const params = {
            method: "POST",
            credentials: "include",
        };
        fetch(href + (href.indexOf("?") > -1 ? "&" : "?") + "is_ajax=true", params)
            .then((response) => {
                return response.json();
            })
            .then((data) => {
                callback(data);
            });
    },
};

export default ClubApi;
