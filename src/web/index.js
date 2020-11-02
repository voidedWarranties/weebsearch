const express = require("express");
const path = require("path");
const Counter = require("../js_common/counter");
const ElasticWrapper = require("./esUtils");
const { IpcSocket, randomString } = require("../js_common/utils");
const fileUpload = require("express-fileupload");
const fs = require("fs");
const FileType = require("file-type");
const { imgWizMiddleWare } = require("express-imgwiz");
const https = require("https");

const es = new ElasticWrapper({ node: "http://localhost:9200" });
const sock = new IpcSocket();

const app = express();
const counter = new Counter();

function modified(dir, file) {
    return fs.statSync(path.join(dir, file)).mtime;
}

function purgeFiles() {
    const dir = "queries";
    const files = fs.readdirSync(dir);
    const filesSorted = files.filter(f => !f.startsWith(".") && (Date.now() - modified(dir, f)) / 1000 / 60 / 60 >= 12);

    for (const file of filesSorted) {
        fs.unlinkSync(path.join(dir, file));
    }
}

app.set("view engine", "pug");
app.set("views", path.join(__dirname, "views"));
app.use(fileUpload({
    limits: { fileSize: 50 * 1024 * 1024 }
}));

app.use("/", express.static(path.join(__dirname, "static")));
app.use("/library", imgWizMiddleWare({
    staticDir: "library",
    cacheDir: "cache"
}));

app.get("/", (req, res) => {
    es.count({ index: "anime" }).then(r => {
        res.render("index", { count: r.body.count });
    });
});

app.post("/search-image", async (req, res) => {
    if (!req.files || !req.files.query) return res.status(400);
    const file = req.files.query;

    const id = randomString();
    const { mime, ext } = await FileType.fromBuffer(file.data);

    if (!ext) return res.status(500);
    if (!mime.startsWith("image/")) return res.status(400);

    const fileName = `${id}.${ext}`;

    fs.writeFileSync(path.join("queries", fileName), file.data);

    purgeFiles();

    res.redirect(`/search-results?file=${fileName}`);
});

function resultUrl(file, page) {
    return `/search-results?file=${file}&page=${page}`;
}

function processHits(hits) {
    for (const result of hits) {
        result.path = "/" + result.path.replace(/\\/g, "/");
    }
}

const pageLength = 24;

app.get("/search-results", (req, res) => {
    es.count({ index: "anime" }).then(async r => {
        var { file, page } = req.query;
        page = page ? parseInt(page) : 0;

        const id = randomString();

        const fileAllowed = fs.readdirSync("queries").includes(file);
        if (!fileAllowed) return res.status(403);

        const data = fs.readFileSync(path.join("queries", file));
        const { mime } = await FileType.fromBuffer(data);
        const b64 = data.toString("base64");
        const output = await sock.sendAndWait(id, `search$${id}$${b64}$0$${page || 0}`);

        if (!output) return res.status(500);

        if (output[1] == "failed") return res.status(204);

        const outObj = JSON.parse(output[1]);

        processHits(outObj.results);

        const startRank = (page || 0) * pageLength + 1;

        const maxPage = Math.ceil(r.body.count / pageLength) - 1;

        res.render("results", {
            results: outObj,
            query: `data:${mime};base64,${b64}`,
            file,
            maxPage,
            resultUrl,
            page,
            startRank
        });
    });
});

app.get("/browse", (req, res) => {
    const { after, before } = req.query;

    const after_raw = after || before;
    const search_after = after_raw ? after_raw.split("-") : null;
    if (search_after) search_after[0] = parseInt(search_after[0]);

    const reverse = before ? true : false;

    es.searchAfter(reverse, search_after).then(async hits => {
        processHits(hits);
        
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

app.get("/counter/:number", (req, res) => {
    res.contentType("image/svg+xml");
    res.end(counter.getSVG(req.params.number));
});

(async function () {
    https.createServer({
        key: fs.readFileSync("certs/privkey.pem"),
        cert: fs.readFileSync("certs/fullchain.pem")
    }, app).listen(8443, () => {
        console.log("Listening");
    });

    app.listen(8080);

    await counter.init();
})();