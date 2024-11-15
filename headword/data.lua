local headword_page_module = "headword/page.lua"

local list_to_set = require("table.lua").listToSet

local data = {}

------ 1. Lists which are converted into sets. ------

-- Zero-plurals (i.e. invariable plurals).
local irregular_plurals = list_to_set({
	"cmavo",
	"cmene",
	"fu'ivla",
	"gismu",
	"Han tu",
	"hanja",
	"hanzi",
	"jyutping",
	"kana",
	"kanji",
	"lujvo",
	"phrasebook",
	"pinyin",
	"rafsi",
}, function(item)
	return item
end)

-- Irregular non-zero plurals AND any regular plurals where the singular ends in "s",
-- because the module assumes that inputs ending in "s" are plurals. The singular and
-- plural both need to be added, as the module will generate a default plural if
-- the input doesn't match a key in this table.
for sg, pl in next, {
	mora = "morae"
} do
	irregular_plurals[sg], irregular_plurals[pl] = pl, pl
end

data.irregular_plurals = irregular_plurals

data.lemmas = list_to_set{
	"abbreviations",
	"acronyms",
	"adjectives",
	"adnominals",
	"adpositions",
	"adverbs",
	"affixes",
	"ambipositions",
	"articles",
	"circumfixes",
	"circumpositions",
	"classifiers",
	"cmavo",
	"cmavo clusters",
	"cmene",
	"combining forms",
	"conjunctions",
	"counters",
	"determiners",
	"diacritical marks",
	"digraphs",
	"equative adjectives",
	"fu'ivla",
	"gismu",
	"Han characters",
	"Han tu",
	"hanja",
	"hanzi",
	"ideophones",
	"idioms",
	"infixes",
	"initialisms",
	"iteration marks",
	"interfixes",
	"interjections",
	"kana",
	"kanji",
	"letters",
	"ligatures",
	"logograms",
	"lujvo",
	"morae",
	"morphemes",
	"non-constituents",
	"nouns",
	"numbers",
	"numeral symbols",
	"numerals",
	"particles",
	"phrases",
	"postpositions",
	"postpositional phrases",
	"predicatives",
	"prefixes",
	"prepositional phrases",
	"prepositions",
	"preverbs",
	"pronominal adverbs",
	"pronouns",
	"proper nouns",
	"proverbs",
	"punctuation marks",
	"relatives",
	"roots",
	"stems",
	"suffixes",
	"syllables",
	"symbols",
	"verbs",
}

data.nonlemmas = list_to_set{
	"active participle forms",
	"active participles",
	"adjectival participles",
    "adjective case forms",
	"adjective forms",
	"adjective feminine forms",
	"adjective plural forms",
	"adverb forms",
	"adverbial participles",
	"agent participles",
	"article forms",
	"circumfix forms",
	"combined forms",
	"comparative adjective forms",
	"comparative adjectives",
	"comparative adverb forms",
	"comparative adverbs",
	"conjunction forms",
	"contractions",
	"converbs",
	"determiner comparative forms",
	"determiner forms",
	"determiner superlative forms",
	"diminutive nouns",
	"elative adjectives",
	"equative adjective forms",
	"equative adjectives",
	"future participles",
	"gerunds",
	"infinitive forms",
	"infinitives",
	"interjection forms",
	"jyutping",
	"misspellings",
	"negative participles",
	"nominal participles",
	"noun case forms",
	"noun dual forms",
	"noun forms",
	"noun paucal forms",
	"noun plural forms",
	"noun possessive forms",
	"noun singulative forms",
	"numeral forms",
	"participles",
	"participle forms",
	"particle forms",
	"passive participles",
	"past active participles",
	"past adverbial participles",
	"past participles",
	"past participle forms",
	"past passive participles",
	"perfect active participles",
	"perfect participles",
	"perfect passive participles",
	"pinyin",
	"plurals",
	"postposition forms",
	"prefix forms",
	"preposition contractions",
	"preposition forms",
	"prepositional pronouns",
	"present active participles",
	"present adverbial participles",
	"present participles",
	"present passive participles",
	"preverb forms",
	"pronoun forms",
	"pronoun possessive forms",
	"proper noun forms",
	"proper noun plural forms",
	"rafsi",
	"romanizations",
	"root forms",
	"singulatives",
	"suffix forms",
	"superlative adjective forms",
	"superlative adjectives",
	"superlative adverb forms",
	"superlative adverbs",
	"verb forms",
	"verbal nouns",
}

-- These langauges will not have links to separate parts of the headword.
data.no_multiword_links = list_to_set{
	"zh",
}

-- These languages will not have "LANG multiword terms" categories added.
data.no_multiword_cat = list_to_set{
	-------- Languages without spaces between words (sometimes spaces between phrases) --------
	"blt", -- Tai Dam
	"ja", -- Japanese
	"khb", -- Lü
	"km", -- Khmer
	"lo", -- Lao
	"mnw", -- Mon
	"my", -- Burmese
	"nan", -- Min Nan (some words in Latin script; hyphens between syllables)
	"nan-hbl", -- Hokkien (some words in Latin script; hyphens between syllables)
	"nod", -- Northern Thai
	"ojp", -- Old Japanese
	"shn", -- Shan
	"sou", -- Southern Thai
	"tdd", -- Tai Nüa
	"th", -- Thai
	"tts", -- Isan
	"twh", -- Tai Dón
	"txg", -- Tangut
	"zh", -- Chinese (all varieties with Chinese characters)
	"zkt", -- Khitan

	-------- Languages with spaces between syllables --------
	"ahk", -- Akha
	"aou", -- A'ou
	"atb", -- Zaiwa
	"byk", -- Biao
	"cdy", -- Chadong
	--"duu", -- Drung; not sure
	--"hmx-pro", -- Proto-Hmong-Mien
	--"hnj", -- Green Hmong; not sure
	"huq", -- Tsat
	"ium", -- Iu Mien
	--"lis", -- Lisu; not sure
	"mtq", -- Muong
	--"mww", -- White Hmong; not sure
	"onb", -- Lingao
	--"sit-gkh", -- Gokhy; not sure
	--"swi", -- Sui; not sure
	"tbq-lol-pro", -- Proto-Loloish
	"tdh", -- Thulung
	"ukk", -- Muak Sa-aak
	"vi", -- Vietnamese
	"yig", -- Wusa Nasu
	"zng", -- Mang

	-------- Languages with ~ with surrounding spaces used to separate variants --------
	"mkh-ban-pro", -- Proto-Bahnaric
	"sit-pro", -- Proto-Sino-Tibetan; listed above

	-------- Other weirdnesses --------
	"mul", -- Translingual; gestures, Morse code, etc.
	"aot", -- Atong (India); bullet is a letter

	-------- All sign languages	--------
	"ads",
	"aed",
	"aen",
	"afg",
	"ase",
	"asf",
	"asp",
	"asq",
	"asw",
	"bfi",
	"bfk",
	"bog",
	"bqn",
	"bqy",
	"bvl",
	"bzs",
	"cds",
	"csc",
	"csd",
	"cse",
	"csf",
	"csg",
	"csl",
	"csn",
	"csq",
	"csr",
	"doq",
	"dse",
	"dsl",
	"ecs",
	"esl",
	"esn",
	"eso",
	"eth",
	"fcs",
	"fse",
	"fsl",
	"fss",
	"gds",
	"gse",
	"gsg",
	"gsm",
	"gss",
	"gus",
	"hab",
	"haf",
	"hds",
	"hks",
	"hos",
	"hps",
	"hsh",
	"hsl",
	"icl",
	"iks",
	"ils",
	"inl",
	"ins",
	"ise",
	"isg",
	"isr",
	"jcs",
	"jhs",
	"jls",
	"jos",
	"jsl",
	"jus",
	"kgi",
	"kvk",
	"lbs",
	"lls",
	"lsl",
	"lso",
	"lsp",
	"lst",
	"lsy",
	"lws",
	"mdl",
	"mfs",
	"mre",
	"msd",
	"msr",
	"mzc",
	"mzg",
	"mzy",
	"nbs",
	"ncs",
	"nsi",
	"nsl",
	"nsp",
	"nsr",
	"nzs",
	"okl",
	"pgz",
	"pks",
	"prl",
	"prz",
	"psc",
	"psd",
	"psg",
	"psl",
	"pso",
	"psp",
	"psr",
	"pys",
	"rms",
	"rsl",
	"rsm",
	"sdl",
	"sfb",
	"sfs",
	"sgg",
	"sgx",
	"slf",
	"sls",
	"sqk",
	"sqs",
	"ssp",
	"ssr",
	"svk",
	"swl",
	"syy",
	"tse",
	"tsm",
	"tsq",
	"tss",
	"tsy",
	"tza",
	"ugn",
	"ugy",
	"ukl",
	"uks",
	"vgt",
	"vsi",
	"vsl",
	"vsv",
	"xki",
	"xml",
	"xms",
	"ygs",
	"ysl",
	"zib",
	"zsl",
}

-- In these languages, the hyphen is not considered a word separator for the "multiword terms" category.
data.hyphen_not_multiword_sep = list_to_set{
	"akk", -- Akkadian; hyphens between syllables
	"akl", -- Aklanon; hyphens for mid-word glottal stops
	"ber-pro", -- Proto-Berber; morphemes separated by hyphens
	"ceb", -- Cebuano; hyphens for mid-word glottal stops
	"cnk", -- Khumi Chin; hyphens used in single words
	"cpi", -- Chinese Pidgin English; Chinese-derived words with hyphens between syllables
	"de", -- too many false positives
	"esx-esk-pro", -- hyphen used to separate morphemes
	"fi", -- Finnish; hyphen used to separate components in compound words if the final and initial vowels match, respectively
	"hil", -- Hiligaynon; hyphens for mid-word glottal stops
	"hnn", -- Hanunoo; too many false positives
	"ilo", -- Ilocano; hyphens for mid-word glottal stops
	"kne", -- Kankanaey; hyphens for mid-word glottal stops
	"lcp", -- Western Lawa; dash as syllable joiner
	"lwl", -- Eastern Lawa; dash as syllable joiner
	"mfa", -- Pattani Malay in Thai script; dash as syllable joiner
	"mkh-vie-pro", -- Proto-Vietic; morphemes separated by hyphens
	"msb", -- Masbatenyo; too many false positives
	"tl", -- Tagalog; too many false positives
	"war", -- Waray-Waray; too many false positives
	"yo", -- Yoruba; hyphens used to show lengthened nasal vowels
}

-- These languages will not have "LANG masculine nouns" and similar categories added.
data.no_gender_cat = list_to_set{
	-- Languages without gender but which use the gender field for other purposes
	"ja",
	"th",
}

data.notranslit = list_to_set{
	"ams",
	"az",
	"bbc",
	"bug",
	"cdo",
	"cia",
	"cjm",
	"cjy",
	"cmn",
	"cnp",
	"cpi",
	"cpx",
	"csp",
	"czh",
	"czo",
	"gan",
	"hak",
	"hnm",
	"hsn",
	"ja",
	"kzg",
	"lad",
	"ltc",
	"luh",
	"lzh",
	"mnp",
	"ms",
	"mul",
	"mvi",
	"nan",
	"nan-dat",
	"nan-hbl",
	"nan-hlh",
	"nan-lnx",
	"nan-tws",
	"nan-zhe",
	"nan-zsh",
	"och",
	"oj",
	"okn",
	"ryn",
	"rys",
	"ryu",
	"sh",
	"sjc",
	"tgt",
	"th",
	"tkn",
	"tly",
	"txg",
	"und",
	"vi",
	"wuu",
	"xug",
	"yoi",
	"yox",
	"yue",
	"za",
	"zh",
	"zhx-sic",
	"zhx-tai",
}

-- Script codes for which a script-tagged display title will be added.
data.toBeTagged = list_to_set{
	"Ahom",
	"Arab",
		"fa-Arab",
		"glk-Arab",
		"kk-Arab",
		"ks-Arab",
		"ku-Arab",
		"mzn-Arab",
		"ms-Arab",
		"ota-Arab",
		"pa-Arab",
		"ps-Arab",
		"sd-Arab",
		"tt-Arab",
		"ug-Arab",
		"ur-Arab",
	"Armi",
	"Armn",
	"Avst",
	"Bali",
	"Bamu",
	"Batk",
	"Beng",
		"as-Beng",
	"Bopo",
	"Brah",
	"Brai",
	"Bugi",
	"Buhd",
	"Cakm",
	"Cans",
	"Cari",
	"Cham",
	"Cher",
	"Copt",
	"Cprt",
	"Cyrl",
	"Cyrs",
	"Deva",
	"Dsrt",
	"Egyd",
	"Egyp",
	"Ethi",
	"Geok",
	"Geor",
	"Glag",
	"Goth",
	"Grek",
		"Polyt",
		"polytonic",
	"Gujr",
	"Guru",
	"Hang",
	"Hani",
	"Hano",
	"Hebr",
	"Hira",
	"Hluw",
	"Ital",
	"Java",
	"Kali",
	"Kana",
	"Khar",
	"Khmr",
	"Knda",
	"Kthi",
	"Lana",
	"Laoo",
	"Latn",
		"Latf",
		"Latg",
		"Latnx",
		"Latinx",
		"pjt-Latn",
	"Lepc",
	"Limb",
	"Linb",
	"Lisu",
	"Lyci",
	"Lydi",
	"Mand",
	"Mani",
	"Marc",
	"Merc",
	"Mero",
	"Mlym",
	"Mong",
		"mnc-Mong",
		"sjo-Mong",
		"xwo-Mong",
	"Mtei",
	"Mymr",
	"Narb",
	"Nkoo",
	"Nshu",
	"Ogam",
	"Olck",
	"Orkh",
	"Orya",
	"Osma",
	"Ougr",
	"Palm",
	"Phag",
	"Phli",
	"Phlv",
	"Phnx",
	"Plrd",
	"Prti",
	"Rjng",
	"Runr",
	"Samr",
	"Sarb",
	"Saur",
	"Sgnw",
	"Shaw",
	"Shrd",
	"Sinh",
	"Sora",
	"Sund",
	"Sylo",
	"Syrc",
	"Tagb",
	"Tale",
	"Talu",
	"Taml",
	"Tang",
	"Tavt",
	"Telu",
	"Tfng",
	"Tglg",
	"Thaa",
	"Thai",
	"Tibt",
	"Ugar",
	"Vaii",
	"Xpeo",
	"Xsux",
	"Yiii",
	"Zmth",
	"Zsym",

	"Ipach",
	"Music",
	"Rumin",
}

-- Parts of speech which will not be categorised in categories like "English terms spelled with É" if
-- the term is the character in question (e.g. the letter entry for English [[é]]). This contrasts with
-- entries like the French adjective [[m̂]], which is a one-letter word spelled with the letter.
data.pos_not_spelled_with_self = list_to_set{
	"diacritical marks",
	"Han characters",
	"Han tu",
	"hanja",
	"hanzi",
	"iteration marks",
	"kana",
	"kanji",
	"letters",
	"ligatures",
	"logograms",
	"morae",
	"numeral symbols",
	"numerals",
	"punctuation marks",
	"syllables",
	"symbols",
}

------ 2. Lists not converted into sets. ------

-- Recognized aliases for parts of speech (param 2=). Key is the short form and value is the canonical singular (not
-- pluralized) form. It is singular so that the same table can be used in [[Module:form of]] for the p=/POS= param
-- and [[Module:links]] for the pos= param.
data.pos_aliases = {
	a = "adjective",
	adj = "adjective",
	adv = "adverb",
	art = "article",
	det = "determiner",
	cnum = "cardinal number",
	conj = "conjunction",
	conv = "converb",
	int = "interjection",
	interj = "interjection",
	intj = "interjection",
	n = "noun",
	num = "numeral",
	part = "participle",
	pcl = "particle",
	phr = "phrase",
	pn = "proper noun",
	postp = "postposition",
	pre = "preposition",
	prep = "preposition",
	pro = "pronoun",
	pron = "pronoun",
	prop = "proper noun",
	proper = "proper noun",
	onum = "ordinal number",
	rom = "romanization",
	v = "verb",
	vb = "verb",
	vi = "intransitive verb",
	vt = "transitive verb",
	vti = "transitive and intransitive verb",
}

-- Parts of speech for which categories like "German masculine nouns" or "Russian imperfective verbs"
-- will be generated if the headword is of the appropriate gender/number.
data.pos_for_gender_number_cat = {
	["nouns"] = "nouns",
	["proper nouns"] = "nouns",
	["suffixes"] = "suffixes",
	-- We include verbs because impf and pf are valid "genders".
	["verbs"] = "verbs",
}

------ 3. Page-wide processing (so that it only needs to be done once per page). ------
data.page = require(headword_page_module).process_page()
-- Fuckme, random references to data.pagename and data.encoded_pagename are scattered throughout the codebase. FIXME!
data.pagename = data.page.pagename
data.encoded_pagename = data.page.encoded_pagename

return data