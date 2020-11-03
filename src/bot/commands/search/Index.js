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

            const output = await this.bot.sock.sendAndWait(id, `process$${id}$${filePath}`);
            if (!output) {
                return msg.channel.createMessage("Timed out");
            }

            const status = parseInt(output[2]);
            if (!status) {
                fs.unlinkSync(filePath);
                return msg.channel.createMessage(`Indexing failed: ${messages[output[3]]}`);
            }

            await msg.channel.createMessage(`Created ${output[1]}`);

            await this.bot.sock.sendAndWait(id, `index$${id}$${filePath}`);
        });
    }
}