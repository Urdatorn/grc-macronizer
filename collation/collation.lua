local export = {}

local require = require
local byte = string.byte
local concat = table.concat
local find = string.find
local get_plaintext = require("utilities.lua").get_plaintext
local match = string.match
local memoize = require("fun.lua").memoize
local remove = table.remove
local sort = table.sort
local string_sort -- defined below as export.string_sort
local sub = string.sub
local trim = mw.text.trim
local type = type

-- Custom functions for generating a sortkey that will achieve the desired sort
-- order.
-- name of module and name of exported function
local custom_funcs = {
	ahk = { "Mymr-sortkey", "makeSortKey" },
	aio = { "Mymr-sortkey", "makeSortKey" },
	blk = { "Mymr-sortkey", "makeSortKey" },
	egy = { "egy-utilities", "make_sortkey" },
	kac = { "Mymr-sortkey", "makeSortKey" },
	kht = { "Mymr-sortkey", "makeSortKey" },
	ksw = { "Mymr-sortkey", "makeSortKey" },
	kyu = { "Mymr-sortkey", "makeSortKey" },
	["mkh-mmn"] = { "Mymr-sortkey", "makeSortKey" },
	mnw = { "Mymr-sortkey", "makeSortKey" },
	my  = { "Mymr-sortkey", "makeSortKey" },
	phk = { "Mymr-sortkey", "makeSortKey" },
	pwo = { "Mymr-sortkey", "makeSortKey" },
	omx = { "Mymr-sortkey", "makeSortKey" },
	shn = { "Mymr-sortkey", "makeSortKey" },
	tjl = { "Mymr-sortkey", "makeSortKey" },
}

local function is_lang_object(lang)
	return type(lang) == "table" and type(lang.getCanonicalName) == "function"
end

local function check_function(funcName, argIdx, func)
	if type(func) ~= "function" then
		error("bad argument #" .. argIdx .. " to " .. funcName
			.. ": expected function object, got " .. type(func) .. ".", 2)
	end
	return true
end

local function make_sortkey_func(lang, make_sortbase)
	local langcode = lang:getCode()
	local makeDisplayText = lang.makeDisplayText
	local custom_func = custom_funcs[langcode]
		
	local makeSortKey
	if custom_func then
		local _makeSortKey = require("Module:" .. custom_func[1])[custom_func[2]]
		function makeSortKey(_, text)
			return _makeSortKey(text, langcode)
		end
	else
		makeSortKey = lang.makeSortKey
	end
	
	return make_sortbase and check_function("make_sortkey_func", 2, make_sortbase) and function(element)
		return (makeSortKey(
			lang,
			(makeDisplayText(
				lang,
				get_plaintext(make_sortbase(element))
			))
		))
	end or function(element)
		return (makeSortKey(
			lang,
			(makeDisplayText(
				lang,
				get_plaintext(element)
			))
		))
	end
end

-- When comparing two elements with code points outside the BMP, the less-than
-- operator treats all code points above U+FFFF as equal because of a bug in
-- glibc. See [[phab:T193096#4161287]]. Instead, compares bytes, which always
-- yields the same result as comparing code points in valid UTF-8 strings.
-- UTF-8-encoded characters that do not belong to the Basic Multilingual Plane
-- (that is, with code points greater than U+FFFF) have byte sequences that
-- begin with the bytes 240 to 244.
do
	-- Memoize match because we've set the `simple` flag, which means it
	-- should only be used with fixed additional arguments (in this case, the
	-- pattern).
	local match = memoize(match, true)
	
	function export.string_sort(item1, item2)
		if match(item1, "^[^\240-\244]*$") and match(item2, "^[^\240-\244]*$") then
			return item1 < item2
		end
		local i = 0
		while true do
			i = i + 1
			local b1, b2 = byte(item1, i, i), byte(item2, i, i)
			if not b1 then
				return b2 and true or false
			elseif b1 ~= b2 then
				return b2 and b1 < b2 or false
			end
		end
	end
	string_sort = export.string_sort
end

function export.sort(elems, lang, make_sortbase)
	if not is_lang_object(lang) then
		return sort(elems)
	end
	
	local make_sortkey = memoize(make_sortkey_func(lang, make_sortbase), true)
	
	return sort(elems, function(elem1, elem2)
		return string_sort(make_sortkey(elem1), make_sortkey(elem2))
	end)
end

function export.sort_template(frame)
	if not mw.isSubsting() then
		error("This template must be substed.")
	end
	
	local args
	if frame.args.parent then
		args = frame:getParent().args
	else
		args = frame.args
	end
	
	local m_table = require("table.lua")
	local elems = m_table.shallowcopy(args)
	local m_languages = require("languages.lua")
	local lang
	if args.lang then
		lang = m_languages.getByCode(args.lang) or m_languages.err(args.lang, "lang")
	else
		local code = remove(elems, 1)
		code = code and trim(code)
		lang = m_languages.getByCode(code) or m_languages.err(code, 1)
	end
	
	local i = 1
	while true do
		local elem = elems[i]
		while elem do
			elem = trim(elem, "%s")
			if elem ~= "" then
				break
			end
			remove(elems, i)
			elem = elems[i]
		end
		if not elem then
			break
		elseif not ( -- Strip redundant wikilinks.
			not match(elem, "^()%[%[") or
			find(elem, "[[", 3, true) or
			find(elem, "]]", 3, true) ~= #elem - 1 or
			find(elem, "|", 3, true)
		) then
			elem = sub(elem, 3, -3)
			elem = trim(elem, "%s")
		end
		elems[i] = elem .. "\n"
		i = i + 1
	end
	
	elems = m_table.removeDuplicates(elems)
	export.sort(elems, lang)
	
	return concat(elems, args.sep or "|")
end

return export