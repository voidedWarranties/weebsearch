const Router = require("router");
const path = require("path");
const fs = require("fs");
const { randomString } = require("../../js_common/utils");
const FileType = require("file-type");

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

function resultUrl(file, page) {
    return `/search-results?file=${file}&page=${page}`;
}

module.exports = class SearchRouter extends Router {
    constructor(es, sock, pageLength) {
        super();

        this.es = es;
        this.sock = sock;
        this.pageLength = pageLength;

        this.post("/search-image", this.handleSearch.bind(this));
        this.get("/search-results", this.handleResults.bind(this));
    }

    async handleSearch(req, res) {
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
    }

    async handleResults(req, res) {
        this.es.count({ index: "anime" }).then(async r => {
            var { file, page } = req.query;
            page = page ? parseInt(page) : 0;

            const id = randomString();

            const fileAllowed = fs.readdirSync("queries").includes(file);
            if (!fileAllowed) return res.status(403);

            const data = fs.readFileSync(path.join("queries", file));
            const { mime } = await FileType.fromBuffer(data);
            const b64 = data.toString("base64");

            this.sock.search(id, b64, page || 0).then(output => {
                if (!output.success) return res.status(204);

                const outObj = output.data;

                const startRank = (page || 0) * this.pageLength + 1;

                const maxPage = Math.ceil(r.body.count / this.pageLength) - 1;

                res.render("results", {
                    results: outObj,
                    query: `data:${mime};base64,${b64}`,
                    file,
                    maxPage,
                    resultUrl,
                    page,
                    startRank
                });
            }).catch(err => {
                if (!err) {
                    res.status(500);
                }
            });
        });
    }
}
