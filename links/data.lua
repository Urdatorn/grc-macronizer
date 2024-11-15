local u = require("Module:string utilities").char

local data = {}

data.phonetic_extraction = {
	["th"] = "th/th.lua",
	["km"] = "km/km.lua",
}

data.ignored_prefixes = {
	["cat"] = true,
	["category"] = true,
	["file"] = true,
	["image"] = true
}

data.pos_tags = {
	["a"] = "adjective",
	["adv"] = "adverb",
	["int"] = "interjection",
	["n"] = "noun",
	["pron"] = "pronoun",
	["v"] = "verb",
	["vi"] = "intransitive verb",
	["vt"] = "transitive verb",
	["vti"] = "transitive and intransitive verb",
}

-- Scheme for using unsupported characters in titles.
data.unsupported_characters = {
	["#"] = "`num`",
	["%"] = "`percnt`", -- only escaped in percent encoding
	["&"] = "`amp`", -- only escaped in HTML entities
	["."] = "`period`", -- only escaped in dot-slash notation
	["<"] = "`lt`",
	[">"] = "`gt`",
	["["] = "`lsqb`",
	["]"] = "`rsqb`",
	["_"] = "`lowbar`",
	["`"] = "`grave`", -- used to enclose unsupported characters in the scheme, so a raw use in an unsupported title must be escaped to prevent interference
	["{"] = "`lcub`",
	["|"] = "`vert`",
	["}"] = "`rcub`",
	["~"] = "`tilde`", -- only escaped when 3 or more are consecutive
	["\239\191\189"] = "`repl`" -- replacement character U+FFFD, which can't be typed directly here due to an abuse filter
}

-- Manually specified unsupported titles. Only put titles here if there is a different reason why they are unsupported, and not just because they contain one of the unsupported characters above.
data.unsupported_titles = {
	[" "] = "Space",
	["&amp;"] = "`amp`amp;",
	["λοπαδοτεμαχοσελαχογαλεοκρανιολειψανοδριμυποτριμματοσιλφιοκαραβομελιτοκατακεχυμενοκιχλεπικοσσυφοφαττοπεριστεραλεκτρυονοπτοκεφαλλιοκιγκλοπελειολαγῳοσιραιοβαφητραγανοπτερύγων"] = "Ancient Greek dish",
	["กรุงเทพมหานคร อมรรัตนโกสินทร์ มหินทรายุธยา มหาดิลกภพ นพรัตนราชธานีบูรีรมย์ อุดมราชนิเวศน์มหาสถาน อมรพิมานอวตารสถิต สักกะทัตติยวิษณุกรรมประสิทธิ์"] = "Thai name of Bangkok",
	[u(0x1680)] = "Ogham space",
	[u(0x3000)] = "Ideographic space"
}

return data