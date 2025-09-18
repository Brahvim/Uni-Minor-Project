import express from "express";

const s_port = 8080;
const s_pathFront = ".";
const s_app = express();

s_app.use(express.static(s_pathFront));

s_app.get("/", (p_request, p_response) => {

});

s_app.listen(s_port, (p_error) => {

	if (!p_error) {

		return;

	}

	console.error(p_error);

});
