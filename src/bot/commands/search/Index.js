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

            const output = await this.bot.sock.sendAndWait(id, { cmd: "process", id, file: filePath });
            if (!output) {
                return msg.channel.createMessage("Timed out");
            }

            if (!output.success) {
                fs.unlinkSync(filePath);
                return msg.channel.createMessage(`Indexing failed: ${messages[output.msg]}`);
            }

            await msg.channel.createMessage(`Created ${output.file}`);

            await this.bot.sock.sendAndWait(id, { cmd: "index", id, file: filePath });
        });
    }
}