import { endpointFrontries } from "./static/protocol.mjs";
import * as mariadb from "mariadb";
import * as fs from "node:fs";
import e from "express";

const s_secrets = JSON.parse(fs.readFileSync("../secrets.json") ?? "");
const s_pathPhotos = "../photos/";
const s_db = mariadb.createPool({
	password: s_secrets["dbPass"],
	host: s_secrets["dbHost"],
	user: s_secrets["dbUser"],
	database: "quickpark",
	bigIntAsNumber: true,
	connectionLimit: 5,
});
const s_pathStatic = "./static/";
const s_port = 8080;
const s_app = e();

s_app.use(e.static(s_pathPhotos));
s_app.use(e.static(s_pathStatic));

s_app.get("/frontries", async (p_request, p_response) => {

	const offset = Number(p_request.query["offset"]) || 0;
	// const slice = entries.slice(offset, offset + 5);
	const db = await s_db.getConnection();

	try {

		const rows = await db.execute(
			"SELECT tstamp, plate FROM entries WHERE plate IS NOT NULL ORDER BY tstamp DESC LIMIT 5 OFFSET ?;",
			[offset]
		);

		const res = [];

		for (let i = 0; i < rows.length; ++i) {

			const plate = rows[i]["plate"];
			const tstamp = rows[i]["tstamp"];

			res.push({

				plate: plate,
				tstamp: tstamp,
				image: fs.readFileSync(`../photos/${tstamp}.jpg`),

			});

		};

		p_response.json(res);

		// p_response.json({

		// 	epoch: tstamp,
		// 	number: plate,
		// 	image: fs.readFileSync(`../py/photos/${tstamp}.jpg`),

		// });
		return;

	} catch (e) {

		p_response.status(500).json(endpointFrontries[500].db);
		console.error(`DB Error!: ${e}`);
		return;

	} finally {

		db.release();

	}

});

s_app.listen(s_port, () => {

	console.log(`Quickpark is on [ http://localhost:${s_port} ]!`)

});
