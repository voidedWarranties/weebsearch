const { Command } = require("karasu");
const config = require("../../../config.json");
const { randomString, downloadImage } = require("../../../js_common/utils");
const fs = require("fs");

const messages = {
    invalid: "Check image format",
    dupe_path: "Image with path already exists",
    questionable: "Image rated questionable or explicit"
};

module.exports = class IndexCommand extends Command {
    constructor(bot) {
        super(bot, "index", {
            category: "search"
        });
    }

    run(msg, args) {
        if (!config.curators.includes(msg.author.id)) return "No permissions";

        const attachments = msg.attachments;

        const url = attachments.length ? attachments[0].url : args[0];

        if (!url) return "No image specified";

        const id = randomString();

        downloadImage(url, `library/${id}`).then(async filePath => {
            if (!filePath) return;

            this.bot.sock.index(id, filePath).then(output => {
                msg.channel.createMessage(`Created ${output.file}`);
            }).catch(err => {
                if (!err) {
                    msg.channel.createMessage("Timed out");
                } else {
                    msg.channel.createMessage(`Indexing failed: ${messages[err]}`);
                }
            });
        });
    }
}
