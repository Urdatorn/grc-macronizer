local subexport = {}

local require_when_needed = require("Module:require when needed")

local cp = require_when_needed("Module:string utilities", "codepoint")
local floor = math.floor
local get_plaintext = require_when_needed("utilities", "get_plaintext")
local get_script = require_when_needed("scripts", "getByCode")
local insert = table.insert
local ipairs = ipairs
local min = math.min
local pairs = pairs
local setmetatable = setmetatable
local sort = table.sort
local split = require_when_needed("Module:string utilities", "split")
local table_len = require_when_needed("table", "length")
local type = type

-- Copied from [[Module:Unicode data]].
local function binaryRangeSearch(codepoint, ranges)
	local low, mid, high
	low, high = 1, ranges.length or table_len(ranges)
	while low <= high do
		mid = floor((low + high) / 2)
		local range = ranges[mid]
		if codepoint < range[1] then
			high = mid - 1
		elseif codepoint <= range[2] then
			return range, mid
		else
			low = mid + 1
		end
	end
	return nil, mid
end

-- Copied from [[Module:Unicode data]].
local function linearRangeSearch(codepoint, ranges)
	for i, range in ipairs(ranges) do
		if codepoint < range[1] then
			break
		elseif codepoint <= range[2] then
			return range
		end
	end
end

local function compareRanges(range1, range2)
	return range1[1] < range2[1]
end

-- Save previously used codepoint ranges in case another character is in the
-- same range.
local rangesCache = {}

--[=[
	Takes a codepoint or a character and finds the script code(s) (if any) that are appropriate for it based on the codepoint, using the data module [[Module:scripts/recognition data]]. The data module was generated from the patterns in [[Module:scripts/data]] using [[Module:User:Erutuon/script recognition]].
	
	By default, it returns only the first script code if there are multiple matches (i.e. the code we take to be the default). If `all_scripts` is set, then a table of all matching codes is returned.
]=]

local charToScriptData
function subexport.charToScript(char, all_scripts)
	charToScriptData = charToScriptData or mw.loadData("Module:scripts/recognition data")
	local t = type(char)
	local codepoint
	if t == "string" then
		local etc
		codepoint, etc = cp(char, 1, 2)
		if etc then
			error("bad argument #1 to 'charToScript' (expected a single character)")
		end
	elseif t == "number" then
		codepoint = char
	else
		error(("bad argument #1 to 'charToScript' (expected string or a number, got %s)")
			:format(t))
	end
	
	local ret = {}
	local individualMatch = charToScriptData.individual[codepoint]
	if individualMatch then
		ret = split(individualMatch, "%s*,%s*", true)
	else
		local range
		if rangesCache[1] then
			range = linearRangeSearch(codepoint, rangesCache)
			if range then
				for i, script in ipairs(range) do
					if i > 2 then
						insert(ret, script)
						if not all_scripts then
							break
						end
					end
				end
			end
		end
		if not ret[1] then
			local index = floor(codepoint / 0x1000)
			range = linearRangeSearch(index, charToScriptData.blocks)
			if not range and charToScriptData[index] then
				range = binaryRangeSearch(codepoint, charToScriptData[index])
				if range then
					insert(rangesCache, range)
					sort(rangesCache, compareRanges)
				end
			end
			if range then
				for i, script in ipairs(range) do
					if i > 2 then
						insert(ret, script)
						if not all_scripts then
							break
						end
					end
				end
			end
		end
	end
	if not ret[1] then
		insert(ret, "None")
	end
	if all_scripts then
		return ret
	else
		return ret[1]
	end
end

--[=[
	Finds the best script for a string in a language-agnostic way.
	
	Converts each character to a codepoint. Iterates the counter for the script code if the codepoint is in the list
	of individual characters, or if it is in one of the defined ranges in the 4096-character block that it belongs to.
	
	Each script has a two-part counter, for primary and secondary matches. Primary matches are when the script is the
	first one listed; otherwise, it's a secondary match. When comparing scripts, first the total of both are compared
	(i.e. the overall number of matches). If these are the same, the number of primary and then secondary matches are
	used as tiebreakers. For example, this is used to ensure that `Grek` takes priority over `Polyt` if no characters
	which exclusively match `Polyt` are found, as `Grek` is a subset of `Polyt`.
	
	If `none_is_last_resort_only` is specified, this will never return None if any characters in `text` belong to a
	script. Otherwise, it will return None if there are more characters that don't belong to a script than belong to
	any individual script. (FIXME: This behavior is probably wrong, and `none_is_last_resort_only` should probably
	become the default.)
]=]
function subexport.findBestScriptWithoutLang(text, none_is_last_resort_only)
	-- `scripts` contains counters for any scripts detected so far. Jpan and Kore are handled as special-cases, as they are combinations of other scripts.
	local scripts_mt = 	{Jpan = true, Kore = true}
	
	local weights_mt = {
		__lt = function(a, b)
			if a[1] + a[2] ~= b[1] + b[2] then
				return a[1] + a[2] < b[1] + b[2]
			elseif a[1] ~= b[1] then
				return a[1] < b[1]
			elseif a[2] ~= b[2] then
				return a[2] < b[2]
			else
				return false
			end
		end
	}
	scripts_mt.__index = function(t, k)
		local ret = {}
		if k == "Jpan" and scripts_mt.Jpan then
			for i = 1, 2 do
				ret[i] = t["Hani"][i] + t["Hira"][i] + t["Kana"][i]
			end
		elseif k == "Kore" and scripts_mt.Kore then
			for i = 1, 2 do
				ret[i] = t["Hani"][i] + t["Hang"][i]
			end
		else
			for i = 1, 2 do
				insert(ret, 0)
			end
		end
		return setmetatable(ret, weights_mt)
	end
	
	local scripts = setmetatable({}, scripts_mt)
	
	text = get_plaintext(text)
	
	local combined_scripts = {
		Jpan = {["Hani"] = true, ["Hira"] = true, ["Kana"] = true},
		Kore = {["Hani"] = true, ["Hang"] = true}
	}
	
	for character in text:gmatch(".[\128-\191]*") do
		for i, script in ipairs(subexport.charToScript(character, true)) do
			if not none_is_last_resort_only or script ~= "None" then
				scripts[script] = scripts[script]
				local weight = min(i, 2)
				scripts[script][weight] = scripts[script][weight] + 1
			end
		end
	end
	
	-- Check the combined script counts. If a single constituent has the same count (i.e. it's the only one), discard the combined script.
	for combined_script, set in pairs(combined_scripts) do
		for script in pairs(set) do
			scripts[combined_script] = scripts[combined_script]
			if (scripts[script][1] + scripts[script][2]) == (scripts[combined_script][1] + scripts[combined_script][2]) then
				scripts[combined_script] = nil
				break
			end
		end
	end
	
	local bestScript
	local greatestCount
	for script, count in pairs(scripts) do
		if (not greatestCount) or greatestCount < count then
			bestScript = script
			greatestCount = count
		end
	end
	
	bestScript = bestScript or "None"
	
	return get_script(bestScript)
end

return subexport