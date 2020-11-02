const elasticsearch = require("@elastic/elasticsearch");

module.exports = class ElasticWrapper extends elasticsearch.Client {
    constructor(opts) {
        super(opts);
    }

    searchFromString(hit) {
        return this.searchFromArray(hit).join("-");
    }

    searchFromArray(hit) {
        return [new Date(hit.timestamp).getTime(), hit.id];
    }

    searchAfterHit(reverse, hit, size=24) {
        return this.searchAfter(reverse, this.searchFromArray(hit), size);
    }

    // search the anime index for all documents
    // after `search_after` ([timestamp, id])
    // only get `size` documents
    // `reverse: true` will effectively "search_before"
    searchAfter(reverse, search_after, size=24) {
        const opts = {
            index: "anime",
            body: {
                size,
                query: {
                    match_all: {}
                },
                sort: [
                    { timestamp: reverse ? "asc" : "desc" },
                    { id: reverse ? "desc" : "asc" }
                ]
            }
        };
    
        if (search_after) {
            opts.body.search_after = search_after;
        }

        return this.search(opts)
            .then(res => res.body.hits.hits)
            .then(hits => hits.map(h => h._source))
            .then(hits => reverse ? hits.reverse() : hits);
    }
}