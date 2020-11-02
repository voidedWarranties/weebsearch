const express = require("express");

const router = express.Router();

module.exports = (es, pageLength) => {
    router.get("/browse", (req, res) => {
        const { after, before } = req.query;
    
        const after_raw = after || before;
        const search_after = after_raw ? after_raw.split("-") : null;
        if (search_after) search_after[0] = parseInt(search_after[0]);
    
        const reverse = before ? true : false;
    
        es.searchAfter(reverse, search_after).then(async hits => {
            if (hits.length < 1) return res.status(204);
    
            var beforeHit = hits[0];
            var afterHit = hits[hits.length - 1];
    
            const beforeHits = await es.searchAfterHit(true, beforeHit);
            if (beforeHits.length < pageLength && beforeHits.length > 0) {
                const beforeHits2 = await es.searchAfterHit(false, beforeHits[0], pageLength - beforeHits.length);
                beforeHit = beforeHits2[beforeHits2.length - 1];
            }
    
            const afterHits = await es.searchAfterHit(false, afterHit);
    
            res.render("browse", {
                results: hits,
                prev: beforeHits.length > 0 ? es.searchFromString(beforeHit) : null,
                next: afterHits.length > 0 ? es.searchFromString(afterHit) : null
            });
        });
    });

    return router;
}