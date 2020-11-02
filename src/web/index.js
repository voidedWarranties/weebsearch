const express = require("express");
const path = require("path");
const Counter = require("../js_common/counter");
const ElasticWrapper = require("./esUtils");
const { IpcSocket } = require("../js_common/utils");
const fileUpload = require("express-fileupload");
const fs = require("fs");
const { imgWizMiddleWare } = require("express-imgwiz");
const https = require("https");

const SearchRouter = require("./routes/search");
const BrowseRouter = require("./routes/browse");

const es = new ElasticWrapper({ node: "http://localhost:9200" });
const sock = new IpcSocket();

const app = express();
const counter = new Counter();
const pageLength = 24;

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

app.use("/", new SearchRouter(es, sock, pageLength));
app.use("/", new BrowseRouter(es, pageLength));

app.get("/", (req, res) => {
    es.count({ index: "anime" }).then(r => {
        res.render("index", { count: r.body.count });
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