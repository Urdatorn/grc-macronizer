local m_str_utils = require("string_utilities")

local concat = table.concat
local explode = m_str_utils.explode_utf8
local gsplit = m_str_utils.gsplit
local match = string.match
local select = select
local split = m_str_utils.split
local toNFC = mw.ustring.toNFC
local toNFD = mw.ustring.toNFD
local toNFKC = mw.ustring.toNFKC
local toNFKD = mw.ustring.toNFKD
local type = type
local ugsub = m_str_utils.gsub
local umatch = m_str_utils.match

local export = {}

local Script = {}

--[==[Returns the script code of the script. Example: {{lua|"Cyrl"}} for Cyrillic.]==]
function Script:getCode()
	return self._code
end

--[==[Returns the canonical name of the script. This is the name used to represent that script on Wiktionary. Example: {{lua|"Cyrillic"}} for Cyrillic.]==]
function Script:getCanonicalName()
	return self._rawData[1] or self._rawData.canonicalName
end

--[==[Returns the display form of the script. For scripts, this is the same as the value returned by <code>:getCategoryName("nocap")</code>, i.e. it reads "NAME script" (e.g. {{lua|"Arabic script"}}). The displayed text used in <code>:makeCategoryLink</code> is always the same as the display form.]==]
function Script:getDisplayForm()
	return self:getCategoryName("nocap")
end

function Script:getOtherNames(onlyOtherNames)
	return require("language_like").getOtherNames(self, onlyOtherNames)
end

function Script:getAliases()
	return self._rawData.aliases or {}
end

function Script:getVarieties(flatten)
	return require("language_like").getVarieties(self, flatten)
end

--[==[Returns the {{w|IETF language tag#Syntax of language tags|IETF subtag}} used for the script, which should always be a valid {{w|ISO 15924}} script code. This is used when constructing HTML {{code|html|lang{{=}}}} tags. The {{lua|ietf_subtag}} value from the script's data file is used, if present; otherwise, the script code is used. For script codes which contain a hyphen, only the part after the hyphen is used (e.g. {{lua|"fa-Arab"}} becomes {{lua|"Arab"}}).]==]
function Script:getIETFSubtag()
	local code = self._ietf_subtag
	if code == nil then
		code = self._rawData.ietf_subtag or match(self._code, "[^%-]+$")
		self._ietf_subtag = code
	end
	return code
end

--[==[Returns the parent of the script. Example: {{lua|"Arab"}} for {{lua|"fa-Arab"}}. It returns {{lua|"top"}} for scripts without a parent, like {{lua|"Latn"}}, {{lua|"Grek"}}, etc.]==]
function Script:getParent()
	return self._rawData.parent
end

function Script:getSystemCodes()
	if not self._systemCodes then
		local system_codes = self._rawData[3]
		if type(system_codes) == "table" then
			self._systemCodes = system_codes
		elseif type(system_codes) == "string" then
			self._systemCodes = split(system_codes, "%s*,%s*", true)
		else
			self._systemCodes = {}
		end
	end
	return self._systemCodes
end

function Script:getSystems()
	if not self._systemObjects then
		local m_systems = require("Module:writing systems")
		self._systemObjects = {}
		
		for _, ws in ipairs(self:getSystemCodes()) do
			table.insert(self._systemObjects, m_systems.getByCode(ws))
		end
	end
	
	return self._systemObjects
end

--[==[Check whether the script is of type `system`, which can be a writing system code or object. If multiple systems are passed, return true if the script is any of the specified systems.]==]
function Script:isSystem(...)
	for _, system in ipairs{...} do
		if type(system) == "table" then
			system = system:getCode()
		end
		for _, s in ipairs(self:getSystemCodes()) do
			if system == s then
				return true
			end
		end
	end
	return false
end

--function Script:getAllNames()
--	return self._rawData.names
--end

--[==[Given a list of types as strings, returns true if the script has all of them. 

Currently the only possible type is {script}; use {{lua|hasType("script")}} to determine if an object that
may be a language, family or script is a script.
]==]	
function Script:hasType(...)
	local types = self._types
	if types == nil then
		types = {script = true}
		local rawtypes = self._rawData.type
		if rawtypes then
			for rawtype in gsplit(rawtypes, "%s*,%s*", true) do
				types[rawtype] = true
			end
		end
		self._types = types
	end
	for i = 1, arg.n do
		if not types[arg[i]] then
			return false
		end
	end
	return true
end

--[==[Returns the name of the main category of that script. Example: {{lua|"Cyrillic script"}} for Cyrillic, whose category is at [[:Category:Cyrillic script]].
Unless optional argument <code>nocap</code> is given, the script name at the beginning of the returned value will be capitalized. This capitalization is correct for category names, but not if the script name is lowercase and the returned value of this function is used in the middle of a sentence. (For example, the script with the code <code>Semap</code> has the name <code>"flag semaphore"</code>, which should remain lowercase when used as part of the category name [[:Category:Translingual letters in flag semaphore]] but should be capitalized in [[:Category:Flag semaphore templates]].) If you are considering using <code>getCategoryName("nocap")</code>, use <code>getDisplayForm()</code> instead.]==]
function Script:getCategoryName(nocap)
	local name = self:getCanonicalName()
	
	-- If the name already has "script", "code" or "semaphore" at the end, don't add it.
	if not (
		name:find("[ %-][Ss]cript$") or
		name:find("[ %-][Cc]ode$") or
		name:find("[ %-][Ss]emaphore$")
	) then
		name = name .. " script"
	end
	if not nocap then
		name = mw.getContentLanguage():ucfirst(name)
	end
	return name
end

function Script:makeCategoryLink()
	return "[[:Category:" .. self:getCategoryName() .. "|" .. self:getDisplayForm() .. "]]"
end

--[==[Returns the Wikidata item id for the script or <code>nil</code>. This corresponds to the the second field in the data modules.]==]
function Script:getWikidataItem()
	return require("language_like").getWikidataItem(self)
end

--[==[
Returns the name of the Wikipedia article for the script. `project` specifies the language and project to retrieve
the article from, defaulting to {"enwiki"} for the English Wikipedia. Normally if specified it should be the project
code for a specific-language Wikipedia e.g. "zhwiki" for the Chinese Wikipedia, but it can be any project, including
non-Wikipedia ones. If the project is the English Wikipedia and the property {wikipedia_article} is present in the data
module it will be used first. In all other cases, a sitelink will be generated from {:getWikidataItem} (if set). The
resulting value (or lack of value) is cached so that subsequent calls are fast. If no value could be determined, and
`noCategoryFallback` is {false}, {:getCategoryName} is used as fallback; otherwise, {nil} is returned. Note that if
`noCategoryFallback` is {nil} or omitted, it defaults to {false} if the project is the English Wikipedia, otherwise
to {true}. In other words, under normal circumstances, if the English Wikipedia article couldn't be retrieved, the
return value will fall back to a link to the script's category, but this won't normally happen for any other project.
]==]
function Script:getWikipediaArticle(noCategoryFallback, project)
	return require("language_like").getWikipediaArticle(self, noCategoryFallback, project)
end

--[==[Returns the name of the Wikimedia Commons category page for the script.]==]
function Script:getCommonsCategory()
	return require("language_like").getCommonsCategory(self)
end

--[==[Returns the charset defining the script's characters from the script's data file.
This can be used to search for words consisting only of this script, but see the warning above.]==]
function Script:getCharacters()
	return self.characters or nil
end

--[==[Returns the number of characters in the text that are part of this script.
'''Note:''' You should never assume that text consists entirely of the same script. Strings may contain spaces, punctuation and even wiki markup or HTML tags. HTML tags will skew the counts, as they contain Latin-script characters. So it's best to avoid them.]==]
function Script:countCharacters(text)
	local charset = self._rawData.characters
	if charset == nil then
		return 0
	end
	return select(2, ugsub(text, "[" .. charset .. "]", ""))
end

function Script:hasCapitalization()
	return not not self._rawData.capitalized
end

function Script:hasSpaces()
	return self._rawData.spaces ~= false
end

function Script:isTransliterated()
	return self._rawData.translit ~= false
end

--[==[Returns true if the script is (sometimes) sorted by scraping page content, meaning that it is sensitive to changes in capitalization during sorting.]==]
function Script:sortByScraping()
	return not not self._rawData.sort_by_scraping
end

--[==[Returns the text direction. Horizontal scripts return {{lua|"ltr"}} (left-to-right) or {{lua|"rtl"}} (right-to-left), while vertical scripts return {{lua|"vertical-ltr"}} (vertical left-to-right) or {{lua|"vertical-rtl"}} (vertical right-to-left).]==]
function Script:getDirection()
	return self._rawData.direction or "ltr"
end

function Script:getRawData()
	return self._rawData
end

--[==[Returns {{lua|true}} if the script contains characters that require fixes to Unicode normalization under certain circumstances, {{lua|false}} if it doesn't.]==]
function Script:hasNormalizationFixes()
	return not not self._rawData.normalizationFixes
end

--[==[Corrects discouraged sequences of Unicode characters to the encouraged equivalents.]==]
function Script:fixDiscouragedSequences(text)
	if self:hasNormalizationFixes() then
		local norm_fixes = self._rawData.normalizationFixes
		local to = norm_fixes.to
		if to then
			for i, v in ipairs(norm_fixes.from) do
				text = ugsub(text, v, to[i] or "")
			end
		end
	end
	return text
end

do
	local combiningClasses
	
	-- Implements a modified form of Unicode normalization for instances where there are identified deficiencies in the default Unicode combining classes.
	local function fixNormalization(text, self)
		if not self:hasNormalizationFixes() then
			return text
		end
		local norm_fixes = self._rawData.normalizationFixes
		local new_classes = norm_fixes.combiningClasses
		if not (new_classes and umatch(text, "[" .. norm_fixes.combiningClassCharacters .. "]")) then
			return text
		end
		-- Obtain the list of default combining classes.
		combiningClasses = combiningClasses or mw.loadData("Module:Unicode data/combining classes")
		text = explode(text)
		-- Manual sort based on new combining classes.
		-- We can't use table.sort, as it compares the first/last values in an array as a shortcut, which messes things up.
		for i = 2, #text do
			local char = text[i]
			local class = new_classes[char] or combiningClasses[char]
			if class then
				repeat
					i = i - 1
					local prev = text[i]
					if (new_classes[prev] or combiningClasses[prev] or 0) < class then
						break
					end
					text[i], text[i + 1] = char, prev
				until i == 1
			end
		end
		return concat(text)
	end
	
	function Script:toFixedNFC(text)
		return fixNormalization(toNFC(text), self)
	end
	
	function Script:toFixedNFD(text)
		return fixNormalization(toNFD(text), self)
	end
	
	function Script:toFixedNFKC(text)
		return fixNormalization(toNFKC(text), self)
	end
	
	function Script:toFixedNFKD(text)
		return fixNormalization(toNFKD(text), self)
	end
end

function Script:toJSON()
	if not self._types then
		self:hasType()
	end
	local types = {}
	for type in pairs(self._types) do
		table.insert(types, type)
	end
	
	local ret = {
		canonicalName = self:getCanonicalName(),
		categoryName = self:getCategoryName("nocap"),
		code = self._code,
		otherNames = self:getOtherNames(true),
		aliases = self:getAliases(),
		varieties = self:getVarieties(),
		type = types,
		direction = self:getDirection(),
		characters = self:getCharacters(),
		parent = self:getParent(),
		systems = self:getSystemCodes(),
		wikipediaArticle = self._rawData.wikipedia_article,
	}
	
	return require("JSON.lua").toJSON(ret)
end

Script.__index = Script
	
function export.makeObject(code, data, useRequire)
	return data and setmetatable({
		_rawData = data,
		_code = code,
		characters = data.characters
	}, Script) or nil
end

--[==[Finds the script whose code matches the one provided. If it exists, it returns a {{lua|Script}} object representing the script. Otherwise, it returns {{lua|nil}}, unless <span class="n">paramForError</span> is given, in which case an error is generated. If <code class="n">paramForError</code> is {{lua|true}}, a generic error message mentioning the bad code is generated; otherwise <code class="n">paramForError</code> should be a string or number specifying the parameter that the code came from, and this parameter will be mentioned in the error message along with the bad code.]==]
function export.getByCode(code, paramForError, disallowNil, useRequire)
	-- Track uses of paramForError, ultimately so it can be removed, as error-handling should be done by [[Module:parameters]], not here.
	if paramForError ~= nil then
		require("debug/track.lua")("scripts/paramForError")
	end
	
	if code == nil and not disallowNil then
		return nil
	end
	
	local data
	if useRequire then
		data = require("scripts.data.lua")[code]
	else
		data = mw.loadData("scripts.data")[code]
	end
	
	local retval = export.makeObject(code, data, useRequire)
	
	if not retval and paramForError then
		require("languages.error")(code, paramForError, "script code", nil, "not real lang")
	end
	
	return retval
end

function export.getByCanonicalName(name, useRequire)
	local code
	if useRequire then
		code = require("Module:scripts/by name")[name]
	else
		code = mw.loadData("Module:scripts/by name")[name]
	end
	
	return export.getByCode(code, nil, nil, useRequire)
end

--[==[
	Takes a codepoint or a character and finds the script code (if any) that is
	appropriate for it based on the codepoint, using the data module
	[[Module:scripts/recognition data]]. The data module was generated from the
	patterns in [[Module:scripts/data]] using [[Module:User:Erutuon/script recognition]].

	Converts the character to a codepoint. Returns a script code if the codepoint
	is in the list of individual characters, or if it is in one of the defined
	ranges in the 4096-character block that it belongs to, else returns "None".
]==]
function export.charToScript(char)
	return require("scripts.charToScript.lua").charToScript(char)
end

--[==[
Returns the code for the script that has the greatest number of characters in `text`. Useful for script tagging text
that is unspecified for language. Uses [[Module:scripts/recognition data]] to determine a script code for a character
language-agnostically. Specifically, it works as follows:
	
Convert each character to a codepoint. Iterate the counter for the script code if the codepoint is in the list
of individual characters, or if it is in one of the defined ranges in the 4096-character block that it belongs to.
	
Each script has a two-part counter, for primary and secondary matches. Primary matches are when the script is the
first one listed; otherwise, it's a secondary match. When comparing scripts, first the total of both are compared
(i.e. the overall number of matches). If these are the same, the number of primary and then secondary matches are
used as tiebreakers. For example, this is used to ensure that `Grek` takes priority over `Polyt` if no characters
which exclusively match `Polyt` are found, as `Grek` is a subset of `Polyt`.
	
If `none_is_last_resort_only` is specified, this will never return {"None"} if any characters in `text` belong to a
script. Otherwise, it will return {"None"} if there are more characters that don't belong to a script than belong to
any individual script. (FIXME: This behavior is probably wrong, and `none_is_last_resort_only` should probably
become the default.)
]==]
function export.findBestScriptWithoutLang(text, none_is_last_resort_only)
	return require("scripts.charToScript.lua").findBestScriptWithoutLang(text, none_is_last_resort_only)
end

return export