local export = {}

export.lang_specific_data_list_module = "Module:labels/data/lang"
export.lang_specific_data_modules_prefix = "Module:labels/data/lang/"
local m_lang_specific_data = mw.loadData(export.lang_specific_data_list_module)
local parse_utilities_module = "Module:parse utilities"
local string_utilities_module = "Module:string utilities"
local table_module = "Module:table"
local utilities_module = "Module:utilities"

--[==[ intro:
Labels go through several stages of processing to get from the original (raw) label specified in the Wikicode to the
final (formatted) label displayed to the user. The following terminology will help keep things straight:

* The "raw label" is the label specified in the Wikicode.
* The "non-canonical label" is the label extracted from the raw label, used for looking up in the label modules in order
  to fetch the associated label data structure and determine the canonical form of the label. Normally this is the same
  as the raw label, but it will be different if the raw label is of the form `!<var>label</var>` (e.g. `!Australian`)
  `<var>label</var>!<var>display</var>` (e.g. `Southern US!Southern`). The former syntax indicates that the label
  should display as-is instead of in its canonical form (which in the example given is `Australia`), and the latter
  syntax indicates that the label should display in the form specified after the exclamation point.
* The "canonical label" is the result of applying alias resolution to the non-canonical label. Normally, the
  canonical label rather than the non-canonical label is what is shown to the user.
* The "display form of the label" is what is shown to the user, not considering links and HTML that may wrap the
  display form to get the formatted form of the label. The display form comes from the `.display` field of the module
  label data for the label; if no such field exists in the label data, it is normally the canonical label. However, if
  the display override exists (see below), it takes precedence over the `.display` field or canonical label when
  determining the display form of the label.
* The "display override", if specified, overrides all other means of determining the display form of the label. It is
  specified in two circumstances, i.e. in the `!<var>label</var>` and `<var>label</var>!<var>display</var>` raw label
  formats (i.e. in the same cirumstances where the raw label and non-canonical label are different).
* The "formatted form of the label" is the final form of the label shown directly to the user. It generally appears to
  the user as the display form of the label, but in the Wikicode, the formatted form may wrap the display form with a
  link to Wikipedia, the Wiktionary glossary or another Wiktionary entry, and that link in turn may be wrapped in an
  HTML span with a "deprecated" CSS class attached, causing the label to display differently (to indicate that it is
  deprecated).
]==]

-- for testing
local force_cat = false

local SUBPAGENAME = mw.title.getCurrentTitle().subpageText

-- Disable tracking on heavy pages to save time.
local pages_where_tracking_is_disabled = {
	-- pages that consistently hit timeouts
	["a"] = true,
	-- pages that sometimes hit timeouts
	["de"] = true,
	["i"] = true,
	["и"] = true,
	["山"] = true,
	["子"] = true,
	["月"] = true,
}

-- Add tracking category for PAGE. The tracking category linked to is [[Wiktionary:Tracking/labels/PAGE]].
-- We also add to [[Wiktionary:Tracking/labels/PAGE/LANGCODE]] and [[Wiktionary:Tracking/labels/PAGE/MODE]] if
-- LANGCODE and/or MODE given.
local function track(page, langcode, mode)
	if pages_where_tracking_is_disabled[SUBPAGENAME] then
		return true
	end
	-- avoid including links in pages (may cause error)
	page = page:gsub("%[", "("):gsub("%]", ")"):gsub("|", "!")
	require("Module:debug/track")("labels/" .. page)
	if langcode then
		require("Module:debug/track")("labels/" .. page .. "/" .. langcode)
	end
	if mode then
		require("Module:debug/track")("labels/" .. page .. "/" .. mode)
	end
	-- We don't currently add a tracking label for both langcode and mode to reduce the total number of labels, to
	-- save some memory.
	return true
end

local function ucfirst(txt)
	return mw.getContentLanguage():ucfirst(txt)
end

local mode_to_outer_class = {
	["label"] = "usage-label-sense",
	["term-label"] = "usage-label-term",
	["accent"] = "usage-label-accent",
	["form-of"] = "usage-label-form-of",
}

local mode_to_property_prefix = {
	["label"] = false,
	["term-label"] = false, -- handled specially
	["accent"] = "accent_",
	["form-of"] = "form_of_",
}

local function validate_mode(mode)
	mode = mode or "label"
	if not mode_to_outer_class[mode] then
		local allowed_values = {}
		for key, _ in pairs(mode_to_outer_class) do
			table.insert(allowed_values, "'" .. key .. "'")
		end
		table.sort(allowed_values)
		error(("Invalid value '%s' for `mode`; should be one of %s"):format(mode, table.concat(allowed_values, ", ")))
	end
	return mode
end

local function getprop(labdata, mode, prop)
	local mode_prefix = mode_to_property_prefix[mode]
	return mode_prefix and labdata[mode_prefix .. prop] or labdata[prop]
end

-- HACK! For languages in any of the given families, check the specified-language Wikipedia for appropriate
-- Wikipedia articles for the language in question (esp. useful for obscure etymology-only languages that may not
-- have English articles for them, like many Chinese lects).
local families_to_wikipedia_languages = {
	{"zhx", "zh"},
	{"sem-arb", "ar"},
}

--[==[
Given language `lang` (a full language, etymology-language or family), fetch a list of Wikimedia languages to check
when converting a Wikidata item to a Wikipedia article. English is always first, followed by the Wikimedia language
code(s) of `lang` if `lang` is a language (which may or may not be the same as `lang`'s Wiktionary code), followed
by the macrolanguage of `lang` for certain languages and families (currently, only languages and families in the Chinese
and Arabic families). If `lang` is nil, only return English. Note that the same code may occur more than once in the
list. This is exported because it's also used by [[Module:category tree/poscatboiler/data/language varieties]].
]==]
function export.get_langs_to_extract_wikipedia_articles_from_wikidata(lang)
	local wikipedia_langs = {}
	table.insert(wikipedia_langs, "en")
	if lang then
		local article_lang = lang
		while article_lang do
			if article_lang:hasType("language") then
				local wmcodes = article_lang:getWikimediaLanguageCodes()
				for _, wmcode in ipairs(wmcodes) do
					table.insert(wikipedia_langs, wmcode)
				end
			end
			article_lang = article_lang:getParent()
		end
		for _, family_to_wp_lang in ipairs(families_to_wikipedia_languages) do
			local family, wp_lang = unpack(family_to_wp_lang)
			if lang:inFamily(family) then
				table.insert(wikipedia_langs, wp_lang)
			end
		end
	end
	return wikipedia_langs
end

--[==[
Fetch the categories to add to a page, given that the label whose canonical form is `canon_label` with language `lang`
has been seen. `labdata` is the label data structure for `label`, fetched from the appropriate submodule. `mode`
specifies how the label was invoked (see {get_label_info()} for more information). The return value is a list of the
actual categories, unless `for_doc` is specified, in which case the categories returned are marked up for display on a
documentation page. If `for_doc` is given, `lang` may be nil to format the categories in a language-independent fashion;
otherwise, it must be specified. If `category_types` is specified, it should be a set object (i.e. with category types
as keys and {true} as values), and only categories of the specified types will be returned.
]==]
function export.fetch_categories(canon_label, labdata, lang, mode, for_doc, category_types)
	local categories = {}

	mode = validate_mode(mode)
	local langcode, canonical_name
	if lang then
		langcode = lang:getFullCode()
		canonical_name = lang:getFullName()
	elseif for_doc then
		langcode = "<var>[langcode]</var>"
		canonical_name = "<var>[language name]</var>"
	else
		error("Internal error: Must specify `lang` unless `for_doc` is given")
	end

	local function labprop(prop)
		return getprop(labdata, mode, prop)
	end
	local empty_list = {}
	local function get_cats(cat_type)
		if category_types and not category_types[cat_type] then
			return empty_list
		end
		local cats = labprop(cat_type)
		if not cats then
			return empty_list
		end
		if type(cats) ~= "table" then
			return {cats}
		end
		return cats
	end

	local topical_categories = get_cats("topical_categories")
	local sense_categories = get_cats("sense_categories")
	local pos_categories = get_cats("pos_categories")
	local regional_categories = get_cats("regional_categories")
	local plain_categories = get_cats("plain_categories")

	local function insert_cat(cat, sense_cat)
		if for_doc then
			cat = "<code>" .. cat .. "</code>"
			if sense_cat then
				if mode == "term-label" then
					cat = cat .. " (using {{tl|tlb}})"
				else
					cat = cat .. " (using {{tl|lb}} or form-of template)"
				end
				cat = mw.getCurrentFrame():preprocess(cat)
			end
		end

		table.insert(categories, cat)
	end

	for _, cat in ipairs(topical_categories) do
		insert_cat(langcode .. ":" .. (cat == true and ucfirst(canon_label) or cat))
	end

	for _, cat in ipairs(sense_categories) do
		if cat == true then
			cat = canon_label
		end
		cat = mode == "term-label" and cat .. " terms" or "terms with " .. cat .. " senses"
		insert_cat(canonical_name .. " " .. cat, true)
	end

	for _, cat in ipairs(pos_categories) do
		insert_cat(canonical_name .. " " .. (cat == true and canon_label or cat))
	end

	for _, cat in ipairs(regional_categories) do
		insert_cat((cat == true and ucfirst(canon_label) or cat) .. " " .. canonical_name)
	end

	for _, cat in ipairs(plain_categories) do
		insert_cat(cat == true and ucfirst(canon_label) or cat)
	end

	return categories
end

--[==[
Return the list of all labels data modules for a label whose language is `lang`. The return value is a list of
module names, with overriding modules earlier in the list (that is, if a label occurs in two modules in the list,
the earlier-listed module takes precedence). If `lang` is nil, only return non-language-specific submodules.
]==]
function export.get_submodules(lang)
	local submodules = {}

	-- get language-specific labels from data module
	local langcode = lang and lang:getFullCode() or nil

	if langcode and m_lang_specific_data.langs_with_lang_specific_modules[langcode] then
		-- prefer per-language label in order to pick subvariety labels over regional ones
		table.insert(submodules, export.lang_specific_data_modules_prefix .. langcode)
	end
	table.insert(submodules, "Module:labels/data")
	table.insert(submodules, "Module:labels/data/qualifiers")
	table.insert(submodules, "Module:labels/data/regional")
	table.insert(submodules, "Module:labels/data/topical")
	return submodules
end

--[==[
Return the formatted form of a label `label` (which should be the canonical form of the label; see comment at top),
given (a) the label data structure `labdata` from one of the data modules; (b) the language object `lang` of the
language being processed, or nil for no language; (c) `deprecated` (true if the label is deprecated, otherwise the
deprecation information is taken from `labdata`); (d) `override_display` (if specified, override the display form of the
label with the specified string, instead of any value in `labdata.display` or `labdata.special_display` or the canonical
label in `label` itself); (e) `mode` (same as `data.mode` passed to {get_label_info()}). Returns two values: the
formatted label form and a boolean indicating whether the label is deprecated.

'''NOTE: Under normal circumstances, do not use this.''' Instead, use {get_label_info()}, which searches all the data
modules for a given label and handles other complications.
]==]
function export.format_label(label, labdata, lang, deprecated, override_display, mode)
	local formatted_label

	mode = validate_mode(mode)
	local function labprop(prop)
		return getprop(labdata, mode, prop)
	end
	deprecated = deprecated or labprop("deprecated")
	if not override_display and labprop("special_display") then
		local function add_language_name(str)
			if str == "canonical_name" then
				if lang then
					return lang:getFullName()
				else
					return "<code><var>[language name]</var></code>"
				end
			else
				return ""
			end
		end

		formatted_label = labprop("special_display"):gsub("<(.-)>", add_language_name)
	else
		--[=[
			If labdata.glossary or labdata.Wikipedia are set to true, there is a glossary definition
			with an anchor identical to the label, or a Wikipedia article with a title
			identical to the label.
				For example, the code
					labels["formal"] = {
						glossary = true,
					}
				indicates that there is a glossary entry for "formal".

			Otherwise:
			* labdata.glossary specifies the anchor in [[Appendix:Glossary]].
			* labdata.Wiktionary specifies an arbitrary Wiktionary page or page + anchor (e.g. a separate Appendix
			  entry).
			* labdata.Wikipedia specifies an arbitrary Wikipedia article.
			* labdata.Wikidata specifies an arbitrary Wikidata item to retrieve a Wikipedia article from, or a list
			  of such items (in this case, we select the first one, but other modules using this info might use all
			  of them). If the item is of the form `wmcode:id`, the Wikipedia article corresponding to `wmcode` is
			  fetched if available. Otherwise, the English-language Wikipedia article is retrieved if available,
			  falling back to the Wikimedia language(s) corresponding to `lang` and then (in certain cases) to the
			  macrolanguage that `lang` is part of.

			Note that if `mode` is specified, prefixed properties (e.g. "accent_display" for `mode` == "accent",
			"form_display" for `mode` == "form") are checked before the bare equivalent (e.g. "display").
		]=]
		local display = override_display or labprop("display") or label

		-- There are several 'Foo spelling' labels specially designed for use in the |from= param in
		-- {{alternative form of}}, {{standard spelling of}} and the like. Often the display includes the word
		-- "spelling" at the end (e.g. if it's defaulted), which is useful when the label is used with {{tl|lb}} or
		-- {{tl|tlb}}; but it causes redundancy when used with the form-of templates, which add the word "form",
		-- "spelling", "standard spelling", etc. after the label.
		if mode == "form-of" then
			display = display:gsub(" spelling$", "")
		end

		if display:find("%[%[") then
			formatted_label = display
		else
			local glossary = labprop("glossary")
			local Wiktionary = labprop("Wiktionary")
			local Wikipedia = labprop("Wikipedia")
			local Wikidata = labprop("Wikidata")
			if glossary then
				local glossary_entry = type(glossary) == "string" and glossary or label
				formatted_label = "[[Appendix:Glossary#" .. glossary_entry .. "|" .. display .. "]]"
			elseif Wiktionary then
				formatted_label = "[[" .. Wiktionary .. "|" .. display .. "]]"
			elseif Wikipedia then
				local Wikipedia_entry = type(Wikipedia) == "string" and Wikipedia or label
				formatted_label = "[[w:" .. Wikipedia_entry .. "|" .. display .. "]]"
			elseif Wikidata then
				if not mw.wikibase then
					error(("Unable to retrieve data from Wikidata ID for label '%s'; `mw.wikibase` not defined"
						):format(label))
				end
				local function make_formatted_label(wmcode, id)
					local article = mw.wikibase.sitelink(id, wmcode .. "wiki")
					if article then
						local link = wmcode == "en" and "w:" .. article or "w:" .. wmcode .. ":" .. article
						return ("[[%s|%s]]"):format(link, display)
					else
						return nil
					end
				end
				if type(Wikidata) == "table" then
					Wikidata = Wikidata[1]
				end
				local wmcode, id = Wikidata:match("^(.*):(.*)$")
				if wmcode then
					formatted_label = make_formatted_label(wmcode, id)
				else
					local langs_to_check = export.get_langs_to_extract_wikipedia_articles_from_wikidata(lang)
					for _, wmcode in ipairs(langs_to_check) do
						formatted_label = make_formatted_label(wmcode, Wikidata)
						if formatted_label then
							break
						end
					end
				end
				formatted_label = formatted_label or display
			else
				formatted_label = display
			end
		end
	end

	if deprecated then
		formatted_label = '<span class="deprecated-label">' .. formatted_label .. '</span>'
	end

	return formatted_label, deprecated
end

--[==[
Return information on a label. On input `data` is an object with the following fields:
* `label`: The raw label to return information on.
* `lang`: The language of the label. Must be specified unless `for_doc` is given.
* `mode`: How the label was invoked. One of the following:
  ** {nil} or {"label"}: invoked through {{tl|lb}} or another template whose labels in the same fashion, e.g.
     {{tl|alt}}, {{tl|quote}} or {{tl|syn}};
  ** {"term-label"}: invoked through {{tl|tlb}};
  ** {"accent"}: invoked through {{tl|a}} or the {{para|a}} or {{para|aa}} parameters of other pronunciation templates,
     such as {{tl|IPA}}, {{tl|rhymes}} or {{tl|homophones}};
  ** {"form-of"}: invoked through {{tl|alt form}}, {{tl|standard spelling of}} or other form-of template.
  This changes the display and/or categorization of a minority of labels. (The majority work the same for all modes.)
* `for_doc`: Data is being fetched for documentation purposes. This causes the raw categories returned in
  `categories` to be formatted for documentation display.
* `nocat`: If true, don't add the label to any categories.
* `notrack`: Disable all tracking for this label.
* `already_seen`: An object used to track labels already seen, so they aren't displayed twice. Tracking is according
  to the display form of the label, so if two labels have the same display form, the second one won't be displayed
  (but its categories will still be added). If `already_seen` is {nil}, this tracking doesn't happen.

The return value is an object with the following fields:
* `raw_text`: If specified, the object does not describe a label but simply raw text surrounding labels. This occurs
  when double angle bracket (<<...>>) notation is used. {get_label_info()} does not currently return objects with this
  field set, but {process_raw_labels()} does. The value is {"begin"} (this is the first raw text portion derived from
  a double angle bracket spec, provided there are at least two raw text portions); {"end"} (this is the last raw text
  portion derived from a double angle bracket spec, provided there are at least two portions); {"middle"} (this is
  neither the first nor the last raw text portion); or {"only"} (this is a raw text portion standing by itself). The
  particular value determines the handling of commas and spaces on one or both sides of the raw text. If this field is
  specified, only the `label` field (containing the actual raw text) and the `category` field (containing an empty list)
  are set; all other fields are {nil}.
* `raw_label`: The raw label that was passed in.
* `non_canonical`: The label prior to canonicalization (i.e. alias resolution). Usually this is the same as `raw_label`,
  but if the raw label was preceded by an exclamation point (meaning "display the raw label as-is"), this field will
  contain the label stripped of the exclamation point, and if the raw label is of the form
  `<var>label</var>!<var>display</var>` (meaning "display the label in the specified form"), this field will contain the
  label before the exclamation point.
* `canonical`: If the label in `non_canonical` is an alias, this contains the canonical name of the label; otherwise it
  will be {nil}.
* `override_display`: If specified, this contains a string that overrides the normal display form of the label. The
  display form of a label is the `.display` field of the label data if present, and otherwise is normally the canonical
  form of the label (i.e. after alias resolution). (This is not the same as the formatted form of the label, found in
  `label`, which is the final form shown to the user and includes links to Wikipedia, the glossary, etc. as well as an
  HTML wrapper if the label is deprecated.) If `override_display` is specified, however, this is used in place of the
  normal display form of the label. This currently happens in two circumstances: (1) the label was preceded by ! to
  indicate that the raw label should be displayed rather than the canonical form; (2) the label was given in the form
  `<var>label</var>!<var>display</var>` (meaning "display the label in the specified `<var>display</var>` form").
* `label`: The formatted form of the label. This is what is actually shown to the user. If the label is recognized
  (found in some module), this will typically be in the form of a link.
* `categories`: A list of the categories to add the label to; an empty list of `nocat` was specified.
* `formatted_categories`: A string containing the formatted categories; {nil} if `nocat` or `for_doc` was specified,
  or if `categories` is empty. Currently will be an empty string if there are categories to format but the namespace is
  one that normally excludes categories (e.g. userspace and discussion pages), and `force_cat` isn't specified.
* `deprecated`: True if the label is deprecated.
* `recognized`: If true, the label was found in some module.
* `data`: The data structure for the label, as fetched from the label modules. For unrecognized labels, this will
  be an empty object.
]==]
function export.get_label_info(data)
	if not data.label then
		error("`data` must now be an object containing the params")
	end

	local mode = validate_mode(data.mode)
	local ret = {categories = {}}
	local label = data.label
	local raw_label = label
	ret.raw_label = raw_label
	local override_display
	if label:find("^!") then
		label = label:gsub("^!", "")
		override_display = label
	elseif label:find("![^%s]") then
		label, override_display = label:match("^(.-)!([^%s].*)$")
		if not label then
			error(("Internal error: This Lua pattern should never fail to match for label '%s'"):format(raw_label))
		end
	end
	local non_canonical = label
	ret.non_canonical = non_canonical
	local deprecated = false
	local labdata
	local submodule
	local data_langcode = data.lang and data.lang:getCode() or nil

	local submodules_to_check = export.get_submodules(data.lang)
	for _, submodule_to_check in ipairs(submodules_to_check) do
		submodule = mw.loadData(submodule_to_check)
		local this_labdata = submodule[label]
		local resolved_label
		if type(this_labdata) == "string" then
			resolved_label = this_labdata
			this_labdata = submodule[this_labdata]
			if not this_labdata then
				error(("Internal error: Label alias '%s' points to '%s', which is undefined in module [[%s]]"):format(
					label, resolved_label, submodule_to_check))
			end
			if type(this_labdata) == "string" then
				error(("Internal error: Label alias '%s' points to '%s', which is also an alias (of '%s') in module [[%s]]"):format(
					label, resolved_label, this_labdata, submodule_to_check))
			end
		end
		if this_labdata then
			-- Make sure either there's no lang restriction, or we're processing lang-independent, or our language
			-- is among the listed languages. Otherwise, continue processing (which could conceivably pick up a
			-- lang-appropriate version of the label in another label data module).
			local lablangs = getprop(this_labdata, mode, "langs")
			if not lablangs or not data_langcode then
				labdata = this_labdata
				label = resolved_label or label
				break
			end
			local lang_in_list = false
			for _, langcode in ipairs(lablangs) do
				if langcode == data_langcode then
					lang_in_list = true
					break
				end
			end
			if lang_in_list then
				labdata = this_labdata
				label = resolved_label or label
				break
			elseif not data.notrack then
				-- Track use of a label that fails the lang restriction.
				-- [[Special:WhatLinksHere/Wiktionary:Tracking/labels/wrong-lang-label]]
				-- [[Special:WhatLinksHere/Wiktionary:Tracking/labels/wrong-lang-label/LANGCODE]]
				-- [[Special:WhatLinksHere/Wiktionary:Tracking/labels/wrong-lang-label/LABEL]]
				-- [[Special:WhatLinksHere/Wiktionary:Tracking/labels/wrong-lang-label/LABEL/LANGCODE]]
				track("wrong-lang-label", data_langcode)
				track("wrong-lang-label/" .. label, data_langcode)
				if resolved_label then
					track("wrong-lang-label/" .. resolved_label, data_langcode)
				end
			end
		end
	end
	if labdata then
		ret.recognized = true
	else
		labdata = {}
		ret.recognized = false
	end

	local function labprop(prop)
		return getprop(labdata, mode, prop)
	end
	if labprop("deprecated") then
		deprecated = true
	end
	if label ~= non_canonical then
		-- Note that this is an alias and store the canonical version.
		ret.canonical = label
	end

	if not data.notrack then -- labprop("track") then -- track all labels now
		-- Track label (after converting aliases to canonical form; but also track raw label (alias) if different
		-- from canonical label).
		-- [[Special:WhatLinksHere/Wiktionary:Tracking/labels/label/LABEL]]
		-- [[Special:WhatLinksHere/Wiktionary:Tracking/labels/label/LABEL/LANGCODE]]
		-- [[Special:WhatLinksHere/Wiktionary:Tracking/labels/label/LABEL/MODE]]
		track("label/" .. label, data_langcode, mode)
		if label ~= non_canonical then
			track("label/" .. non_canonical, data_langcode, mode)
		end
	end

	local formatted_label
	formatted_label, deprecated = export.format_label(label, labdata, data.lang, deprecated, override_display, mode)
	ret.deprecated = deprecated
	if deprecated then
		if not data.nocat then
			local depcat = "Entries with deprecated labels"
			if data.for_doc then
				depcat = "<code>" .. depcat .. "</code>"
			end
			table.insert(ret.categories, depcat)
		end
	end

	local label_for_already_seen =
		(labprop("topical_categories") or labprop("regional_categories")
		or labprop("plain_categories") or labprop("pos_categories")
		or labprop("sense_categories")) and formatted_label
		or nil

	-- Track label text. If label text was previously used, don't show it, but include the categories.
	-- For an example, see [[hypocretin]].
	if data.already_seen and data.already_seen[label_for_already_seen] then
		ret.label = ""
	else
		if formatted_label:find("{") then
			formatted_label = mw.getCurrentFrame():preprocess(formatted_label)
		end
		ret.label = formatted_label
	end

	if data.nocat then
		-- do nothing
	else
		local cats = export.fetch_categories(label, labdata, data.lang, mode, data.for_doc)
		for _, cat in ipairs(cats) do
			table.insert(ret.categories, cat)
		end
		if not ret.categories[1] or data.for_doc then
			-- Don't try to format categories if we're doing this for documentation ({{label/doc}}), because there
			-- will be HTML in the categories.
			-- do nothing
		else
			ret.formatted_categories = require(utilities_module).format_categories(ret.categories, data.lang,
				data.sort, nil, force_cat)
		end
	end

	ret.data = labdata

	if label_for_already_seen and data.already_seen then
		data.already_seen[label_for_already_seen] = true
	end

	return ret
end

--[==[
Split a string containing comma-separated raw labels into the individual labels. This will not split on a comma
followed by whitespace, and it will not split inside of matched <...> or [...]. The code is written to be efficient, so
that it does not load modules (e.g. [[Module:parse utilities]]) unnecessarily.
]==]
function export.split_labels_on_comma(term)
	if term:find("[%[<]") then
		-- Do it the "hard way". We don't want to split anything inside of <...> or <<...>> even if there are commas
		-- inside of the angle brackets. For good measure we do the same for [...] and [[...]]. We first parse balanced
		-- segment runs involving either [...] or <...>. Then we split alternating runs on comma (but not on
		-- comma+whitespace). Then we rejoin the split runs. For example, given the following:
		-- "regional,older <<non-rhotic,and,non-hoarse-horse>> speakers", the first call to
		-- parse_multi_delimiter_balanced_segment_run() produces
		--
		-- {"regional,older ", "<<non-rhotic,and,non-hoarse-horse>>", " speakers"}
		--
		-- After calling split_alternating_runs_on_comma(), we get the following:
		--
		-- {{"regional"}, {"older ", "<<non-rhotic,and,non-hoarse-horse>>", " speakers"}}
		--
		-- After rejoining each group, we get:
		--
		-- {"regional", "older <<non-rhotic,and,non-hoarse-horse>> speakers"}
		--
		-- which is the desired output. When processing the second "label" string, the code in process_raw_labels()
		-- will do a similar process to this to pull out the labels inside of the <<...>> notation.
		local put = require(parse_utilities_module)
		local segments = put.parse_multi_delimiter_balanced_segment_run(term, {{"<", ">"}, {"[", "]"}})
		-- This won't split on comma+whitespace.
		local comma_separated_groups = put.split_alternating_runs_on_comma(segments)
		for i, group in ipairs(comma_separated_groups) do
			comma_separated_groups[i] = table.concat(group)
		end
		return comma_separated_groups
	elseif term:find(",%s") then
		-- This won't split on comma+whitespace.
		return require(parse_utilities_module).split_on_comma(term)
	elseif term:find(",") then
		return require(string_utilities_module).split(term, ",")
	else
		return {term}
	end
end

--[==[
Return a list of objects corresponding to a set of raw labels. Each object returned is of the format returned by
{get_label_info()}. This is similar to looping over the labels and calling {get_label_info()} on each one, but it also
correctly handles embedded double angle bracket specs <<...>> found in the labels. (In such a case, there will be more
objects returned than raw labels passed in.) On input, `data` is an object with the following fields:
* `labels`: The list of labels to process.
* `lang`: The language of the labels. Must be specified.
* `mode`: How the label was invoked; see {get_label_info()} for more information.
* `nocat`: If true, don't add the label to any categories.
* `notrack`: Disable all tracking for this label.
* `sort`: Sort key for categorization.
* `already_seen`: An object used to track labels already seen, so they aren't displayed twice. Tracking is according
  to the display form of the label, so if two labels have the same display form, the second one won't be displayed
  (but its categories will still be added). If `already_seen` is {nil}, this tracking doesn't happen.

'''WARNING''': This destructively modifies the `data` structure.
]==]
function export.process_raw_labels(data)
	local label_infos = {}

	local function get_info_and_insert(label)
		-- Reuse this structure to save memory.
		data.label = label
		table.insert(label_infos, export.get_label_info(data))
	end

	for _, label in ipairs(data.labels) do
		if label:find("<<") then
			local segments = require(string_utilities_module).split(label, "<<(.-)>>")
			for i, segment in ipairs(segments) do
				if i % 2 == 1 then
					local raw_text_type = i == 1 and "begin" or i == #segments and "end" or "middle"
					table.insert(label_infos, {raw_text = raw_text_type, label = segment, categories = {}})
				else
					local segment_labels = export.split_labels_on_comma(segment)
					for _, segment_label in ipairs(segment_labels) do
						get_info_and_insert(segment_label)
					end
				end
			end
		else
			get_info_and_insert(label)
		end
	end

	return label_infos
end

--[==[
Split a comma-separated string of raw labels and process each label to get a list of objects suitable for passing to
{format_processed_labels()}. Each object returned is of the format returned by {get_label_info()}. This is equivalent to
calling {split_labels_on_comma()} followed by {process_raw_labels()}. On input, `data` is an object with the following
fields:
* `labels`: The string containing the raw comma-separated labels.
* `lang`: The language of the labels. Must be specified.
* `mode`: How the label was invoked; see {get_label_info()} for more information.
* `nocat`: If true, don't add the label to any categories.
* `notrack`: Disable all tracking for this label.
* `sort`: Sort key for categorization.
* `already_seen`: An object used to track labels already seen, so they aren't displayed twice. Tracking is according
  to the display form of the label, so if two labels have the same display form, the second one won't be displayed
  (but its categories will still be added). If `already_seen` is {nil}, this tracking doesn't happen.

'''WARNING''': This destructively modifies the `data` structure.
]==]
function export.split_and_process_raw_labels(data)
	data.labels = export.split_labels_on_comma(data.labels)
	return export.process_raw_labels(data)
end

--[==[
Format one or more already-processed labels for display and categorization. "Already-processed" means that
{get_label_info()} or {process_raw_labels()} has been called on the raw labels to convert them into objects containing
information on how to display and categorize the labels. This is a lower-level alternative to {show_labels()} and is
meant for modules such as [[Module:alternative forms]], [[Module:quote]] and [[Module:etymology/templates/descendant]]
that support displaying labels along with some other information.

On input `data` is an object with the following fields:
* `labels`: List of the label objects to format, in the format returned by {get_label_info()}.
* `lang`: The language of the labels.
* `mode`: How the label was invoked; see {get_label_info()} for more information.
* `sort`: Sort key for categorization.
* `already_seen`: An object used to track labels already seen, so they aren't displayed twice, as documented in
  {get_label_info()}. To enable this, set this to an empty object. If `already_seen` is {nil}, this tracking doesn't
  happen, meaning if the same label appears twice, it will be displayed twice.
* `open`: Open bracket or parenthesis to display before the concatenated labels. If specified, it is wrapped in the
  {"ib-brac"} CSS class. If {nil}, no open bracket is displayed.
* `close`: Close bracket or parenthesis to display after the concatenated labels. If specified, it is wrapped in the
  {"ib-brac"} CSS class. If {nil}, no close bracket is displayed.
* `no_ib_content`: By default, the concatenated formatted labels inside of the open/close brackets are wrapped in the
  {"ib-content"} CSS class. Specify this to suppress this wrapping.

Return value is a string containing the contenated labels, optionally surrounded by open/close brackets or parentheses.
Normally, labels are separated by comma-space sequences, but this may be suppressed for certain labels. If `nocat`
wasn't given to {get_label_info() or process_raw_labels()}, the label objects will contain formatted categories in
them, which will be inserted into the returned text. The concatenated text inside of the open/close brackets is normally
wrapped in the {"ib-content"} CSS class, but this can be suppressed, as mentioned above.

'''WARNING''': This destructively modifies the `data` structure.
]==]
function export.format_processed_labels(data)
	if not data.labels then
		error("`data` must now be an object containing the params")
	end
	local labels = data.labels
	if not labels[1] then
		error("You must specify at least one label.")
	end

	-- Show the labels
	local omit_preComma = false
	local omit_postComma = true
	local omit_preSpace = false
	local omit_postSpace = true

	for _, label in ipairs(labels) do
		omit_preComma = omit_postComma
		omit_preSpace = omit_postSpace

		local raw_text_omit_before = label.raw_text == "middle" or label.raw_text == "end"
		local raw_text_omit_after = label.raw_text == "middle" or label.raw_text == "begin"
		label.omit_comma = omit_preComma or (label.data and label.data.omit_preComma) or raw_text_omit_before
		omit_postComma = (label.data and label.data.omit_postComma) or raw_text_omit_after
		label.omit_space = omit_preSpace or (label.data and label.data.omit_preSpace) or raw_text_omit_before
		omit_postSpace = (label.data and label.data.omit_postSpace) or raw_text_omit_after
	end

	if data.lang then
		local lang_functions_module = export.lang_specific_data_modules_prefix .. data.lang:getCode() .. "/functions"
		local m_lang_functions = require(utilities_module).safe_require(lang_functions_module)
		if m_lang_functions and m_lang_functions.postprocess_handlers then
			for _, handler in ipairs(m_lang_functions.postprocess_handlers) do
				handler(data)
			end
		end
	end

	for i, labelinfo in ipairs(labels) do
		local label
		-- Need to check for 'not raw_text' here because blank labels may legitimately occur as raw text if a double
		-- angle bracket spec occurs at the beginning of a label. In this case we've already taken into account the
		-- context and don't want to leave out a preceding comma and space e.g. in a case like
		-- {{lb|en|rare|<<dialect>> or <<eye dialect>>}}. FIXME: We should reconsider whether we need this special case
		-- at all.
		if labelinfo.label == "" and not labelinfo.raw_text then
			label = ""
		else
			label = (labelinfo.omit_comma and "" or '<span class="ib-comma">,</span>') ..
					(labelinfo.omit_space and "" or "&#32;") ..
					labelinfo.label
		end
		labels[i] = label .. (labelinfo.formatted_categories or "")
	end

	local function wrap_open_close(val)
		if val then
			return "<span class=\"ib-brac\">" .. val .. "</span>"
		else
			return ""
		end
	end

	local concatenated_labels = table.concat(labels, "")
	if not data.no_ib_content then
		concatenated_labels = "<span class=\"ib-content\">" .. concatenated_labels .. "</span>"
	end

	return wrap_open_close(data.open) .. concatenated_labels .. wrap_open_close(data.close)
end

--[==[
Format one or more labels for display and categorization. This provides the implementation of the
{{tl|label}}/{{tl|lb}}, {{tl|term label}}/{{tl|tlb}} and {{tl|accent}}/{{tl|a}} templates, and can also be called from a
module. The return value is a string to be inserted into the generated page, including the display and categories. On
input `data` is an object with the following fields:
* `labels`: List of the labels to format.
* `lang`: The language of the labels.
* `mode`: How the label was invoked; see {get_label_info()} for more information.
* `nocat`: If true, don't add the labels to any categories.
* `notrack`: Disable all tracking for these labels.
* `sort`: Sort key for categorization.
* `no_track_already_seen`: Don't track already-seen labels. If not specified, already-seen labels are not displayed
  again, but still categorize. See the documentation of {get_label_info()}.
* `open`: Open bracket or parenthesis to display before the concatenated labels. If {nil}, defaults to an open
  parenthesis. Set to {false} to disable.
* `close`: Close bracket or parenthesis to display after the concatenated labels. If {nil}, defaults to a close
  parenthesis. Set to {false} to disable.

Compared with {format_processed_labels()}, this function has the following differences:
# The labels specified in `labels` are raw labels (i.e. strings) rather than formatted objects.
# The open and close brackets default to parentheses ("round brackets") rather than not being displayed by default.
# Tracking of already-seen labels is enabled unless explicitly turned off using `no_track_already_seen`.
# The entire formatted result is wrapped in a {"usage-label-<var>type</var>"} CSS class (depending on the value of
  `mode`).

'''WARNING''': This destructively modifies the `data` structure.
]==]
function export.show_labels(data)
	if not data.labels then
		error("`data` must now be an object containing the params")
	end
	local labels = data.labels
	if not labels[1] then
		error("You must specify at least one label.")
	end

	local mode = validate_mode(data.mode)

	if not data.no_track_already_seen then
		data.already_seen = {}
	end

	data.labels = export.process_raw_labels(data)
	if data.open == nil then
		data.open = "("
	end
	if data.close == nil then
		data.close = ")"
	end
	local formatted = export.format_processed_labels(data)
	return "<span class=\"" .. mode_to_outer_class[mode] .. "\">" .. formatted .. "</span>"
end

--[==[Helper function for the data modules.]==]
function export.alias(labels, key, aliases)
	require(table_module).alias(labels, key, aliases)
end

--[==[
Split the display form of a label. Returns two values: `link` and `display`. If the display form consists of a
two-part link, `link` is the first part and `display` is the second part. If the display form consists of a
single-part link, `link` and `display` are the same. Otherwise (the display form is not a link or contains an
embedded link), `link` is the same as the passed-in `label` and `display` is nil.
]==]
function export.split_display_form(label)
	if not label:find("%[%[") then
		return label, nil
	end
	local link, display = label:match("^%[%[([^%[%]|]+)|([^%[%]|]+)%]%]$")
	if link then
		return link, display
	end
	local link = label:match("^%[%[([^%[%]|])+%]%]$")
	if link then
		return link, link
	end
	return label, nil
end

--[==[
Combine the `link` and `display` parts of the display form of a label as returned by {split_display_form()}.
If `display` is nil, `link` is returned directly. Otherwise, a one-part or two-part link is constructed
depending on whether `link` and `display` are the same. (As a special case, if both consist of a blank string,
the return value is a blank string rather than a malformed link.)
]==]
function export.combine_display_form_parts(link, display)
	if not display then
		return link
	end
	if link == display then
		if link == "" then
			return ""
		else
			return ("[[%s]]"):format(link)
		end
	end
	return ("[[%s|%s]]"):format(link, display)
end

--[==[Used to finalize the data into the form that is actually returned.]==]
function export.finalize_data(labels)
	local shallowcopy = require(table_module).shallowcopy
	local aliases = {}
	for label, data in pairs(labels) do
		if type(data) == "table" then
			if data.aliases then
				for _, alias in ipairs(data.aliases) do
					aliases[alias] = label
				end
				data.aliases = nil
			end
			if data.deprecated_aliases then
				local data2 = shallowcopy(data)
				data2.deprecated = true
				data2.canonical = label
				for _, alias in ipairs(data2.deprecated_aliases) do
					aliases[alias] = data2
				end
				data.deprecated_aliases = nil
				data2.deprecated_aliases = nil
			end
		end
	end
	for label, data in pairs(aliases) do
		labels[label] = data
	end
	return labels
end

return export