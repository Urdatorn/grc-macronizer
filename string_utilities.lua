local export = {}

local function_module = "fun"

local mw = mw
local string = string
local table = table
local ustring = mw.ustring

local byte = string.byte
local char = string.char
local concat = table.concat
local find = string.find
local format = string.format
local gmatch = string.gmatch
local gsub = string.gsub
local len = string.len
local load_data = mw.loadData
local lower = string.lower
local match = string.match
local next = next
local require = require
local reverse = string.reverse
local select = select
local sort = table.sort
local sub = string.sub
local tonumber = tonumber
local tostring = tostring
local type = type
local ucodepoint = ustring.codepoint
local ufind = ustring.find
local ugcodepoint = ustring.gcodepoint
local ugmatch = ustring.gmatch
local ugsub = ustring.gsub
local ulower = ustring.lower
local umatch = ustring.match
local unpack = unpack
local upper = string.upper
local usub = ustring.sub
local uupper = ustring.upper
-- Defined below.
local charset_escape
local codepoint
local explode_utf8
local format_fun
local get_indefinite_article
local pattern_escape
local pattern_simplifier
local php_trim
local replacement_escape
local u
local ulen

local module_name = "string_utilities"

local function is_callable(...)
	is_callable = require(function_module).is_callable
	return is_callable(...)
end

--[==[Explodes a string into an array of UTF-8 characters. '''Warning''': this function has no safety checks for non-UTF-8 byte sequences, to optimize speed and memory use. Inputs containing them therefore result in undefined behaviour.]==]
function export.explode_utf8(str)
	local text, i = {}, 0
	for ch in gmatch(str, ".[\128-\191]*") do
		i = i + 1
		text[i] = ch
	end
	return text
end
explode_utf8 = export.explode_utf8

do
	local chars = {
		["\0"] = "%z", ["$"] = "%$", ["%"] = "%%", ["("] = "%(", [")"] = "%)",
		["*"] = "%*", ["+"] = "%+", ["-"] = "%-", ["."] = "%.", ["?"] = "%?",
		["["] = "%[", ["]"] = "%]", ["^"] = "%^"
	}
	--[==[Escapes the magic characters used in [[mw:Extension:Scribunto/Lua reference manual#Patterns|patterns]] (Lua's version of regular expressions): <code>$%()*+-.?[]^</code>, and converts the null character to <code>%z</code>. For example, {{lua|"^$()%.[]*+-?\0"}} becomes {{lua|"%^%$%(%)%%%.%[%]%*%+%-%?%z"}}. This is necessary when constructing a pattern involving arbitrary text (e.g. from user input).]==]
	function export.pattern_escape(str)
		return (gsub(str, "[%z$%%()*+%-.?[%]^]", chars))
	end
	pattern_escape = export.pattern_escape

	--[==[Escapes the magic characters used in [[mw:Extension:Scribunto/Lua reference manual#Patterns|pattern]] character sets: <code>%-]^</code>, and converts the null character to <code>%z</code>.]==]
	function export.charset_escape(str)
		return (gsub(str, "[%z%%%-%]^]", chars))
	end
	charset_escape = export.charset_escape
end

--[==[Escapes only <code>%</code>, which is the only magic character used in replacement [[mw:Extension:Scribunto/Lua reference manual#Patterns|patterns]] with string.gsub and mw.ustring.gsub.]==]
function export.replacement_escape(str)
	return (gsub(str, "%%", "%%%%"))
end
replacement_escape = export.replacement_escape

do
	local function check_sets_equal(set1, set2)
		local k2
		for k1, v1 in next, set1 do
			local v2 = set2[k1]
			if v1 ~= v2 and (v2 == nil or not check_sets_equal(v1, v2)) then
				return false
			end
			k2 = next(set2, k2)
		end
		return next(set2, k2) == nil
	end
	
	local function check_sets(bytes)
		local key, set1, set = next(bytes)
		if set1 == true then
			return true
		elseif not check_sets(set1) then
			return false
		end
		while true do
			key, set = next(bytes, key)
			if not key then
				return true
			elseif not check_sets_equal(set, set1) then
				return false
			end
		end
	end
	
	local function make_charset(range)
		if #range == 1 then
			return char(range[1])
		end
		sort(range)
		local compressed, n, start = {}, 0, range[1]
		for i = 1, #range do
			local this, nxt = range[i], range[i + 1]
			if nxt ~= this + 1 then
				n = n + 1
				compressed[n] = this == start and char(this) or
					char(start) .. "-" .. char(this)
				start = nxt
			end
		end
		return "[" .. concat(compressed) .. "]"
	end
	
	local function parse_1_byte_charset(pattern, pos)
		while true do
			local ch, nxt_pos
			pos, ch, nxt_pos = match(pattern, "()([%%%]\194-\244][\128-\191]*)()", pos)
			if not ch then
				return false
			elseif ch == "%" then
				if match(pattern, "^()[acdlpsuwxACDLPSUWXZ\128-\255]", nxt_pos) then
					return false
				end
				pos = pos + 2
			elseif ch == "]" then
				pos = nxt_pos
				return pos
			else
				return false
			end
		end
	end
	
	local function _pattern_simplifier(pattern)
		if type(pattern) == "number" then
			return tostring(pattern)
		end
		local pos, captures, start, n, output = 1, 0, 1, 0
		while true do
			local ch, nxt_pos
			pos, ch, nxt_pos = match(pattern, "()([%%(.[\194-\244][\128-\191]*)()", pos)
			if not ch then
				break
			end
			local nxt = sub(pattern, nxt_pos, nxt_pos)
			if ch == "%" then
				if nxt == "b" then
					if not match(pattern, "^()[^\128-\255][^\128-\255]", pos + 2) then
						return false
					end
					pos = pos + 4
				elseif nxt == "f" then
					pos = pos + 2
					if not match(pattern, "^()%[[^^]", pos) then
						return false
					end
					-- Only possible to convert a %f charset which is all
					-- ASCII, so use parse_1_byte_charset.
					pos = parse_1_byte_charset(pattern, pos)
					if not pos then
						return false
					end
				elseif nxt == "Z" then
					pos = pos + 2
					nxt = sub(pattern, pos, pos)
					if nxt == "*" or nxt == "+" or nxt == "-" then
						pos = pos + 1
					else
						output = output or {}
						n = n + 1
						if nxt == "?" then
							output[n] = sub(pattern, start, pos - 3) .. "[\1-\127\194-\244]?[\128-\191]*"
							pos = pos + 1
						else
							output[n] = sub(pattern, start, pos - 3) .. "[\1-\127\194-\244][\128-\191]*"
						end
						start = pos
					end
				elseif find("acdlpsuwxACDLPSUWX", nxt, 1, true) then
					return false
				-- Skip the next character if it's ASCII. Otherwise, we will
				-- still need to do length checks.
				else
					pos = pos + (byte(nxt) < 128 and 2 or 1)
				end
			elseif ch == "(" then
				if nxt == ")" or captures == 32 then
					return false
				end
				captures = captures + 1
				pos = pos + 1
			elseif ch == "." then
				if nxt == "*" or nxt == "+" or nxt == "-" then
					pos = pos + 2
				else
					output = output or {}
					n = n + 1
					if nxt == "?" then
						output[n] = sub(pattern, start, pos - 1) .. "[^\128-\191]?[\128-\191]*"
						pos = pos + 2
					else
						output[n] = sub(pattern, start, pos - 1) .. "[^\128-\191][\128-\191]*"
						pos = pos + 1
					end
					start = pos
				end
			elseif ch == "[" then
				-- Fail negative charsets. TODO: 1-byte charsets should be safe.
				if nxt == "^" then
					return false
				-- If the first character is "%", ch_len is determined by the
				-- next one instead.
				elseif nxt == "%" then
					nxt_pos = nxt_pos + 1
					nxt = sub(pattern, nxt_pos, nxt_pos)
				end
				local ch_len = #match(pattern, "^.[\128-\191]*", nxt_pos)
				if ch_len == 1 then -- Single-byte charset.
					pos = parse_1_byte_charset(pattern, pos + 1)
					if not pos then
						return false
					end
				else -- Multibyte charset.
					local charset_pos, bytes = pos
					pos = pos + 1
					while true do -- TODO: non-ASCII charset ranges.
						pos, ch, nxt_pos = match(pattern, "()([^\128-\191][\128-\191]*)()", pos)
						if not ch then
							return false
						-- If escaped, get the next character. No need to
						-- distinguish magic characters or character classes,
						-- as they'll all fail for having the wrong length
						-- anyway.
						elseif ch == "%" then
							pos, ch, nxt_pos = match(pattern, "()([^\128-\191][\128-\191]*)()", pos)
						elseif ch == "]" then
							pos = nxt_pos
							break
						end
						if ch_len ~= #ch then
							return false
						end
						bytes = bytes or {}
						local bytes = bytes
						for i = 1, ch_len - 1 do
							local b = byte(ch, i, i)
							bytes[b] = bytes[b] or {}
							bytes = bytes[b]
						end
						bytes[byte(ch, -1)] = true
						pos = nxt_pos
					end
					if not pos then
						return false
					end
					local nxt = sub(pattern, pos, pos)
					if (
						(nxt == "?" or nxt == "*" or nxt == "-") or
						(nxt == "+" and ch_len > 2) or
						not check_sets(bytes)
					) then
						return false
					end
					local ranges, b, key, next_byte = {}, 0
					repeat
						key, next_byte = next(bytes)
						local range, n = {key}, 1
						-- Loop starts on the second iteration.
						for key in next, bytes, key do
							n = n + 1
							range[n] = key
						end
						b = b + 1
						ranges[b] = range
						bytes = next_byte
					until next_byte == true
					if nxt == "+" then
						local range1, range2 = ranges[1], ranges[2]
						ranges[1] = make_charset(range1)
						ranges[3] = make_charset(range2)
						local n = #range2
						for i = 1, #range1 do
							n = n + 1
							range2[n] = range1[i]
						end
						ranges[2] = make_charset(range2) .. "*"
						pos = pos + 1
					else
						for i = 1, #ranges do
							ranges[i] = make_charset(ranges[i])
						end
					end
					output = output or {}
					n = n + 1
					output[n] = sub(pattern, start, charset_pos - 1) .. concat(ranges)
					start = pos
				end
			elseif nxt == "+" then
				if #ch ~= 2 then
					return false
				end
				output = output or {}
				n = n + 1
				output[n] = sub(pattern, start, pos) .. "[" .. ch .. "]*" .. sub(ch, 2, 2)
				pos = nxt_pos + 1
				start = pos
			elseif nxt == "?" or nxt == "*" or nxt == "-" then
				return false
			else
				pos = nxt_pos
			end
		end
		if start == 1 then
			return pattern
		end
		return concat(output) .. sub(pattern, start)
	end
	
	--[==[Parses `pattern`, a ustring library pattern, and attempts to convert it into a string library pattern. If conversion isn't possible, returns false.]==]
	function pattern_simplifier(pattern)
		-- Memoize the actual function, point variables to it, then call it.
		pattern_simplifier = require(function_module).memoize(_pattern_simplifier, true)
		export.pattern_simplifier = pattern_simplifier
		return pattern_simplifier(pattern)
	end
	export.pattern_simplifier = pattern_simplifier -- For testing.
end

function export.len(str)
	return type(str) == "number" and len(str) or
		#str - #gsub(str, "[^\128-\191]+", "")
end
ulen = export.len

function export.sub(str, i, j)
	str, i = type(str) == "number" and tostring(str) or str, i or 1
	if i < 0 or j and j < 0 then
		return usub(str, i, j)
	elseif j and i > j or i > #str then
		return ""
	end
	local n, new_i = 0
	for loc1, loc2 in gmatch(str, "()[^\128-\191]+()[\128-\191]*") do
		n = n + loc2 - loc1
		if not new_i and n >= i then
			new_i = loc2 - (n - i) - 1
			if not j then
				return sub(str, new_i)
			end
		end
		if j and n > j then
			return sub(str, new_i, loc2 - (n - j) - 1)
		end
	end
	return new_i and sub(str, new_i) or ""
end

do
	local function _find(str, loc1, loc2, ...)
		if loc1 and not match(str, "^()[^\128-\255]*$") then
			-- Use raw values of loc1 and loc2 to get loc1 and the length of the match.
			loc1, loc2 = ulen(sub(str, 1, loc1)), ulen(sub(str, loc1, loc2))
			-- Offset length with loc1 to get loc2.
			loc2 = loc1 + loc2 - 1
		end
		return loc1, loc2, ...
	end
	
	--[==[A version of find which uses string.find when possible, but otherwise uses mw.ustring.find.]==]
	function export.find(str, pattern, init, plain)
		init = init or 1
		if init ~= 1 and not match(str, "^()[^\128-\255]*$") then
			return ufind(str, pattern, init, plain)
		elseif plain then
			return _find(str, find(str, pattern, init, true))
		end
		local simple = pattern_simplifier(pattern)
		if simple then
			return _find(str, find(str, simple, init))
		end
		return ufind(str, pattern, init)
	end
end

--[==[A version of match which uses string.match when possible, but otherwise uses mw.ustring.match.]==]
function export.match(str, pattern, init)
	init = init or 1
	if init ~= 1 and not match(str, "^()[^\128-\255]*$") then
		return umatch(str, pattern, init)
	end
	local simple = pattern_simplifier(pattern)
	if simple then
		return match(str, simple, init)
	end
	return umatch(str, pattern, init)
end

--[==[A version of gmatch which uses string.gmatch when possible, but otherwise uses mw.ustring.gmatch.]==]
function export.gmatch(str, pattern)
	local simple = pattern_simplifier(pattern)
	if simple then
		return gmatch(str, simple)
	end
	return ugmatch(str, pattern)
end

--[==[A version of gsub which uses string.gsub when possible, but otherwise uses mw.ustring.gsub.]==]
function export.gsub(str, pattern, repl, n)
	local simple = pattern_simplifier(pattern)
	if simple then
		return gsub(str, simple, repl, n)
	end
	return ugsub(str, pattern, repl, n)
end

--[==[Like gsub, but pattern-matching facilities are turned off, so `pattern` and `repl` (if a string) are treated as literal.]==]
function export.plain_gsub(str, pattern, repl, n)
	return gsub(str, pattern_escape(pattern), type(repl) == "string" and replacement_escape(repl) or repl, n)
end

--[==[Reverses a UTF-8 string; equivalent to string.reverse.]==]
function export.reverse(str)
	return reverse(gsub(str, "[\194-\244][\128-\191]*", reverse))
end

do
	local function err(cp)
		error("Codepoint " .. cp .. " is out of range: codepoints must be between 0x0 and 0x10FFFF.", 2)
	end

	local function utf8_char(cp)
		cp = math.floor(tonumber(cp)) -- Ensure cp is an integer
		if cp < 0 then
			err(string.format("-0x%X", -cp))
		elseif cp < 0x80 then
			return char(cp)
		elseif cp < 0x800 then
			return char(
				0xC0 + math.floor(cp / 0x40),
				0x80 + (cp % 0x40)
			)
		elseif cp < 0x10000 then
			if cp >= 0xD800 and cp < 0xE000 then
				return "?" -- Handle surrogate pairs explicitly.
			end
			return char(
				0xE0 + math.floor(cp / 0x1000),
				0x80 + math.floor(cp / 0x40) % 0x40,
				0x80 + (cp % 0x40)
			)
		elseif cp < 0x110000 then
			return char(
				0xF0 + math.floor(cp / 0x40000),
				0x80 + math.floor(cp / 0x1000) % 0x40,
				0x80 + math.floor(cp / 0x40) % 0x40,
				0x80 + (cp % 0x40)
			)
		end
		err(string.format("0x%X", cp))
	end
	
	function export.char(cp, ...)
		if ... == nil then
			return utf8_char(cp)
		end
		local ret = {cp, ...}
		for i = 1, #ret do
			ret[i] = utf8_char(ret[i])
		end
		return concat(ret)
	end
	
	u = export.char
end

do
	local function get_codepoint(b1, b2, b3, b4)
		if b1 < 128 then
			return b1, 1
		elseif b1 < 224 then
			return 0x40 * b1 + b2 - 0x3080, 2
		elseif b1 < 240 then
			return 0x1000 * b1 + 0x40 * b2 + b3 - 0xE2080, 3
		end
		return 0x40000 * b1 + 0x1000 * b2 + 0x40 * b3 + b4 - 0x3C82080, 4
	end

	function export.codepoint(str, i, j)
		if type(str) == "number" then
			return byte(str, i, j)
		end
		i, j = i or 1, j == -1 and #str or i or 1
		if i == 1 and j == 1 then
			return (get_codepoint(byte(str, 1, 4)))
		elseif i < 0 or j < 0 then
			return ucodepoint(str, i, j) -- FIXME
		end
		local n, nb, ret, nr = 0, 1, {}, 0
		while n < j do
			n = n + 1
			if n < i then
				local b = byte(str, nb)
				nb = nb + (b < 128 and 1 or b < 224 and 2 or b < 240 and 3 or 4)
			else
				local b1, b2, b3, b4 = byte(str, nb, nb + 3)
				if not b1 then
					break
				end
				nr = nr + 1
				local add
				ret[nr], add = get_codepoint(b1, b2, b3, b4)
				nb = nb + add
			end
		end
		return unpack(ret)
	end
	codepoint = export.codepoint
	
	function export.gcodepoint(str, i, j)
		i, j = i or 1, j ~= -1 and j or nil
		if i < 0 or j and j < 0 then
			return ugcodepoint(str, i, j) -- FIXME
		end
		local n, nb = 1, 1
		while n < i do
			local b = byte(str, nb)
			if not b then
				break
			end
			nb = nb + (b < 128 and 1 or b < 224 and 2 or b < 240 and 3 or 4)
			n = n + 1
		end
		
		return function()
			if j and n > j then
				return nil
			end
			n = n + 1
			local b1, b2, b3, b4 = byte(str, nb, nb + 3)
			if not b1 then
				return nil
			end
			local ret, add = get_codepoint(b1, b2, b3, b4)
			nb = nb + add
			return ret
		end
	end
end

--[==[A version of lower which uses string.lower when possible, but otherwise uses mw.ustring.lower.]==]
function export.lower(str)
	return (match(str, "^()[^\128-\255]*$") and lower or ulower)(str)
end

--[==[A version of upper which uses string.upper when possible, but otherwise uses mw.ustring.upper.]==]
function export.upper(str)
	return (match(str, "^()[^\128-\255]*$") and upper or uupper)(str)
end

do
	local function add_captures(text, n, ...)
		-- Insert any captures from the splitting pattern.
		local offset, capture = n - 1, ...
		while capture do
			n = n + 1
			text[n] = capture
			capture = select(n - offset, ...)
		end
		return n
	end
	
	local function iterate(str, str_len, text, n, start, _sub, loc1, loc2, ...)
		if not (loc1 and start <= str_len) then
			-- If no match, or there is but we're past the end of the string
			-- (which happens when the match is the empty string), then add
			-- the final chunk and return.
			n = n + 1
			text[n] = _sub(str, start)
			return
		elseif loc2 < loc1 then
			-- Special case: If we match the empty string, then include the
			-- next character; this avoids an infinite loop, and makes
			-- splitting by an empty string work the way mw.text.split() does
			-- (including non-adjacent empty string matches with %f). If we
			-- reach the end of the string this way, return immediately, so we
			-- don't get a final empty string. If using the string library, we
			-- need to make sure we advance by one UTF-8 character.
			if _sub == sub then
				loc1 = loc1 + #match(str, "^[\128-\191]*", loc1 + 1)
			end
			n = n + 1
			text[n] = _sub(str, start, loc1)
			start = loc1 + 1
			if start > str_len then
				return ... and add_captures(text, n, ...) or n
			end
		else
			-- Add chunk up to the current match.
			n = n + 1
			text[n] = _sub(str, start, loc1 - 1)
			start = loc2 + 1
		end
		return (... and add_captures(text, n, ...) or n), start
	end
	
	local function _split(str, get_next, str_len, _sub, _find, func, plain)
		local text, n, start = {}, 0, 1
		
		if func then
			repeat
				n, start = iterate(str, str_len, text, n, start, _sub, get_next(str, start))
			until not start
		else
			repeat
				n, start = iterate(str, str_len, text, n, start, _sub, _find(str, get_next, start, plain))
			until not start
		end
		
		return text
	end
	
	--[==[Reimplementation of mw.text.split() that includes any capturing groups in the splitting pattern. This works like Python's re.split() function, except that it has Lua's behavior when the split pattern is empty (i.e. advancing by one character at a time; Python returns the whole remainder of the string). When possible, it will use the string library, but otherwise uses the ustring library. There are two optional parameters: `str_lib` forces use of the string library, while `plain` turns any pattern matching facilities off, treating `pattern` as literal.
	
		In addition, `pattern` may be a custom find function (or callable table), which takes the input string and start index as its two arguments, and must return the start and end index of the match, plus any optional captures, or nil if there are no further matches. By default, the start index will be calculated using the ustring library, unless `str_lib` or `plain` is set.]==]
	function export.split(str, pattern, str_lib, plain)
		local func = is_callable(pattern)
		if str_lib or plain then
			return _split(str, pattern, #str, sub, find, func, plain)
		elseif not func then
			local simple = pattern_simplifier(pattern)
			if simple then
				return _split(str, simple, #str, sub, find)
			end
		end
		return _split(str, pattern, ulen(str), usub, ufind, func)
	end
	export.capturing_split = export.split -- To be removed.
end

do
	-- TODO: merge this with export.split. Not clear how to do this while
	-- maintaining the same level of performance, as gsplit is slower.
	local function _split(str, pattern, str_len, _sub, _find, plain)
		local start, final = 1
		
		local function iter(loc1, loc2, ...)
			-- If no match, return the final chunk.
			if not loc1 then
				final = true
				return _sub(str, start)
			end
			-- Special case: If we match the empty string, then eat the
			-- next character; this avoids an infinite loop, and makes
			-- splitting by the empty string work the way mw.text.gsplit() does
			-- (including non-adjacent empty string matches with %f). If we
			-- reach the end of the string this way, set `final` to true, so we
			-- don't get stuck matching the empty string at the end.
			local chunk
			if loc2 < loc1 then
				-- If using the string library, we need to make sure we advance
				-- by one UTF-8 character.
				if _sub == sub then
					loc1 = loc1 + #match(str, "^[\128-\191]*", loc1 + 1)
				end
				chunk = _sub(str, start, loc1)
				if loc1 >= str_len then
					final = true
				else
					start = loc1 + 1
				end
			-- Eat chunk up to the current match.
			else
				chunk = _sub(str, start, loc1 - 1)
				start = loc2 + 1
			end
			return chunk, ...
		end
		
		return function()
			if not final then
				return iter(_find(str, pattern, start, plain))
			end
			return nil
		end
	end
	
	function export.gsplit(str, pattern, str_lib, plain)
		if str_lib or plain then
			return _split(str, pattern, #str, sub, find, plain)
		end
		local simple = pattern_simplifier(pattern)
		if simple then
			return _split(str, simple, #str, sub, find)
		end
		return _split(str, pattern, ulen(str), usub, ufind)
	end
end

-- Note: this algorithm is a refined version of "^%m*(.*%M)" (where %m/%M are the charset/anticharset), which is the fastest trim algorithm for any strings which don't match "^%m*$" (i.e. all %m characters), as they result in catastrophic backtracking. This function splits the operation into two stages, which reduces those strings to "" after the first stage. See export.php_trim for an even faster workaround which only works for charsets sets that include "\0". Trims which require umatch use the pattern "^%m*(.-)%m*$", however, as the overhead of calling two ustring functions outweighs the benefits of this optimization.
function export.trim(str, charset)
	if not charset then
		return match(gsub(str, "^%s*", ""), "^.*%S") or ""
	elseif match(charset, "^()[^\128-\255]*$") then
		return match(gsub(str, "^[" .. charset .. "]*", ""), "^.*[^" .. charset .. "]") or ""
	end
	return umatch(str, "^[" .. charset .. "]*(.-)[" .. charset .. "]*$")
end

do
	local entities

	local function decode_numeric_entity(code, pattern, base)
		local cp = match(code, pattern) and tonumber(code, base)
		return cp and cp < 0x110000 and u(cp) or nil
	end

	local function decode_entity(hash, x, code)
		if hash == "#" then
			return x == "" and decode_numeric_entity(code, "^%d+$") or
				decode_numeric_entity(code, "^%x+$", 16)
		end
		entities = entities or load_data("data/entities.lua")
		return entities[x .. code]
	end

	-- Non-ASCII characters aren't valid in proper HTML named entities, but MediaWiki uses them in some custom aliases which have also been included in [[Module:data/entities]].
	function export.decode_entities(str)
		return find(str, "&", 1, true) and
			gsub(str, "&(#?)([xX]?)([%w\128-\255]+);", decode_entity) or str
	end
end

do
	local html_entities
	
	local function encode_entity(ch)
		local entity = html_entities[ch]
		if entity then
			return entity
		end
		entity = "&#" .. codepoint(ch) .. ";"
		html_entities[ch] = entity
		return entity
	end
	
	function export.encode_entities(str, charset, str_lib, plain)
		-- Memoized HTML entities (taken from mw.text.lua).
		html_entities = html_entities or {
			["\""] = "&quot;",
			["&"] = "&amp;",
			["'"] = "&#039;",
			["<"] = "&lt;",
			[">"] = "&gt;",
			["\194\160"] = "&nbsp;",
		}
		if not charset then
			return (gsub(str, "[\"&'<>\194]\160?", html_entities))
		elseif plain then
			return (gsub(str, "[" .. charset_escape(charset) .. "]", encode_entity))
		elseif str_lib then
			if not match(charset, "^()[^\128-\255]*$") then
				error("Cannot use the string library with a character set that contains a character with a codepoint above U+007F.")
			end
			return (gsub(str, "[" .. charset .. "]", encode_entity))
		end
		local pattern = charset and "[" .. charset .. "]"
		local simple = pattern_simplifier(pattern)
		if simple then
			return (gsub(str, simple, encode_entity))
		end
		return (ugsub(str, pattern, encode_entity))
	end
end

do
	local function decode_path(code)
		return char(tonumber(code, 16))
	end
	
	local function decode(lead, trail)
		if lead == "+" or lead == "_" then
			return " " .. trail
		elseif #trail == 2 then
			return decode_path(trail)
		end
		return lead .. trail
	end
	
	function export.decode_uri(str, enctype)
		enctype = enctype and upper(enctype) or "QUERY"
		if enctype == "PATH" then
			return find(str, "%", 1, true) and
				gsub(str, "%%(%x%x)", decode_path) or str
		elseif enctype == "QUERY" then
			return (find(str, "%", 1, true) or find(str, "+", 1, true)) and
				gsub(str, "([%%%+])(%x?%x?)", decode) or str
		elseif enctype == "WIKI" then
			return (find(str, "%", 1, true) or find(str, "_", 1, true)) and
				gsub(str, "([%%_])(%x?%x?)", decode) or str
		end
		error("bad argument #2 to \"decode_uri\" (expected QUERY, PATH, or WIKI)", 2)
	end
end

do
	local function _remove_comments(str, pre)
		local head = find(str, "<!--", 1, true)
		if not head then
			return str
		end
		local ret, n = {sub(str, 1, head - 1)}, 1
		while true do
			local loc = find(str, "-->", head + 4, true)
			if not loc then
				return pre and concat(ret) or
					concat(ret) .. sub(str, head)
			end
			head = loc + 3
			loc = find(str, "<!--", head, true)
			if not loc then
				return concat(ret) .. sub(str, head)
			end
			n = n + 1
			ret[n] = sub(str, head, loc - 1)
			head = loc
		end
	end
	
	--[==[Removes any HTML comments from the input text. `stage` can be one of three options:
	* {{lua|"PRE"}} (default) applies the method used by MediaWiki's preprocessor: all {{code||<nowiki><!-- ... --></nowiki>}} pairs are removed, as well as any text after an unclosed {{code||<nowiki><!--</nowiki>}}. This is generally suitable when parsing raw template or [[mw:Parser extension tags|parser extension tag]] code. (Note, however, that the actual method used by the preprocessor is considerably more complex and differs under certain conditions (e.g. comments inside nowiki tags); if full accuracy is absolutely necessary, use [[Module:template parser]] instead).
	* {{lua|"POST"}} applies the method used to generate the final page output once all templates have been expanded: it loops over the text, removing any {{code||<nowiki><!-- ... --></nowiki>}} pairs until no more are found (e.g. {{code||<nowiki><!-<!-- ... -->- ... --></nowiki>}} would be fully removed), but any unclosed {{code||<nowiki><!--</nowiki>}} is ignored. This is suitable for handling links embedded in template inputs, where the {{lua|"PRE"}} method will have already been applied by the native parser.
	* {{lua|"BOTH"}} applies {{lua|"PRE"}} then {{lua|"POST"}}.]==]
	function export.remove_comments(str, stage)
		if not stage or stage == "PRE" then
			return _remove_comments(str, true)
		end
		local processed = stage == "POST" and _remove_comments(str) or
			stage == "BOTH" and _remove_comments(str, true) or
			error("bad argument #2 to \"remove_comments\" (expected PRE, POST, or BOTH)", 2)
		while processed ~= str do
			str = processed
			processed = _remove_comments(str)
		end
		return str
	end
end

--[==[Lua equivalent of PHP's {{code|php|trim($string)}}, which trims {{lua|"\0"}}, {{lua|"\t"}}, {{lua|"\n"}}, {{lua|"\v"}}, {{lua|"\r"}} and {{lua|" "}}. This is useful when dealing with template parameters, since the native parser trims them like this.]==]
function export.php_trim(str)
	-- Note: this is a special-case version of the algorithm used by export.trim (see the comments at that function). In frontier patterns, %z is used to mean the start/end of the string, in addition to its usual meaning of "\0". Since the charset includes "\0", it's possible to use "%f[%M].*%f[%m]" (where %m/%M are the charset/anticharset), which is only slightly slower than "^%m*(.*%M)", but avoids catastrophic backtracking in strings which match "^%m*$" due to %z matching the start/end of a string. This means that there's no need to call match twice, as there's no need to check for "^%m*$" strings first.
	return match(str, "%f[^%z\t\n\v\r ].*%f[%z\t\n\v\r ]") or ""
end
php_trim = export.php_trim

--[==[Takes a parameter name as either a string or number, and returns the Scribunto-normalized form (i.e. the key that that parameter would have in a {{lua|frame.args}} table). For example, {{lua|"1"}} (a string) is normalized to {{lua|1}} (a number), {{lua|" foo "}} is normalized to {{lua|"foo"}}, and {{lua|1.5}} (a number) is normalized to {{lua|"1.5"}} (a string). Inputs which cannot be normalized (e.g. booleans) return {{lua|nil}}. If the `no_trim` flag is set, string parameters are not trimmed, but strings may still be converted to numbers if they do not contain whitespace; this is necessary when normalizing keys into the form received by PHP during callbacks, before any trimming occurs (e.g. in the table of arguments when calling {{lua|frame:expandTemplates()}}).

Strings are trimmed with {{lua|export.php_trim}}, unless the `no_trim` flag is set. They are then converted to numbers if '''all''' of the following are true:
# They are integers; i.e. no decimals or leading zeroes (e.g. {{lua|"2"}}, but not {{lua|"2.0"}} or {{lua|"02"}}).
# They are ≤ 2{{sup|53}} and ≥ -2{{sup|53}}.
# There is no leading sign unless < 0 (e.g. {{lua|"2"}} or {{lua|"-2"}}, but not {{lua|"+2"}} or {{lua|"-0"}}).
# They contain no leading or trailing whitespace (which may be present when the `no_trim` flag is set).

Numbers are converted to strings if '''either''':
# They are not integers (e.g. {{lua|1.5}}).
# They are > 2{{sup|53}} or < -2{{sup|53}}.

When converted to strings, integers ≤ 2{{sup|63}} and ≥ -2{{sup|63}} are formatted as integers (i.e. all digits are given), which is the range of PHP's integer precision, though the actual output may be imprecise since Lua's integer precision is > 2{{sup|53}} to < -2{{sup|53}}. All other numbers use the standard formatting output by {{lua|tostring()}}.]==]
function export.scribunto_param_key(key, no_trim)
	local tp = type(key)
	if tp == "string" then
		if not no_trim then
			key = php_trim(key)
		end
		if match(key, "^()-?[1-9]%d*$") then
			local num = tonumber(key)
			-- Lua integers are only precise to 2^53 - 1, so specifically check for 2^53 and -2^53 as strings, since a numerical comparison won't work as it can't distinguish 2^53 from 2^53 + 1.
			return (
				num <= 9007199254740991 and num >= -9007199254740991 or
				key == "9007199254740992" or
				key == "-9007199254740992"
			) and num or key
		end
		return key == "0" and 0 or key
	elseif tp == "number" then
		-- No special handling needed for inf or NaN.
		return key % 1 == 0 and (
			key <= 9007199254740992 and key >= -9007199254740992 and key or
			key <= 9223372036854775808 and key >= -9223372036854775808 and format("%d", key)
		) or tostring(key)
	end
	return nil
end

do
	local byte_escapes
	
	local function escape_byte(b)
		return byte_escapes[b] or format("\\%03d", byte(b))
	end
	
	function export.escape_bytes(str)
		byte_escapes = byte_escapes or load_data("Module:string utilities/data").byte_escapes
		return (gsub(str, ".", escape_byte))
	end
end

function export.format_fun(str, fun)
	return (gsub(str, "{(\\?)((\\?)[^{}]*)}", function(p1, name, p2)
		if #p1 + #p2 == 1 then
			return name == "op" and "{" or
				name == "cl" and "}" or
				error(module_name .. ".format: unrecognized escape sequence '{\\" .. name .. "}'")
		elseif fun(name) and type(fun(name)) ~= "string" then
			error(module_name .. ".format: \"" .. name .. "\" is a " .. type(fun(name)) .. ", not a string")
		end
		return fun(name) or error(module_name .. ".format: \"" .. name .. "\" not found in table")
	end))
end
format_fun = export.format_fun

--[==[This function, unlike {{lua|string.format}} and {{lua|mw.ustring.format}}, takes just two parameters—a format string and a table—and replaces all instances of {{lua|{param_name}}} in the format string with the table's entry for {{lua|param_name}}. The opening and closing brace characters can be escaped with <code>{\op}</code> and <code>{\cl}</code>, respectively. A table entry beginning with a slash can be escaped by doubling the initial slash.
====Examples====
* {{lua|=string_utilities.format("{foo} fish, {bar} fish, {baz} fish, {quux} fish", {["foo"]="one", ["bar"]="two", ["baz"]="red", ["quux"]="blue"})}}
*: produces: {{lua|"one fish, two fish, red fish, blue fish"}}
* {{lua|=string_utilities.format("The set {\\op}1, 2, 3{\\cl} contains {\\\\hello} elements.", {["\\hello"]="three"})}}
*: produces: {{lua|"The set {1, 2, 3} contains three elements."}}
*:* Note that the single and double backslashes should be entered as double and quadruple backslashes when quoted in a literal string.]==]
function export.format(str, tbl)
	return format_fun(str, function(key)
		return tbl[key]
	end)
end

do
	local function do_uclcfirst(str, case_func)
		-- Actual function to re-case of the first letter.
		local first_letter = case_func(match(str, "^.[\128-\191]*") or "")
		return first_letter .. sub(str, #first_letter + 1)
	end
	
	local function uclcfirst(str, case_func)
		-- If there's a link at the beginning, re-case the first letter of the
		-- link text. This pattern matches both piped and unpiped links.
		-- If the link is not piped, the second capture (linktext) will be empty.
		local link, linktext, remainder = match(str, "^%[%[([^|%]]+)%|?(.-)%]%](.*)$")
		if link then
			return "[[" .. link .. "|" .. do_uclcfirst(linktext ~= "" and linktext or link, case_func) .. "]]" .. remainder
		end
		return do_uclcfirst(str, case_func)
	end
	
	function export.ucfirst(str)
		return uclcfirst(str, uupper)
	end

	function export.lcfirst(str)
		return uclcfirst(str, ulower)
	end
	
	local function capitalize(w)
		return uclcfirst(w, uupper)
	end
	
	--[==[Capitalize each word of a string. WARNING: May be broken in the presence of multiword links.]==]
	function export.capitalize(str)
		if type(str) == "table" then
			-- allow calling from a template
			str = str.args[1]
		end
		-- Capitalize multi-word that is separated by spaces
		-- by uppercasing the first letter of each part.
		-- I assume nobody will input all CAP text.
		return (ugsub(str, "%S+", capitalize))
	end
end

function export.pluralize(str) -- To be removed once all calling modules have been changed to call Module:en-utilities directly.
	return require("en_utilities.lua").pluralize(str)
end

do
	local function do_singularize(str)
		local sing = match(str, "^(.-)ies$")
		if sing then
			return sing .. "y"
		end
		-- Handle cases like "[[parish]]es"
		return match(str, "^(.-[cs]h%]*)es$") or -- not -zhes
		-- Handle cases like "[[box]]es"
			match(str, "^(.-x%]*)es$") or -- not -ses or -zes
		-- Handle regular plurals
			match(str, "^(.-)s$") or
		-- Otherwise, return input
			str
	end
	
	local function collapse_link(link, linktext)
		if link == linktext then
			return "[[" .. link .. "]]"
		end
		return "[[" .. link .. "|" .. linktext .. "]]"
	end
	
	--[==[
	Singularize a word in a smart fashion, according to normal English rules. Works analogously to {pluralize()}.

	'''NOTE''': This doesn't always work as well as {pluralize()}. Beware. It will mishandle cases like "passes" -> "passe", "eyries" -> "eyry".
	# If word ends in -ies, replace -ies with -y.
	# If the word ends in -xes, -shes, -ches, remove -es. [Does not affect -ses, cf. "houses", "impasses".]
	# Otherwise, remove -s.

	This handles links correctly:
	# If a piped link, change the second part appropriately. Collapse the link to a simple link if both parts end up the same.
	# If a non-piped link, singularize the link.
	# A link like "[[parish]]es" will be handled correctly because the code that checks for -shes etc. allows ] characters between the
	  'sh' etc. and final -es.
	]==]
	function export.singularize(str)
		if type(str) == "table" then
			-- allow calling from a template
			str = str.args[1]
		end
		-- Check for a link. This pattern matches both piped and unpiped links.
		-- If the link is not piped, the second capture (linktext) will be empty.
		local beginning, link, linktext = match(str, "^(.*)%[%[([^|%]]+)%|?(.-)%]%]$")
		if not link then
			return do_singularize(str)
		elseif linktext ~= "" then
			return beginning .. collapse_link(link, do_singularize(linktext))
		end
		return beginning .. "[[" .. do_singularize(link) .. "]]"
	end
end

--[==[
Return the appropriate indefinite article to prefix to `str`. Correctly handles links and capitalized text.
Does not correctly handle words like [[union]], [[uniform]] and [[university]] that take "a" despite beginning with
a 'u'. The returned article will have its first letter capitalized if `ucfirst` is specified, otherwise lowercase.
]==]
function export.get_indefinite_article(str, ucfirst)
	str = str or ""
	-- If there's a link at the beginning, examine the first letter of the
	-- link text. This pattern matches both piped and unpiped links.
	-- If the link is not piped, the second capture (linktext) will be empty.
	local link, linktext = match(str, "^%[%[([^|%]]+)%|?(.-)%]%]")
	if match(link and (linktext ~= "" and linktext or link) or str, "^()[AEIOUaeiou]") then
		return ucfirst and "An" or "an"
	end
	return ucfirst and "A" or "a"
end
get_indefinite_article = export.get_indefinite_article

--[==[
Prefix `text` with the appropriate indefinite article to prefix to `text`. Correctly handles links and capitalized
text. Does not correctly handle words like [[union]], [[uniform]] and [[university]] that take "a" despite beginning
with a 'u'. The returned article will have its first letter capitalized if `ucfirst` is specified, otherwise lowercase.
]==]
function export.add_indefinite_article(text, ucfirst)
	return get_indefinite_article(text, ucfirst) .. " " .. text
end

return export