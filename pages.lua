local export = {}

local string_utilities_module = "Module:string utilities"

local find = string.find
local format = string.format
local get_current_section -- Defined below.
local gsub = string.gsub
local is_valid_title -- Defined below.
local lower = string.lower
local match = string.match
local new_title = mw.title.new
local require = require
local sub = string.sub
local tonumber = tonumber
local type = type
local unstrip_nowiki = mw.text.unstripNoWiki

-- Functions in other modules that load locally on demand by dereferencing themselves.
local function decode_entities(...)
	decode_entities = require(string_utilities_module).decode_entities
	return decode_entities(...)
end

local function trim(...)
	trim = require(string_utilities_module).trim
	return trim(...)
end

--[==[
Returns true if the title object is a valid title that is not an interwiki link.]==]
function export.is_valid_title(title)
	-- Note: Mainspace titles starting with "#" should be invalid, but a bug in mw.title.new and mw.title.makeTitle means a title object is returned that has the empty string for prefixedText, so they need to be filtered out.
	return title and #title.prefixedText > 0 and #title.interwiki == 0
end
is_valid_title = export.is_valid_title

--[==[
Returns true if `pagename` is a valid page title that is not an interwiki link.]==]
function export.is_valid_page_name(pagename)
	return is_valid_title(new_title(pagename))
end

do
	-- Any template/module with "sandbox" in the title. These are impossible
	-- to screen for more accurately, as there's no consistent pattern. Also
	-- any user sandboxes in the form (e.g.) "Template:User:...".
	local function is_sandbox(text)
		return (find(lower(text), "sandbox", 1, true) or sub(text, 1, 5) == "User:") and true or false
	end
	
	-- Any template/module documentation pages.
	local function is_documentation(text)
		return match(text, "./documentation$") and true or false
	end
	
	-- Any template/module testcases (which can be labelled and/or followed by
	-- further subpages).
	local function is_testcase_page(text)
		return match(text, "./[Tt]estcases?%f[%L]") and true or false
	end
	
	--[==[
	Returns the page type of `title` in a format which can be used in running text.]==]
	function export.pagetype(title)
		if not is_valid_title(title) then
			error(mw.dumpObject(title.fullText) .. " is not a valid page name.")
		end
		-- Content models have overriding priority, as they can appear in
		-- nonstandard places due to page content model changes.
		local content_model = title.contentModel
		if content_model == "css" or content_model == "sanitized-css" then
			return "stylesheet"
		elseif content_model == "javascript" then
			return "script"
		elseif content_model == "json" then
			return "JSON data page"
		elseif content_model == "MassMessageListContent" then
			return "mass message delivery list"
		-- Modules.
		elseif content_model == "Scribunto" then
			local title_text = title.text
			if is_sandbox(title_text) then
				return "module sandbox"
			elseif is_testcase_page(title_text) then
				return "module testcase page"
			end
			return "module"
		elseif content_model == "text" then
			return "page" -- ???
		-- Otherwise, the content model is "wikitext", so check namespaces.
		elseif title.isTalkPage then
			return "talk page"
		end
		local ns = title.namespace
		-- Main namespace.
		if ns == 0 then
			return "entry"
		-- Wiktionary:
		elseif ns == 4 then
			return "project page"
		-- MediaWiki: and TimedText:
		elseif ns == 8 or ns == 710 then
			return title.nsText .. " page"
		elseif ns == 10 then
			local title_text = title.text
			if is_sandbox(title_text) then
				return "template sandbox"
			elseif is_documentation(title_text) then
				return "template documentation page"
			elseif is_testcase_page(title_text) then
				return "template testcase page"
			end
			return "template"
		-- Any non-Scribunto pages in the Module: space (which will almost
		-- always be documentation subpages). Any remaining will get default
		-- handling as "module pages".
		elseif ns == 828 then
			local title_text = title.text
			if is_sandbox(title_text) then
				return "module sandbox"
			elseif is_documentation(title_text) then
				return "module documentation page"
			end
		end
		local ns_text = lower(title.nsText)
		-- Category: and Appendix:
		if ns == 14 or ns == 100 then
			return ns_text
		-- Thesaurus: and Reconstruction:
		elseif ns == 110 or ns == 118 then
			return ns_text .. " entry"
		end
		return gsub(ns_text, "_", " ") .. " page"
	end
end

do
	local function check_level(lvl)
		if type(lvl) ~= "number" then
			error("Heading levels must be numbers.")
		elseif lvl < 1 or lvl > 6 or lvl % 1 ~= 0 then
			error("Heading levels must be integers between 1 and 6.")
		end
		return lvl
	end

	--[==[
	A helper function which iterates over the headings in `text`, which should be the content of a page or (main) section.

	Each iteration returns three values: `sec` (the section title), `lvl` (the section level) and `loc` (the index of the section in the given text, from the first equals sign). The section title will be automatically trimmed, and any HTML entities will be resolved.
	The optional parameter `a` (which should be an integer between 1 and 6) can be used to ensure that only headings of the specified level are iterated over. If `b` is also given, then they are treated as a range.
	The optional parameters `a` and `b` can be used to specify a range, so that only headings with levels in that range are returned. If only `a` is given ...
	]==]
	local function find_headings(text, a, b)
		a = a and check_level(a) or nil
		b = b and check_level(b) or a or nil
		local start, loc, lvl, sec = 1

		return function()
			repeat
				loc, lvl, sec, start = match(text, "()%f[^%z\n](==?=?=?=?=?)([^\n]+)%2[\t ]*%f[%z\n]()", start)
				lvl = lvl and #lvl
			until not (sec and a) or (lvl >= a and lvl <= b)
			return sec and trim(decode_entities(sec)) or nil, lvl, loc
		end
	end

	local function _get_section(content, name, level)
		if not (content and name) then
			return nil
		elseif find(name, "\n", 1, true) then
			error("Heading name cannot contain a newline.")
		end
		level = level and check_level(level) or nil
		name = trim(decode_entities(name))
		local start
		for sec, lvl, loc in find_headings(content, level and 1 or nil, level) do
			if start and lvl <= level then
				return sub(content, start, loc - 1)
			elseif not start and (not level or lvl == level) and sec == name then
				start, level = loc, lvl
			end
		end
		return start and sub(content, start)
	end

	--[==[
	A helper function to return the content of a page section.

	`content` is raw wikitext, `name` is the requested section, and `level` is an optional parameter that specifies
	the required section heading level. If `level` is not supplied, then the first section called `name` is returned.
	`name` can either be a string or table of section names. If a table, each name represents a section that has the
	next as a subsection. For example, { {"Spanish", "Noun"}} will return the first matching section called "Noun"
	under a section called "Spanish". These do not have to be at adjacent levels ("Noun" might be L4, while "Spanish"
	is L2). If `level` is given, it refers to the last name in the table (i.e. the name of the section to be returned).

	The returned section includes all of its subsections. If no matching section is found, return {nil}.
	]==]
	function export.get_section(content, names, level)
		if type(names) ~= "table" then
			return _get_section(content, names, level)
		end
		local i = 1
		local name = names[i]
		if not name then
			error("Must specify at least 1 section.")
		end
		while true do
			local nxt_i = i + 1
			local nxt = names[nxt_i]
			if nxt == nil then
				return _get_section(content, name, level)
			end
			content = _get_section(content, name)
			if content == nil then
				return nil
			elseif i == 6 then
				error("Not possible specify more than 6 sections: headings only go up to level 6.")
			end
			i = nxt_i
			name = names[i]
		end
		return content
	end
end

do
	local current_section
	--[==[
	A function which returns the number of the page section which contains the current {#invoke}.
	]==]
	function export.get_current_section()
		if current_section then
			return current_section
		end
		local frame = mw.getCurrentFrame()
		local extension_tag = frame.extensionTag
		-- We determine the section via the heading strip marker count, since they're numbered sequentially, but the only way to do this is to generate a fake heading via frame:preprocess(). The native parser assigns each heading a unique marker, but frame:preprocess() will return copies of older markers if the heading is identical to one further up the page, so the fake heading has to be unique to the page. The best way to do this is to feed it a heading containing a nowiki marker (which we will need later), since those are always unique.
		local nowiki_marker = extension_tag(frame, "nowiki")
		-- Note: heading strip markers have a different syntax to the ones used for tags.
		local h = tonumber(match(
			frame:preprocess("=" .. nowiki_marker .. "="),
			"\127'\"`UNIQ%-%-h%-(%d+)%-%-QINU`\"'\127"
		))
		-- For some reason, [[Special:ExpandTemplates]] doesn't generate a heading strip marker, so if that happens we simply abort early.
		if not h then
			return 0
		end
		-- The only way to get the section number is to increment the heading count, so we store the offset in nowiki strip markers which can be retrieved by procedurally unstripping nowiki markers, counting backwards until we find a match.
		local n, offset = tonumber(match(
			nowiki_marker,
			"\127'\"`UNIQ%-%-nowiki%-([%dA-F]+)%-QINU`\"'\127"
		), 16)
		while not offset and n > 0 do
			n = n - 1
			offset = match(
				unstrip_nowiki(format("\127'\"`UNIQ--nowiki-%08X-QINU`\"'\127", n)),
				"^HEADING\1(%d+)" -- Prefix "HEADING\1" prevents collisions.
			)
		end
		offset = offset and (offset + 1) or 0
		extension_tag(frame, "nowiki", "HEADING\1" .. offset)
		current_section = h - offset
		return current_section
	end
	get_current_section = export.get_current_section
end

do
	local L2_sections
	--[==[
	A function which returns the name of the L2 language section which contains the current {#invoke}.
	]==]
	function export.get_current_L2()
		local section = get_current_section()
		if section == 0 then
			return
		end
		L2_sections = L2_sections or mw.loadData("Module:headword/data").page.L2_sections
		while section > 0 do
			local L2 = L2_sections[section]
			if L2 then
				return L2
			end
			section = section - 1
		end
	end
end

return export