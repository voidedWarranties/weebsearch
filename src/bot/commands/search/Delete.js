const { Command } = require("karasu");
const { randomString } = require("../../../js_common/utils");

module.exports = class DeleteCommand extends Command {
    constructor(bot) {
        super(bot, "delete", {
            ownerOnly: true,
            category: "search"
        });
    }

    run(msg, args) {
        if (args.length < 1) {
            return "Not enough arguments (expected id)";
        }

        const [doc_id] = args;
        const id = randomString();

        this.bot.sock.delete(id, doc_id).then(output => {
            if (!output.success) {
                msg.channel.createMessage("Deletion failed (check id)");
            } else {
                msg.channel.createMessage(`Deleted ${output.file}`);
            }
        }).catch(err => {
            if (!err) {
                msg.channel.createMessage("Timed out");
            }
        });
    }
}
