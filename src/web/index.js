const express = require("express");
const path = require("path");
const Counter = require("../js_common/counter");
const ElasticWrapper = require("./esUtils");
const { IpcSocket } = require("../js_common/utils");
const fileUpload = require("express-fileupload");
const fs = require("fs");
const { imgWizMiddleWare } = require("express-imgwiz");
const https = require("https");
const bodyParser = require("body-parser");

const mongooseConnection = require("./db/driver");
const passport = require("./passport");
const session = require("express-session");
const MongoStore = require("connect-mongo")(session);

const SearchRouter = require("./routes/search");
const BrowseRouter = require("./routes/browse");

const es = new ElasticWrapper({ node: "http://localhost:9200" });
const sock = new IpcSocket();

const app = express();
const counter = new Counter();
const pageLength = 24;

function checkAuth(req, res, next) {
    if (req.user) {
        next();
    } else {
        res.redirect("/login");
    }
}

app.set("view engine", "pug");
app.set("views", path.join(__dirname, "views"));
app.use(fileUpload({
    limits: { fileSize: 50 * 1024 * 1024 }
}));
app.use(bodyParser.urlencoded({ extended: true }));

app.use(session({
    secret: "zonoiwneidnfijionorigjoixdnoiagj",
    store: new MongoStore({ mongooseConnection }),
    resave: false,
    saveUninitialized: false
}));

app.use(passport.initialize());
app.use(passport.session());

app.use("/", express.static(path.join(__dirname, "static")));
app.use("/library", imgWizMiddleWare({
    staticDir: "library",
    cacheDir: "cache"
}));

app.use("/", new SearchRouter(es, sock, pageLength));
app.use("/", new BrowseRouter(es, pageLength));

app.post("/register",
    passport.authenticate("local-signup"),
    (req, res) => {
        res.redirect("/login");
    });

app.post("/login",
    passport.authenticate("local-login"),
    (req, res) => {
        res.redirect("/");
    });

app.get("/register", (req, res) => {
    res.render("register");
});

app.get("/login", (req, res) => {
    res.render("login");
});

app.get("/logout", checkAuth, (req, res) => {
    req.logout();
    res.redirect("/");
});

app.get("/", (req, res) => {
    es.count({ index: "anime" }).then(r => {
        res.render("index", { count: r.body.count, user: req.user });
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
