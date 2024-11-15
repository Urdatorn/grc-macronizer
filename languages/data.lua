local m_scripts = require("scripts")

local table = table
local insert = table.insert
local u = require("string.char")

local export = {}

-- UTF-8 encoded strings for some commonly-used diacritics.
local c = {
	grave			= u(0x0300),
	acute			= u(0x0301),
	circ			= u(0x0302),
	tilde			= u(0x0303),
	macron			= u(0x0304),
	overline		= u(0x0305),
	breve			= u(0x0306),
	dotabove		= u(0x0307),
	diaer			= u(0x0308),
	ringabove		= u(0x030A),
	dacute			= u(0x030B),
	caron			= u(0x030C),
	lineabove		= u(0x030D),
	dgrave			= u(0x030F),
	invbreve		= u(0x0311),
	commaabove		= u(0x0313),
	revcommaabove	= u(0x0314),
	dotbelow		= u(0x0323),
	diaerbelow		= u(0x0324),
	ringbelow		= u(0x0325),
	cedilla			= u(0x0327),
	ogonek			= u(0x0328),
	brevebelow		= u(0x032E),
	macronbelow		= u(0x0331),
	perispomeni		= u(0x0342),
	ypogegrammeni	= u(0x0345),
	CGJ				= u(0x034F), -- combining grapheme joiner
	zigzag			= u(0x035B),
	dbrevebelow		= u(0x035C),
	dmacron			= u(0x035E),
	dtilde			= u(0x0360),
	dinvbreve		= u(0x0361),
	small_a			= u(0x0363),
	small_e			= u(0x0364),
	small_i			= u(0x0365),
	small_o			= u(0x0366),
	small_u			= u(0x0367),
	kamora          = u(0x0484),
	dasiapneumata   = u(0x0485),
	psilipneumata   = u(0x0486),
	kashida			= u(0x0640),
	fathatan		= u(0x064B),
	dammatan		= u(0x064C),
	kasratan		= u(0x064D),
	fatha			= u(0x064E),
	damma			= u(0x064F),
	kasra			= u(0x0650),
	shadda			= u(0x0651),
	sukun			= u(0x0652),
	hamzaabove		= u(0x0654),
	nunghunna		= u(0x0658),
	zwarakay        = u(0x0659),
	smallv			= u(0x065A),
	superalef		= u(0x0670),
	udatta			= u(0x0951),
	anudatta		= u(0x0952),
	psili			= u(0x1FBD),
	coronis			= u(0x1FBF),
	ZWNJ			= u(0x200C), -- zero width non-joiner
	ZWJ				= u(0x200D), -- zero width joiner
	RSQuo			= u(0x2019), -- right single quote
	VS01			= u(0xFE00), -- variation selector 1
	-- Punctuation for the standardChars field.
	-- Note: characters are literal (i.e. no magic characters).
	punc			= " ',-‐‑‒–—…∅",
	-- Range covering all diacritics.
	diacritics		= u(0x300) .. "-" .. u(0x34E) ..
						u(0x350) .. "-" .. u(0x36F) ..
						u(0x1AB0) .. "-" .. u(0x1ACE) ..
						u(0x1DC0) .. "-" .. u(0x1DFF) ..
						u(0x20D0) .. "-" .. u(0x20F0) ..
						u(0xFE20) .. "-" .. u(0xFE2F),
}
-- Braille characters for the standardChars field.
local braille = {}
for i = 0x2800, 0x28FF do
	insert(braille, u(i))
end
c.braille = table.concat(braille)
export.chars = c

-- PUA characters, generally used in sortkeys.
-- Note: if the limit needs to be increased, do so in powers of 2 (due to the way memory is allocated for tables).
local p = {}
for i = 1, 32 do
	p[i] = u(0xF000+i-1)
end
export.puaChars = p

local s = {}
-- These values are placed here to make it possible to synchronise a group of languages without the need for a dedicated function module.

s["cau-Cyrl-displaytext"] = {
	from = {"[IlΙІӀ]", "ᴴ"},
	to = {"ӏ", "ᵸ"}
}

s["cau-Cyrl-entryname"] = {
	remove_diacritics = c.grave .. c.acute .. c.macron,
	from = s["cau-Cyrl-displaytext"].from,
	to = s["cau-Cyrl-displaytext"].to
}

s["cau-Latn-entryname"] = {remove_diacritics = c.grave .. c.acute .. c.macron}

s["Cyrs-entryname"] = {remove_diacritics = c.grave .. c.acute ..  c.diaer .. c.kamora .. c.dasiapneumata .. c.psilipneumata}

s["Cyrs-sortkey"] = {
	from = {
		"ї", "оу", -- 2 chars
		"ґ", "ꙣ", "є", "[ѕꙃꙅ]", "ꙁ", "[іꙇ]", "[ђꙉ]", "[ѻꙩꙫꙭꙮꚙꚛ]", "ꙋ", "[ѡѿꙍѽ]", "ꙑ", "ѣ", "ꙗ", "ѥ", "ꙕ", "[ѧꙙ]", "[ѩꙝ]", "ꙛ", "ѫ", "ѭ", "ѯ", "ѱ", "ѳ", "ѵ", "ҁ" -- 1 char
	},
	to = {
		"и" .. p[1], "у",
		"г" .. p[1], "д" .. p[1], "е", "ж" .. p[1], "з", "и" .. p[1], "и" .. p[2], "о", "у", "х" .. p[1], "ы", "ь" .. p[1], "ь" .. p[2], "ь" .. p[3], "ю", "я", "я" .. p[1], "я" .. p[2], "я" .. p[3], "я" .. p[4], "я" .. p[5], "я" .. p[6], "я" .. p[7], "я" .. p[8], "я" .. p[9]
	},
}

s["Grek-sortkey"] = {
	remove_diacritics = c.grave .. c.acute .. c.diaer .. c.caron .. c.commaabove .. c.revcommaabove .. c.macron .. c.breve .. c.diaerbelow .. c.brevebelow .. c.perispomeni .. c.ypogegrammeni,
	from = {"ϝ", "ͷ", "ϛ", "ͱ", "ϻ", "ϟ", "ϙ", "ς", "ϡ", "ͳ"},
	to = {"ε" .. p[1], "ε" .. p[2], "ε" .. p[3], "ζ" .. p[1], "π" .. p[1], "π" .. p[2], "π" .. p[2], "σ", "ω" .. p[1], "ω" .. p[1]}
}

s["Jpan-standardchars"] = -- exclude ぢづヂヅ
	"ぁあぃいぅうぇえぉおかがきぎくぐけげこごさざしじすずせぜそぞただちっつてでとどなにぬねのはばぱひびぴふぶぷへべぺほぼぽまみむめもゃやゅゆょよらりるれろん" ..
	"ァアィイゥウェエォオカガキギクグケゲコゴサザシジスズセゼソゾタダチッツテデトドナニヌネノハバパヒビピフブプヘベペホボポマミムメモャヤュユョヨラリルレロン"

local jpx_displaytext = {
	from = {"～", "＝"},
	to = {"〜", "゠"}
}

s["jpx-displaytext"] = {
	Jpan = jpx_displaytext,
	Hani = jpx_displaytext,
	Hrkt = jpx_displaytext,
	Hira = jpx_displaytext,
	Kana = jpx_displaytext
	-- not Latn or Brai
}

s["jpx-entryname"] = s["jpx-displaytext"]

s["jpx-sortkey"] = {
	Jpan = "Jpan-sortkey",
	Hani = "Hani-sortkey",
	Hrkt = "Hira-sortkey", -- sort general kana by normalizing to Hira
	Hira = "Hira-sortkey",
	Kana = "Kana-sortkey",
	Latn = {remove_diacritics = c.tilde .. c.macron .. c.diaer}
}

s["jpx-translit"] = {
	Hrkt = "Hrkt-translit",
	Hira = "Hrkt-translit",
	Kana = "Hrkt-translit"
}

local HaniChars = m_scripts.getByCode("Hani"):getCharacters()
-- `漢字(한자)`→`漢字`
-- `가-나-다`→`가나다`, `가--나--다`→`가-나-다`
-- `온돌(溫突/溫堗)`→`온돌` ([[ondol]])
s["Kore-entryname"] = {
	remove_diacritics = u(0x302E) .. u(0x302F),
	from = {"([" .. HaniChars .. "])%(.-%)", "^%-", "%-$", "%-(%-?)", "\1", "%([" .. HaniChars .. "/]+%)"},
	to = {"%1", "\1", "\1", "%1", "-"}
}

s["Lisu-sortkey"] = {
	from = {"𑾰"},
	to = {"ꓬ" .. p[1]}
}

s["Mong-displaytext"] = {
	from = {"([ᠨ-ᡂᡸ])ᠶ([ᠨ-ᡂᡸ])", "([ᠠ-ᡂᡸ])ᠸ([^᠋ᠠ-ᠧ])", "([ᠠ-ᡂᡸ])ᠸ$"},
	to = {"%1ᠢ%2", "%1ᠧ%2", "%1ᠧ"}
}

s["Mong-entryname"] = s["Mong-displaytext"]

s["Polyt-entryname"] = {
	remove_diacritics = c.macron .. c.breve .. c.dbrevebelow,
	from = {"[" .. c.RSQuo .. c.psili .. c.coronis .. "]"},
	to = {"'"}
}

s["roa-oil-sortkey"] = {
	remove_diacritics = c.grave .. c.acute .. c.circ .. c.diaer .. c.ringabove .. c.cedilla .. "'",
	from = {"æ", "œ"},
	to = {"ae", "oe"}
}

s["Tibt-displaytext"] = {
	from = {"ༀ", "༌", "།།", "༚༚", "༚༝", "༝༚", "༝༝", "ཷ", "ཹ", "ེེ", "ོོ"},
	to = {"ཨོཾ", "་", "༎", "༛", "༟", "࿎", "༞", "ྲཱྀ", "ླཱྀ", "ཻ", "ཽ"}
}

s["Tibt-entryname"] = s["Tibt-displaytext"]

s["wen-sortkey"] = {
	from = {
		"l", -- Ensure "l" comes after "ł".
		"b́", "č", "ć", "dź", "ě", "f́", "ch", "ł", "ḿ", "ń", "ó", "ṕ", "ř", "ŕ", "š", "ś", "ẃ", "ž", "ż", "ź"
	},
	to = {
		"l" .. p[1],
		"b" .. p[1], "c" .. p[1], "c" .. p[2], "d" .. p[1], "e" .. p[1], "f" .. p[1], "h" .. p[1], "l", "m" .. p[1], "n" .. p[1], "o" .. p[1], "p" .. p[1], "r" .. p[1], "r" .. p[2], "s" .. p[1], "s" .. p[2], "w" .. p[1], "z" .. p[1], "z" .. p[2], "z" .. p[3]
	}
}

export.shared = s

-- Short-term solution to override the standard substitution process, by forcing the module to substitute the entire text in one pass. This results in any PUA characters that are used as stand-ins for formatting being handled by the language-specific substitution process, which is usually undesirable.
-- This override is provided for languages which use formatting between strings of text which might need to interact with each other (e.g. Korean 값이 transliterates as "gaps-i", but [[값]] has the formatting '''값'''[[-이]]. The normal process would split the text at the second '''.)
export.contiguous_substitution = {
	["ja"] = "tr",
	["jje"] = "tr",
	["ko"] = "tr",
	["ko-ear"] = "tr",
	["ru"] = "tr",
	["th-new"] = "tr",
	["sa"] = "tr",
	["zkt"] = "tr",
}

-- Code aliases. The left side is the alias and the right side is the canonical code. NOTE: These are gradually
-- being deprecated, so should not be added to on a permanent basis. Temporary additions are permitted under reasonable
-- circumstances (e.g. to facilitate changing a language's code). When an alias is no longer used, it should be removed.
-- Aliases in this table are tracked at [[Wiktionary:Tracking/languages/LANG]]; see e.g.
-- [[Special:WhatLinksHere/Wiktionary:Tracking/languages/RL.]] for the `RL.` alias.
export.aliases = {
	["CL."] = "la-cla",
	["EL."] = "la-ecc",
	["LL."] = "la-lat",
	["ML."] = "la-med",
	["NL."] = "la-new",
	["RL."] = "la-ren",
	["VL."] = "la-vul",
	["prv"] = "oc-pro",
	["nan-hnm"] = "hnm",
	["nan-luh"] = "luh",
}

-- Codes which are tracked. Note that all aliases listed above are also tracked, so should not be duplicated here.
-- Tracking uses the same mechanism described above in the comment above `export.aliases`.
export.track = {
	-- Codes duplicated between full and etymology-only languages.
	["lzh-lit"] = true,
	-- Languages actively being converted to families.
	["bh"] = true, -- inc-bih
	["nan"] = true, -- zhx-nan
}

return export