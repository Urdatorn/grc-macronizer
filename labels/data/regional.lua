local labels = {}

------------------------------------------ Generic ------------------------------------------

--not sure where to put this
labels["Classical"] = {
	aliases = {"classical"},
	-- "ca", "fa", "id", la", "zh" handled in lang-specific module
	langs = {"ar", "az", "ja", "jv", "kum", "ms", "quc", "sa", "tl"},
	special_display = "[[Classical <canonical_name>]]",
	regional_categories = true,
}

labels["Epigraphic"] = {
	langs = {"grc", "pgd", "pra", "sa"},
	special_display = "[[w:Epigraphy|Epigraphic <canonical_name>]]",
	regional_categories = true,
}

labels["regional"] = {
	display = "[[regional#English|regional]]",
	regional_categories = true,
}


------------------------------------------ Places ------------------------------------------

labels["Anatri"] = {
	aliases = {"Lower Chuvash"},
	langs = {"cv"}, -- e.g. вот "fire" vs the Upper Chuvash / literary standard вут 
	Wikipedia = true,
	regional_categories = true,
}

labels["Australia"] = {
	aliases = {"AU", "Australian"},
	-- "de", "en", "mt", "zh" handled in lang-specific modules
	langs = {"el", "it", "ko", "ru"},
	Wikipedia = true,
	regional_categories = "Australian",
}

labels["Black Isle"] = {
	langs = {"sco"}, -- conceivably also en, gd, perhaps enm, but -sche could only find sco
	Wikipedia = true,
	regional_categories = true,
}

-- WARNING: No existing languages or categories associated with label; add to `langs` as needed
labels["Bogor"] = {
	langs = {},
	Wikipedia = true,
	regional_categories = true,
}

labels["Brazil"] = {
	aliases = {"Brazilian"},
	-- "pt" handled in lang-specific module
	langs = {"ja", "mch", "vec", "yi"},
	Wikipedia = true,
	regional_categories = "Brazilian",
}

-- WARNING: No existing languages or categories associated with label; add to `langs` as needed
labels["Brebes"] = {
	aliases = {"Brebian"},
	langs = {},
	Wikipedia = "Brebes Regency",
	regional_categories = true,
}

labels["Britain"] = {
	aliases = {"Brit", "British", "Great Britain"},
	-- "en", "zh" handled in lang-specific module
	langs = {"bn", "ur", "vi"},
	Wikipedia = "Great Britain",
	regional_categories = "British",
}

labels["Bukovina"] = {
	aliases = {"Bucovina", "Bukovinian", "Bukowina"},
	langs = {"pl", "ro", "uk"},
	Wikipedia = true,
	regional_categories = "Bukovinian",
}

-- WARNING: No existing languages or categories associated with label; add to `langs` as needed
labels["Burundi"] = {
	aliases = {"Burundian"},
	langs = {},
	Wikipedia = true,
	regional_categories = "Burundian",
}

labels["Canada"] = {
	aliases = {"Canadian"},
	-- "en", "fr", "zh" handled in lang-specific module
	langs = {"gd", "haa", "is", "ko", "ru", "tli", "uk", "vi"},
	Wikipedia = true,
	regional_categories = "Canadian",
}

labels["China"] = {
	-- "en", "ko" handled in lang-specific module
	langs = {"ja", "khb", "kk", "mhx", "mn", "ug"},
	Wikipedia = true,
	regional_categories = "Chinese",
}

labels["Congo"] = {
	aliases = {"Democratic Republic of the Congo", "Democratic Republic of Congo", "DR Congo", "Congo-Kinshasa", "Republic of the Congo", "Republic of Congo", "Congo-Brazzaville", "Congolese"}, -- these could be split if need be
	-- "fr" handled in lang-specific module
	langs = {"avu", "yom"},
	Wikipedia = true,
	regional_categories = "Congolese",
}

labels["Cyprus"] = {
	aliases = {"cypriot", "Cypriot"},
	-- "tr" handled in lang-specific module
	langs = {"ar", "el"},
	Wikipedia = true,
	regional_categories = "Cypriot",
}

labels["Dobruja"] = {
	aliases = {"Dobrogea", "Dobrujan"},
	langs = {"crh", "ro"},
	Wikipedia = true,
	regional_categories = "Dobrujan",
}

-- WARNING: No existing languages or categories associated with label; add to `langs` as needed
labels["Durban"] = {
	langs = {},
	Wikipedia = true,
	regional_categories = true,
}

labels["Europe"] = {
	-- "en", "es", "fr", "pt" handled in lang-specific module
	langs = {"ur"},
	Wikipedia = true,
	regional_categories = "European",
}

labels["France"] = {
	aliases = {"French"},
	-- "fr", "zh" handled in lang-specific module
	langs = {"la", "lad", "nrf", "vi", "yi"},
	Wikipedia = true,
	regional_categories = "French",
}

labels["India"] = {
	aliases = {"Indian"},
	-- "en", "pa", "pt" handled in lang-specific module
	langs = {"bn", "dv", "fa", "ml", "ta", "ur"},
	Wikipedia = true,
	regional_categories = "Indian",
}

labels["Indonesia"] = {
	aliases = {"Indonesian"},
	-- "en", "zh" handled in lang-specific module
	langs = {"id", "jv", "ms", "nl"},
	Wikipedia = true,
	regional_categories = "Indonesian",
}

labels["Israel"] = {
	aliases = {"Israeli"},
	-- "en" handled in lang-specific module
	langs = {"ajp", "ar", "he", "ru", "yi"},
	Wikipedia = true,
	regional_categories = "Israeli",
}

-- WARNING: No existing languages or categories associated with label; add to `langs` as needed
labels["Kalix"] = {
	langs = {},
	Wikipedia = true,
	regional_categories = true,
}

-- FIXME: Move to Uyghur label data module
labels["Kazakhstan"] = {
	aliases = {"Kazakhstani", "Kazakh"},
	langs = {"ug"},
	Wikipedia = true,
	regional_categories = "Kazakhstani",
}

-- WARNING: No existing languages or categories associated with label; add to `langs` as needed
labels["Kemaliye"] = {
	langs = {},
	Wikipedia = true,
	regional_categories = true,
}

-- WARNING: No existing languages or categories associated with label; add to `langs` as needed
labels["Kitti"] = {
	langs = {},
	Wikipedia = "Kitti, Federated States of Micronesia",
	regional_categories = true,
}

-- WARNING: No existing languages or categories associated with label; add to `langs` as needed
labels["Kukkuzi"] = {
	langs = {},
	Wikipedia = true,
	regional_categories = true,
}

-- WARNING: No existing languages or categories associated with label; add to `langs` as needed
labels["Lucknow"] = {
	langs = {},
	Wikipedia = true,
	regional_categories = true,
}

-- WARNING: No existing languages or categories associated with label; add to `langs` as needed
labels["Luleå"] = {
	aliases = {"Lulea"},
	langs = {},
	Wikipedia = true,
	regional_categories = true,
}

labels["Lviv"] = {
	aliases = {"Lvov", "Lwow", "Lwów"},
	langs = {"pl", "uk"},
	Wikipedia = true,
	regional_categories = true,
}

-- WARNING: No existing languages or categories associated with label; add to `langs` as needed
labels["Muş"] = {
	aliases = {"Mush"},
	langs = {},
	Wikipedia = true,
	regional_categories = true,
}

labels["Myanmar"] = {
	aliases = {"Myanmarese", "Burma", "Burmese"},
	-- "en", "my", "zh" handled in lang-specific module; FIXME: move ksw and mnw to lang-specific modules
	langs = {"ksw", "mnw"},
	Wikipedia = true,
	regional_categories = true,
}

labels["Nigeria"] = {
	aliases = {"Nigerian"},
	-- "en" handled in lang-specific module
	langs = {"ar", "ff", "guw", "ha", "yo"},
	Wikipedia = true,
	regional_categories = "Nigerian",
}

labels["Palestine"] = {
	aliases = {"Palestinian"},
	-- "en" handled in lang-specific module
	langs = {"ajp", "ar", "arc"},
	Wikipedia = true,
	regional_categories = "Palestinian",
}

-- WARNING: No existing languages or categories associated with label; add to `langs` as needed
labels["Priangan"] = {
	langs = {},
	Wikipedia = "Parahyangan",
	regional_categories = true,
}

-- WARNING: No existing languages or categories associated with label; add to `langs` as needed
labels["Rome"] = {
	aliases = {"Roma", "Romano"},
	langs = {},
	Wikipedia = true,
	regional_categories = "Roman",
}

labels["Scania"] = {
	aliases = {"Scanian", "Skanian", "Skåne"},
	langs = {"gmq-oda", "sv"},
	Wikipedia = true,
	regional_categories = "Scanian",
}

-- Silesia German, Silesia Polish; for differentiation between sli "Silesian East Central German"
-- don't add Silesian as alias
labels["Silesia"] = {
	langs = {"de", "pl"},
	Wikipedia = true,
}

labels["South Africa"] = {
	aliases = {"South African"},
	-- "de", "en", "pt" handled in lang-specific module
	langs = {"af", "nl", "st", "te", "yi", "zu"},
	Wikipedia = true,
	regional_categories = "South African",
}

labels["Spain"] = {
	aliases = {"Spanish", "ES"},
	-- "ca", "es" handled in lang-specific module
	langs = {"la"},
	Wikipedia = true,
	regional_categories = "Spanish",
}

-- WARNING: No existing languages or categories associated with label; add to `langs` as needed
labels["Surati"] = {
	langs = {},
	Wikipedia = "Surat district",
	regional_categories = true,
}

-- WARNING: No existing languages or categories associated with label; add to `langs` as needed
labels["Surgut"] = {
	langs = {},
	Wikipedia = true,
	regional_categories = true,
}

labels["Suriname"] = {
	aliases = {"Surinamese"},
	langs = {"car", "hns", "jv", "nl"},
	Wikipedia = true,
	regional_categories = "Surinamese",
}

labels["Thailand"] = {
	aliases = {"Thai"},
	-- "en", "zh" handled in lang-specific module
	langs = {"khb", "mnw", "th"},
	Wikipedia = true,
	regional_categories = "Thai",
}

labels["UK"] = {
	aliases = {"United Kingdom"},
	-- "en", "zh" handled in lang-specific module
	langs = {"bn", "ur", "vi"},
	Wikipedia = "United Kingdom",
	regional_categories = "British",
}

-- WARNING: No existing languages or categories associated with label; add to `langs` as needed
labels["Old Ukrainian"] = {
	langs = {},
	Wikipedia = true,
	plain_categories = true,
}

labels["US"] = {
	aliases = {"U.S.", "United States", "United States of America", "USA", "America", "American"}, -- America/American: should these be aliases of 'North America'?
	-- DO NOT include "es" here, otherwise {{lb|es|American}} will categorize in [[:Category:American Spanish]]; see [[:Category:United States Spanish]].
	-- "de", "en", "pt", "zh" handled in lang-specific module
	langs = {"hi", "is", "it", "ja", "ko", "nl", "ru", "tli", "ur", "vi", "yi"},
	Wikipedia = "United States",
	regional_categories = "American",
}

-- WARNING: No existing languages or categories associated with label; add to `langs` as needed
labels["Vilhelmina"] = {
	langs = {},
	Wikipedia = true,
	regional_categories = true,
}

labels["Viryal"] = {
	aliases = {"Upper Chuvash"},
	langs = {"cv"},
	Wikipedia = true,
	regional_categories = true,
}

-- WARNING: No existing languages or categories associated with label; add to `langs` as needed
labels["Wallonia"] = {
	aliases = {"Wallonian"},
	langs = {},
	Wikipedia = true,
	regional_categories = "Wallonian",
}

-- WARNING: No existing languages or categories associated with label; add to `langs` as needed
labels["Special Region of Yogyakarta"] = {
	aliases = {"SR Yogyakarta"},
	langs = {},
	Wikipedia = true,
	regional_categories = true,
}

-- WARNING: No existing languages or categories associated with label; add to `langs` as needed
labels["Zakarpattia"] = {
	langs = {},
	Wikipedia = "Zakarpattia Oblast",
	regional_categories = true,
}

-- WARNING: No existing languages or categories associated with label; add to `langs` as needed
labels["Zululand"] = {
	langs = {},
	Wikipedia = true,
	regional_categories = true,
}


------------------------------------------ Chinese romanizations ------------------------------------------

labels["Hanyu Pinyin"] = {
	aliases = {"Hanyu pinyin", "Pinyin", "pinyin"},
	Wikidata = "Q42222",
	plain_categories = true,
}

labels["Postal Romanization"] = {
	aliases = {"Postal romanization", "postal romanization", "Postal", "postal"},
	Wikidata = "Q151868",
	plain_categories = true,
}

labels["Tongyong Pinyin"] = {
	aliases = {"Tongyong pinyin"},
	Wikidata = "Q700739",
	plain_categories = true,
}

labels["Wade–Giles"] = {
	aliases = {"Wade-Giles"},
	Wikidata = "Q208442",
	plain_categories = true,
}


return require("labels.lua").finalize_data(labels)