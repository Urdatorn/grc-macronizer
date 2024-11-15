local m = {}

m["ira-mid"] = {
	"Middle Iranian",
	6841465,
	"ira",
	family = "ira",
}

m["ira-old"] = {
	"Old Iranian",
	23301845,
	"ira",
	family = "ira",
	wikipedia_article = "Old Iranian languages",
}

m = require("Module:languages").addDefaultTypes(m, false, "family")
return require("Module:languages").finalizeEtymologyData(m)