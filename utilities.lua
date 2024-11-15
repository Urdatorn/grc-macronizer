local mw = mw
local package = package
local table = table

local anchor_encode = mw.uri.anchorEncode
local concat = table.concat
local decode_entities -- Assigned when needed.
local format = string.format
local get_by_code -- Assigned when needed.
local insert = table.insert
local ipairs = ipairs
local remove_links -- Assigned when needed.
local require = require
local tonumber = tonumber
local trim -- Assigned when needed.
local type = type
local unstrip = mw.text.unstrip

local export = {}

do
	local loaded = package.loaded
	local loader = package.searchers[2]

	--[==[
	Like require, but return false if a module does not exist instead of throwing an error.
	Outputs are cached in {package.loaded}, which is faster for all module types, but much faster for nonexistent modules since require will attempt to use the full loader each time (since they don't get cached in {package.loaded}).
	]==]
	function export.safe_require(modname)
		local module = loaded[modname]
		if module ~= nil then
			return module
		end
		-- The loader returns a function if the module exists, or nil if it doesn't, and checking this is faster than using pcall with require. If found, we still use require instead of loading and caching directly, because require contains safety checks against infinite loading loops (and we do want those to throw an error).
		module = loader(modname)
		if module then
			return require(modname)
		end
		loaded[modname] = false
		return false
	end
end

--[==[
Convert decimal to hexadecimal.

Note: About three times as fast as the hex library.
]==]
function export.dec_to_hex(dec)
	dec = tonumber(dec)
	if dec == nil or dec % 1 ~= 0 then
		error("Input should be a decimal integer.")
	end
	return format("%X", dec)
end

--[==[
A helper function to strip wiki markup, giving the plaintext of what is displayed on the page.
]==]
function export.get_plaintext(text)
	text = text
		:gsub("%[%[", "\1")
		:gsub("%]%]", "\2")

	-- Remove strip markers and HTML tags.
	text = unstrip(text):gsub("<[^<>\1\2]+>", "")

	-- Parse internal links for the display text, and remove categories.
	if remove_links == nil then
		remove_links = require("links").remove_links
	end
	text = remove_links(text)

	-- Remove files.
	for _, falsePositive in ipairs({"File", "Image"}) do
		text = text:gsub("\1" .. falsePositive .. ":[^\1\2]+\2", "")
	end

	-- Parse external links for the display text.
	text = text:gsub("%[(https?://[^%[%]]+)%]",
		function(capture)
			return capture:match("https?://[^%s%]]+%s([^%]]+)") or ""
		end)
		-- Any remaining square brackets aren't involved in links, but must be escaped to avoid creating new links.
		:gsub("\1", "&#91;&#91;")
		:gsub("\2", "&#93;&#93;")
		:gsub("%[", "&#91;")
		:gsub("]", "&#93;")
		-- Strip bold, italics and soft hyphens.
		:gsub("('*)'''(.-'*)'''", "%1%2")
		:gsub("('*)''(.-'*)''", "%1%2")
		:gsub("­", "")

	if decode_entities == nil then
		local m_str_utils = require("Module:string utilities")
		decode_entities = m_str_utils.decode_entities
		trim = m_str_utils.trim
	end
	
	-- Get any HTML entities and trim.
	-- Note: don't decode URL percent encoding, as it shouldn't be used in display text and may cause problems if % is used.
	return trim(decode_entities(text))
end

do
	local title_obj, category_namespaces, page_data, pagename, pagename_defaultsort
	--[==[
	Format the categories with the appropriate sort key.
	* `categories` is a list of categories. Each entry in the list can be either a string (the full category, minus
	  the {"Category:"} prefix) or an object. In the latter case, the object should have fields
	  ** `cat`: the full category, minus the {"Category:"} prefix (required);
	  ** `lang`: optional language object to override the overall `lang`;
	  ** `sort_key`: optional sort key to override the overall `sort_key`;
	  ** `sort_base`: optional sort base to override the overall `sort_base`;
	  ** `sc`: optional script object to override the overall `sc`.
	* `lang` is an object encapsulating a language; if {nil}, the object for language code {"und"} (undetermined) will
	  be used. `lang` is used when computing the sort key (either from the subpage name or sort base).
	* `sort_key` is placed in the category invocation, and indicates how the page will sort in the respective category.
	  Normally '''do not use this'''. Instead, leave it {nil}, and if you need to a control the sort order, use
	  {sort_base}, so that language-specific normalization is applied on top of the specified sort base. If neither
	  {sort_key} nor {sort_base} is specified, the default is to apply language-specific normalization to the subpage
	  name; see below.
	* `sort_base` lets you override the default sort key while still maintaining appropriate language-specific
	  normalization. If {nil} is specified, this defaults to the subpage name, which is the portion of the full pagename
	  after subtracting the namespace prefix (and, in certain namespaces such as {User:}, but notably not in the
	  mainspace, after subtracting anything up through the final slash). The actual sort key is derived from the sort
	  base approximately by lowercasing, applying language-specific normalization and then uppercasing; note that the
	  same process is applied in deriving the sort key when no sort base is specified. For example, for French, Spanish,
	  etc. the normalization process maps accented letters to their unaccented equivalents, so that e.g. in French,
	  {{m|fr|ça}} sorts after {{m|fr|ca}} (instead of after the default Wikimedia sort order, which is approximately
	  based on Unicode sort order and places ç after z) and {{m|fr|côté}} sorts after {{m|fr|coté}} (instead of between
	  c and d). Similarly, in Russian the normalization process converts Cyrillic ё to a string consisting of Cyrillic е
	  followed by U+10FFFF, so that effectively ё sorts after е instead of the default Wikimedia sort, which (I think)
	  puts ё after я, the last letter of the Cyrillic alphabet.
	* `force_output` forces normal output in all namespaces. Normally, nothing is output if the page isn't in the main,
	  Appendix:, Thesaurus:, Reconstruction: or Citations: namespaces.
	* `sc` is a script object; if nil, the default will be derived from the sort base (or its default value, the
	  subpage name) by calling {lang:findBestScript()}. The value of `sc` is used during the sort base normalization
	  process; for example, languages with multiple scripts will often have script-specific normalization processes.
	]==]
	function export.format_categories(categories, lang, sort_key, sort_base, force_output, sc)
		if type(lang) == "table" and not lang.getCode then
			error("The second argument to format_categories should be a language object.")
		end

		title_obj = title_obj or mw.title.getCurrentTitle()
		category_namespaces = category_namespaces or mw.loadData("Module:utilities/data").category_namespaces

		if not (
			force_output or
			category_namespaces[title_obj.namespace] or
			title_obj.prefixedText == "Wiktionary:Sandbox"
		) then
			return ""
		elseif not page_data then
			page_data = mw.loadData("Module:headword/data").page
			pagename = page_data.encoded_pagename
			pagename_defaultsort = page_data.pagename_defaultsort
		end

		local extra_categories
		local function generate_sort_key(lang, sort_key, sort_base, sc)
			-- Generate a default sort key.
			-- If the sort key is "-", bypass the process of generating a sort key altogether. This is desirable when categorising (e.g.) translation requests, as the pages to be categorised are always in English/Translingual.
			if sort_key == "-" then
				sort_key = sort_base and sort_base:uupper() or pagename_defaultsort
			else
				if not lang then
					if get_by_code == nil then
						get_by_code = require("languages").getByCode
					end
					lang = get_by_code("und")
				end
				sort_base = lang:makeSortKey(sort_base or pagename, sc) or pagename_defaultsort
				if not sort_key or sort_key == "" then
					sort_key = sort_base
				elseif lang:getCode() ~= "und" then
					if not extra_categories then
						extra_categories = {}
					end
					insert(extra_categories, lang:getFullName() .. " terms with " .. (
						sort_key:uupper() == sort_base and "redundant" or
						"non-redundant non-automated"
					) .. " sortkeys")
				end
			end
			if not sort_key or sort_key == "" then
				sort_key = pagename_defaultsort
			end
			return sort_key
		end

		local ret = {}
		local default_sort_key = generate_sort_key(lang, sort_key, sort_base, sc)
		local ins_point = 0
		local function process_category(cat)
			local this_sort_key
			if type(cat) == "string" then
				this_sort_key = default_sort_key
			else
				this_sort_key = generate_sort_key(cat.lang or lang, cat.sort_key or sort_key,
					cat.sort_base or sort_base, cat.sc or sc)
				cat = cat.cat
			end
			ins_point = ins_point + 1
			ret[ins_point] = "[[Category:" .. cat .. "|" .. this_sort_key .. "]]"
		end

		for _, cat in ipairs(categories) do
			process_category(cat)
		end
		if extra_categories then
			for _, cat in ipairs(extra_categories) do
				process_category(cat)
			end
		end

		return concat(ret)
	end
end

do
	local catfix_scripts

	--[==[
	Add a "catfix", which is used on language-specific category pages to add language attributes and often script
	classes to all entry names. The addition of language attributes and script classes makes the entry names display
	better (using the language- or script-specific styles specified in [[MediaWiki:Common.css]]), which is particularly
	important for non-English languages that do not have consistent font support in browsers.

	Language attributes are added for all languages, but script classes are only added for languages with one script
	listed in their data file, or for languages that have a default script listed in the {catfix_script} list in
	[[Module:utilities/data]]. Some languages clearly have a default script, but still have other scripts listed in
	their data file and therefore need their default script to be specified. Others do not have a default script.

	* Serbo-Croatian is regularly written in both the Latin and Cyrillic scripts. Because it uses two scripts,
	  Serbo-Croatian cannot have a script class applied to entries in its category pages, as only one script class
	  can be specified at a time.
	* Russian is usually written in the Cyrillic script ({{cd|Cyrl}}), but Braille ({{cd|Brai}}) is also listed in
	  its data file. So Russian needs an entry in the {catfix_script} list, so that the {{cd|Cyrl}} (Cyrillic) script
	  class will be applied to entries in its category pages.

	To find the scripts listed for a language, go to [[Module:languages]] and use the search box to find the data file
	for the language. To find out what a script code means, search the script code in [[Module:scripts/data]].
	]==]
	function export.catfix(lang, sc)
		if not lang or not lang.getCanonicalName then
			error('The first argument to the function "catfix" should be a language object from [[Module:languages]] or [[Module:etymology languages]].')
		end
		if sc and not sc.getCode then
			error('The second argument to the function "catfix" should be a script object from [[Module:scripts]].')
		end
		local canonicalName = lang:getCanonicalName()
		local fullName = lang:getFullName()

		-- To add script classes to links on pages created by category boilerplate templates.
		if not sc then
			catfix_scripts = catfix_scripts or mw.loadData("Module:utilities/data").catfix_scripts
			sc = catfix_scripts[lang:getCode()] or catfix_scripts[lang:getFullCode()]
			if sc then
				sc = require("scripts.lua").getByCode(sc)
			end
		end

		local catfix_class = anchor_encode("CATFIX-" .. canonicalName)
		if fullName ~= canonicalName then
			catfix_class = catfix_class .. " " .. anchor_encode("CATFIX-" .. fullName)
		end
		return "<span id=\"catfix\" style=\"display:none;\" class=\"" .. catfix_class .. "\">" ..
			require("Module:script utilities").tag_text("&nbsp;", lang, sc, nil) ..
			"</span>"
	end
end

--[==[
Given a type (as a string) and an arbitrary number of entities, checks whether all of those entities are language,
family, script, writing system or Wikimedia language objects. Useful for error handling in functions that require
one of these kinds of object.

If `noErr` is set, the function returns false instead of throwing an error, which allows customised error handling to
be done in the calling function.
]==]
function export.check_object(typ, noErr, ...)
	local function fail(message)
		if noErr then
			return false
		else
			error(message, 3)
		end
	end

	local objs = {...}
	if #objs == 0 then
		return fail("Must provide at least one object to check.")
	end
	for _, obj in ipairs(objs) do
		if type(obj) ~= "table" or type(obj.hasType) ~= "function" then
			return fail("Function expected a " .. typ .. " object, but received a " .. type(obj) .. " instead.")
		elseif not (typ == "object" or obj:hasType(typ)) then
			for _, wrong_type in ipairs{"family", "language", "script", "Wikimedia language", "writing system"} do
				if obj:hasType(wrong_type) then
					return fail("Function expected a " .. typ .. " object, but received a " .. wrong_type .. " object instead.")
				end
			end
			return fail("Function expected a " .. typ .. " object, but received another type of object instead.")
		end
	end
	return true
end

return export