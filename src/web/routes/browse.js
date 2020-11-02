const Router = require("router");

module.exports = class BrowseRouter extends Router {
    constructor(es, pageLength) {
        super();

        this.es = es;
        this.pageLength = pageLength;

        this.get("/browse", this.handleBrowse.bind(this));
    }

    handleBrowse(req, res) {
        const { after, before } = req.query;
    
        const after_raw = after || before;
        const search_after = after_raw ? after_raw.split("-") : null;
        if (search_after) search_after[0] = parseInt(search_after[0]);
    
        const reverse = before ? true : false;
    
        this.es.searchAfter(reverse, search_after).then(async hits => {
            if (hits.length < 1) return res.status(204);
    
            var beforeHit = hits[0];
            var afterHit = hits[hits.length - 1];
    
            const beforeHits = await this.es.searchAfterHit(true, beforeHit);
            if (beforeHits.length < this.pageLength && beforeHits.length > 0) {
                const beforeHits2 = await this.es.searchAfterHit(false, beforeHits[0], this.pageLength - beforeHits.length);
                beforeHit = beforeHits2[beforeHits2.length - 1];
            }
    
            const afterHits = await this.es.searchAfterHit(false, afterHit);
    
            res.render("browse", {
                results: hits,
                prev: beforeHits.length > 0 ? this.es.searchFromString(beforeHit) : null,
                next: afterHits.length > 0 ? this.es.searchFromString(afterHit) : null
            });
        });
    }
}