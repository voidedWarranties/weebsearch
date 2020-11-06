const crypto = require("crypto");
const FileType = require("file-type");
const axios = require("axios");
const fs = require("fs");
const glob = require("glob");
const zmq = require("zeromq");
const { EventEmitter } = require("events");

function randomString() {
    return Math.abs(crypto.randomBytes(5).readInt32LE()).toString(36);
}

function downloadImage(url, filePath) {
    return axios({
        method: "get",
        url,
        responseType: "arraybuffer"
    }).then(async res => {
        const { ext } = await FileType.fromBuffer(res.data);
        const fileLoc = `${filePath}.${ext}`;

        if (glob.sync(`${filePath}.*`).length) return null;

        fs.writeFileSync(fileLoc, res.data);

        return fileLoc;
    });
}

function imageB64(url) {
    return axios({
        method: "get",
        url,
        responseType: "arraybuffer"
    }).then(async res => {
        const { mime } = await FileType.fromBuffer(res.data);
        if (!mime.startsWith("image/")) return null;

        return res.data.toString("base64");
    });
}

class IpcSocket extends EventEmitter {
    constructor() {
        super();

        this.socket = new zmq.Dealer({
            reconnectInterval: 1000
        });

        this.socket.connect("tcp://127.0.0.1:6969");

        this.loop();
    }

    index(id, filePath) {
        return new Promise(async (resolve, reject) => {
            const output = await this.sendAndWait("process", id, {
                file: filePath
            });

            if (!output) {
                reject(null);
            }

            if (!output.success) {
                fs.unlinkSync(filePath);
                reject(output.msg);
            }

            const output2 = await this.sendAndWait("index", id, {
                file: filePath
            });

            resolve(output);
        });
    }

    search(id, file, page = 0, plot = false) {
        return new Promise(async (resolve, reject) => {
            const output = await this.sendAndWait("search", id, {
                file, page, plot
            });

            if (!output) {
                reject(null);
            } else {
                resolve(output);
            }
        });
    }

    delete(id, doc_id) {
        return new Promise(async (resolve, reject) => {
              const output = await this.sendAndWait("delete", id, {
                  id_: doc_id
              });

              if (!output) {
                  reject(null);
              } else {
                  resolve(output);
              }
        });
    }

    sendAndWait(cmd, id, msg) {
        return new Promise(async resolve => {
            msg.cmd = cmd;
            msg.id = id;
            await this.send(JSON.stringify(msg));

            const handler = async res => {
                res = JSON.parse(res);
                if (res.id === id) {
                    this.off("message", handler);
                    resolve(res);
                }
            }

            setTimeout(() => {
                this.off("message", handler);
                resolve(null);
            }, 15000);

            this.on("message", handler);
        });
    }

    async loop() {
        for await (const [msg] of this.socket) {
            this.emit("message", msg.toString());
        }
    }

    send(msg) {
        return this.socket.send(msg);
    }
}

module.exports = { randomString, downloadImage, imageB64, IpcSocket };
